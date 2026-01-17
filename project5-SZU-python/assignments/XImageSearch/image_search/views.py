from __future__ import annotations

import os
import time
import hashlib
from urllib.parse import quote, unquote
from typing import Iterable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

import numpy as np
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction, close_old_connections
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect, csrf_exempt

from .models import HistoryRecord, HistoryItem, Favorite
from .search_engine import SearchEngine
from .dinov2_onnx import parse_providers


# ---------- Engine singleton ----------
_ENGINE: SearchEngine | None = None


def get_engine() -> SearchEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = SearchEngine(
            gallery_features_path=getattr(settings, "GALLERY_FEATURES", ""),
            gallery_index_path=getattr(settings, "GALLERY_INDEX", ""),
            gallery_url_prefix=getattr(settings, "GALLERY_URL", "/gallery/"),
            cdn_base=getattr(settings, "GALLERY_CDN_BASE", None),
            gallery_root=str(getattr(settings, "GALLERY_ROOT", "") or ""),
            weights_path=getattr(settings, "DINO_WEIGHTS", None),
            backend=str(getattr(settings, "DINO_BACKEND", "numpy") or "numpy"),
            onnx_model_path=str(getattr(settings, "DINO_ONNX_PATH", "") or "") or None,
            ort_providers=parse_providers(str(getattr(settings, "DINO_ORT_PROVIDERS", "") or "")),
        )
    return _ENGINE


# ---------- Async execution ----------
_EXECUTOR = ThreadPoolExecutor(max_workers=1)

# cache keys (survive multi-worker if cache backend is shared)
def _ck_status(record_id: int) -> str:
    return f"image_search:task:{record_id}:status"

def _ck_error(record_id: int) -> str:
    return f"image_search:task:{record_id}:error"

def _ck_embed(sha256_hex: str) -> str:
    return f"image_search:embed:{sha256_hex}"

def _set_task_pending(record_id: int, ttl: int = 3600) -> None:
    cache.set(_ck_status(record_id), "pending", ttl)
    cache.delete(_ck_error(record_id))

def _set_task_done(record_id: int, ttl: int = 3600) -> None:
    cache.set(_ck_status(record_id), "done", ttl)
    cache.delete(_ck_error(record_id))

def _set_task_error(record_id: int, error: str, ttl: int = 3600) -> None:
    cache.set(_ck_status(record_id), "error", ttl)
    cache.set(_ck_error(record_id), error[:4000], ttl)  # cap to avoid huge payloads


def _gallery_url_fix_and_exists(url: str) -> tuple[str, bool]:
    """
    保持你原来的“%20/%2B 等字面量编码文件名”兼容逻辑，但强化：
    - root/path traversal 防护
    - 返回是否存在
    """
    if not url:
        return url, False

    prefix = (getattr(settings, "GALLERY_URL", "/gallery/") or "/gallery/").rstrip("/") + "/"
    if not url.startswith(prefix):
        return url, True

    root = getattr(settings, "GALLERY_ROOT", None)
    if not root:
        return url, True

    root_abs = os.path.abspath(str(root))
    rest = url[len(prefix):]

    def exists_for(rest_part: str) -> bool:
        rel = unquote(rest_part).replace("/", os.sep)
        full = os.path.abspath(os.path.join(root_abs, rel))
        if not full.startswith(root_abs):
            return False
        return os.path.isfile(full)

    # A) as-is
    if exists_for(rest):
        return url, True

    # B) quote once (escape literal % -> %25)
    rest_q = quote(rest, safe="/")
    if exists_for(rest_q):
        return prefix + rest_q, True

    return prefix + rest_q, False


def _quality_stats(scores: Iterable[float]) -> dict:
    vals: list[float] = []
    for s in scores:
        try:
            fs = float(s)
        except Exception:
            continue
        if not np.isfinite(fs):
            continue
        vals.append(fs)

    if not vals:
        return {"avg": None, "best": None, "total": 0, "strong": 0, "medium": 0, "weak": 0, "poor": 0}

    # keep consistent with your current heuristic (do not break UI meaning)
    strong_t = 0.55
    medium_t = 0.45
    weak_t = 0.35

    return {
        "avg": float(sum(vals) / len(vals)),
        "best": float(max(vals)),
        "total": int(len(vals)),
        "strong": int(sum(1 for s in vals if s >= strong_t)),
        "medium": int(sum(1 for s in vals if medium_t <= s < strong_t)),
        "weak": int(sum(1 for s in vals if weak_t <= s < medium_t)),
        "poor": int(sum(1 for s in vals if s < weak_t)),
    }


def _run_search_async(record_id: int, image_bytes: bytes, filename: str, topk: int) -> None:
    """
    后台线程：计算 query embedding，检索，写入 DB
    关键改进：
    - 错误写 cache，results/api_results 一定能看见
    - 任何异常都不会影响“网页打开”
    """
    close_old_connections()
    _set_task_pending(record_id)

    try:
        engine = get_engine()

        # 性能优化：同一张图重复上传时，直接复用 embedding
        digest = hashlib.sha256(image_bytes).hexdigest()
        cached = cache.get(_ck_embed(digest))
        q_feat = None
        if isinstance(cached, (bytes, bytearray)):
            try:
                arr = np.frombuffer(cached, dtype=np.float32)
                # 维度校验，避免权重/特征切换导致错配
                if engine.features is not None and arr.shape[0] == int(engine.features.shape[1]):
                    q_feat = arr
            except Exception:
                q_feat = None

        if q_feat is None:
            q_feat = engine.embed_query(image_bytes)
            try:
                ttl = int(getattr(settings, "ENGINE_EMBED_CACHE_TTL", 86400))
            except Exception:
                ttl = 86400
            cache.set(_ck_embed(digest), q_feat.astype(np.float32, copy=False).tobytes(), ttl)

        results = engine.search(q_feat, topk=topk)

        feat = q_feat.astype(np.float32, copy=False)

        with transaction.atomic():
            rec = HistoryRecord.objects.select_for_update().get(id=record_id)
            rec.query_feat = feat.tobytes()
            rec.feat_dim = int(feat.shape[0])
            if not rec.query_image:
                rec.query_image.save(filename or "query.jpg", ContentFile(image_bytes), save=True)
            rec.save(update_fields=["query_feat", "feat_dim", "query_image"])

            HistoryItem.objects.filter(record=rec).delete()
            if results:
                HistoryItem.objects.bulk_create(
                    [HistoryItem(record=rec, rank=i + 1, url=r.url, score=r.score) for i, r in enumerate(results)],
                    batch_size=500,
                )

        _set_task_done(record_id)

    except Exception as e:
        _set_task_error(record_id, str(e))

    finally:
        close_old_connections()


# ---------- Views ----------
@csrf_exempt
@ensure_csrf_cookie
def index(request: HttpRequest) -> HttpResponse:
    """首页 - 处理GET和POST上传"""
    if request.method != "POST":
        # GET 请求：返回首页
        return render(request, "image_search/index.html")
    
    # POST 请求：处理上传
    accept = request.headers.get("Accept", "") or ""
    is_xhr = (request.headers.get("X-Requested-With") == "XMLHttpRequest") or ("application/json" in accept)

    up = request.FILES.get("image")
    if not up:
        msg = "未选择图片（字段名必须为 image）"
        if is_xhr:
            return JsonResponse({"ok": False, "error": msg}, status=400)
        return render(request, "image_search/index.html", {"error": msg})

    # topk hardening
    try:
        topk = int(request.POST.get("topk", "50"))
    except Exception:
        topk = 50
    topk = max(1, min(topk, 200))

    image_bytes = up.read()

    # create record immediately, so results page can open even if async fails
    with transaction.atomic():
        rec = HistoryRecord.objects.create()
        rec.query_image.save(up.name or "query.jpg", ContentFile(image_bytes), save=True)

    request.session["last_history_id"] = rec.id

    # mark pending immediately to avoid race with results page polling
    _set_task_pending(rec.id)

    # kick async task
    fut = _EXECUTOR.submit(_run_search_async, rec.id, image_bytes, up.name or "query.jpg", topk)

    # 尝试在请求内“抢一把”：如果机器够快，直接一秒内拿到结果
    # 默认等待 900ms，可用环境变量/设置关闭或调整
    try:
        wait_ms = int(getattr(settings, "INDEX_SYNC_WAIT_MS", 900))
    except Exception:
        wait_ms = 900

    if wait_ms > 0:
        try:
            fut.result(timeout=wait_ms / 1000.0)
        except FutureTimeout:
            pass

    redirect_url = reverse("results") + f"?hid={rec.id}"
    if is_xhr:
        return JsonResponse({"ok": True, "redirect": redirect_url, "hid": rec.id, "pending": True})
    return redirect(redirect_url)


@require_http_methods(["GET"])
@ensure_csrf_cookie
def results(request: HttpRequest) -> HttpResponse:
    """结果页"""
    hid = request.GET.get("hid")
    rec = None
    
    # 优先级1：如果指定了 hid，加载对应的记录
    if hid:
        try:
            rec = HistoryRecord.objects.get(id=int(hid))
        except Exception:
            rec = None
    
    # 优先级2：从 session 获取最近一次搜索
    if rec is None:
        sid = request.session.get("last_history_id")
        if sid:
            try:
                rec = HistoryRecord.objects.get(id=int(sid))
            except Exception:
                rec = None
    
    # 优先级3：加载最新的一条记录
    if rec is None:
        rec = HistoryRecord.objects.order_by("-id").first()
    
    # 如果还是没有任何记录，显示空结果页
    if rec is None:
        return render(request, "image_search/results.html", {
            "query_web_url": None,
            "results": [],
            "pending": False,
            "error": "暂无搜索记录，请回到首页上传图片进行搜索",
        })
    
    # 加载搜索结果
    items = HistoryItem.objects.filter(record=rec).order_by("-score")[:50]
    results_list = [
        {
            "rank": idx + 1,
            "url": item.url,
            "score": item.score,
            "quality": item.quality,
        }
        for idx, item in enumerate(items)
    ]
    
    # 检查是否还在等待中
    status = cache.get(_ck_status(rec.id), "done")
    pending = status == "pending"
    
    return render(request, "image_search/results.html", {
        "query_web_url": rec.query_preview_url,
        "results": results_list,
        "pending": pending,
        "hid": rec.id,
    })


@require_http_methods(["GET"])
@ensure_csrf_cookie
def history(request: HttpRequest) -> HttpResponse:
    """历史页"""
    records = HistoryRecord.objects.order_by("-created_at")[:20]
    return render(request, "image_search/history.html", {"records": records})


@require_http_methods(["GET"])
@ensure_csrf_cookie
def history_detail(request: HttpRequest, record_id: int) -> HttpResponse:
    """历史详情页"""
    rec = get_object_or_404(HistoryRecord, id=record_id)
    items = HistoryItem.objects.filter(record=rec).order_by("-score")[:50]
    
    results_list = [
        {
            "rank": idx + 1,
            "url": item.url,
            "score": item.score,
            "quality": item.quality,
        }
        for idx, item in enumerate(items)
    ]
    
    return render(request, "image_search/results.html", {
        "query_web_url": rec.query_preview_url,
        "results": results_list,
        "pending": False,
        "hid": rec.id,
    })


@require_http_methods(["GET"])
@ensure_csrf_cookie
def favorites(request: HttpRequest) -> HttpResponse:
    """收藏页"""
    favs = Favorite.objects.order_by("-created_at")[:50]
    return render(request, "image_search/favorites.html", {"favorites": favs})


@require_http_methods(["GET"])
def api_results(request: HttpRequest) -> JsonResponse:
    """获取搜索结果API"""
    hid = request.GET.get("hid")
    if not hid:
        return JsonResponse({"ok": False, "error": "hid required"}, status=400)
    
    try:
        rec = HistoryRecord.objects.get(id=int(hid))
    except Exception:
        return JsonResponse({"ok": False, "error": "not found"}, status=404)
    
    status = cache.get(_ck_status(rec.id), "done")
    pending = status == "pending"
    
    items = HistoryItem.objects.filter(record=rec).order_by("-score")[:50]
    results_list = [
        {
            "rank": idx + 1,
            "url": item.url,
            "score": float(item.score),
            "quality": item.quality,
        }
        for idx, item in enumerate(items)
    ]
    
    return JsonResponse({
        "ok": True,
        "pending": pending,
        "resultsCount": len(results_list),
        "results": results_list,
    })


@require_http_methods(["POST"])
@csrf_protect
def api_history_remove(request: HttpRequest) -> JsonResponse:
    """删除历史记录API"""
    try:
        hid = int(request.POST.get("id", 0))
        rec = HistoryRecord.objects.get(id=hid)
        rec.delete()
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
@csrf_protect
def api_favorite_add(request: HttpRequest) -> JsonResponse:
    """添加收藏API"""
    try:
        url = request.POST.get("url", "").strip()
        if not url:
            return JsonResponse({"ok": False, "error": "url required"}, status=400)

        # 强制要求填写标签：兼容 tag/tags 两种字段名
        tags = (request.POST.get("tags") or request.POST.get("tag") or "").strip()
        if not tags:
            return JsonResponse({"ok": False, "error": "tags required"}, status=400)

        score_raw = (request.POST.get("score") or "").strip()
        try:
            score = float(score_raw) if score_raw else 0.0
        except Exception:
            score = 0.0
        
        fav, created = Favorite.objects.get_or_create(
            url=url,
            defaults={"tags": tags, "score": score},
        )
        updated = False
        if not created:
            # 允许重复点击收藏时更新标签/分数
            new_tags = tags
            new_score = score
            if fav.tags != new_tags or float(fav.score) != float(new_score):
                fav.tags = new_tags
                fav.score = new_score
                fav.save(update_fields=["tags", "score"])
                updated = True

        return JsonResponse({"ok": True, "created": created, "updated": updated})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
@csrf_protect
def api_favorite_remove(request: HttpRequest) -> JsonResponse:
    """删除收藏API"""
    try:
        fid = int(request.POST.get("id", 0))
        fav = Favorite.objects.get(id=fid)
        fav.delete()
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)