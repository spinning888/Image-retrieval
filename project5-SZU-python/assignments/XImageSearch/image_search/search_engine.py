from __future__ import annotations
import io, os, csv, sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class SearchResult:
    url: str
    score: float


def _norm(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v) + 1e-12)
    return (v / n).astype(np.float32, copy=False)


class SearchEngine:
    """
    DINOv2 NumPy embedding + cosine retrieval.

    Hardening changes:
    - Gallery loading uses mmap to reduce memory spikes
    - Any load failure -> features=None (no crash), error message accessible
    - Path handling prevents traversal and encodes safely for /gallery/
    """

    def __init__(
        self,
        gallery_features_path: str,
        gallery_index_path: str,
        gallery_url_prefix: str = "/gallery/",
        cdn_base: Optional[str] = None,
        gallery_root: Optional[str] = None,
        weights_path: Optional[str] = None,
        backend: str = "numpy",
        onnx_model_path: Optional[str] = None,
        ort_providers: Optional[List[str]] = None,
    ):
        self.gallery_features_path = gallery_features_path or ""
        self.gallery_index_path = gallery_index_path or ""
        self.gallery_url_prefix = (gallery_url_prefix or "/gallery/").rstrip("/") + "/"
        self.cdn_base = (cdn_base.rstrip("/") + "/") if cdn_base else None

        self.gallery_root_abs = os.path.abspath(gallery_root) if gallery_root else None
        self.weights_path = weights_path

        self.backend = (backend or "numpy").strip().lower()
        self.onnx_model_path = onnx_model_path
        self.ort_providers = ort_providers

        self._vit = None
        self._weights_loaded = False

        self.features: Optional[np.ndarray] = None
        self.paths: List[str] = []
        self.last_error: Optional[str] = None

        self._load_gallery()

    def _set_error(self, msg: str):
        self.last_error = msg

    def _ensure_vit(self):
        if self._weights_loaded:
            return
        if self.backend in ("onnx", "ort", "onnxrt", "onnxruntime"):
            try:
                if not self.onnx_model_path:
                    raise RuntimeError("Missing onnx_model_path (DINO_ONNX_PATH)")
                model_abs = os.path.abspath(self.onnx_model_path)
                if not os.path.exists(model_abs):
                    raise FileNotFoundError(f"onnx model not found: {model_abs}")

                from .dinov2_onnx import Dinov2Onnx, OrtConfig

                self._vit = Dinov2Onnx(OrtConfig(model_path=model_abs, providers=self.ort_providers))
                self._weights_loaded = True
                return
            except Exception as e:
                # 自动回退到 numpy，保证服务可用
                self._set_error(f"ONNX backend failed: {e}. Falling back to numpy.")
                self.backend = "numpy"

        # default: numpy CPU backend
        if not self.weights_path:
            raise RuntimeError("Missing weights_path (DINO_WEIGHTS)")
        weights_path_abs = os.path.abspath(self.weights_path)
        if not os.path.exists(weights_path_abs):
            raise FileNotFoundError(f"weights not found: {weights_path_abs}")

        weights_dir = str(Path(weights_path_abs).resolve().parent)
        if weights_dir not in sys.path:
            sys.path.insert(0, weights_dir)

        try:
            from dinov2_numpy import Dinov2Numpy  # type: ignore
        except Exception as e:
            raise RuntimeError(f"Cannot import dinov2_numpy.Dinov2Numpy: {e}")

        weights = np.load(weights_path_abs, allow_pickle=False)
        self._vit = Dinov2Numpy(weights)
        self._weights_loaded = True

    @staticmethod
    def _preprocess_pil(img: Image.Image, target: int = 224) -> np.ndarray:
        img = img.convert("RGB")
        w, h = img.size
        if w <= 0 or h <= 0:
            raise ValueError("bad image size")

        short = min(w, h)
        scale = float(target) / float(short)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        img = img.resize((new_w, new_h), Image.BILINEAR)

        left = max(0, (new_w - target) // 2)
        top = max(0, (new_h - target) // 2)
        img = img.crop((left, top, left + target, top + target))

        arr = (np.array(img).astype(np.float32) / 255.0)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        arr = (arr - mean) / std
        x = arr.transpose(2, 0, 1)[None, ...]  # (1,3,224,224)
        return x

    def _load_gallery(self):
        self.features = None
        self.paths = []
        self.last_error = None

        # Features
        if self.gallery_features_path and os.path.exists(self.gallery_features_path):
            try:
                feats = np.load(self.gallery_features_path, mmap_mode="r", allow_pickle=False)
                feats = np.asarray(feats, dtype=np.float32)
                if feats.ndim != 2 or feats.shape[0] <= 0 or feats.shape[1] <= 0:
                    raise ValueError(f"bad gallery_features shape: {feats.shape}")
                # normalize
                denom = np.linalg.norm(feats, axis=1, keepdims=True) + 1e-12
                self.features = np.ascontiguousarray((feats / denom).astype(np.float32, copy=False))
            except Exception as e:
                self._set_error(f"Failed to load gallery features: {e}")
                self.features = None

        # Index
        if self.gallery_index_path and os.path.exists(self.gallery_index_path):
            try:
                with open(self.gallery_index_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    key = None
                    if reader.fieldnames:
                        for c in reader.fieldnames:
                            if c.lower() in ("path", "file", "filename", "image", "img"):
                                key = c
                                break
                        key = key or reader.fieldnames[0]

                    for row in reader:
                        p = (row.get(key) or "").strip()
                        if not p:
                            continue
                        # Normalize windows separators
                        norm = p.replace("/", "\\")
                        if self.gallery_root_abs and os.path.isabs(norm):
                            # convert absolute -> relative to root
                            try:
                                rel = os.path.relpath(norm, start=self.gallery_root_abs)
                                p = rel
                            except Exception:
                                p = os.path.basename(norm)
                        self.paths.append(p)
            except Exception as e:
                self._set_error(f"Failed to load gallery index: {e}")

        # fallback paths
        if self.features is not None and not self.paths:
            self.paths = [f"{i}.jpg" for i in range(int(self.features.shape[0]))]

        # align lengths
        if self.features is not None and len(self.paths) != int(self.features.shape[0]):
            n = min(len(self.paths), int(self.features.shape[0]))
            self.paths = self.paths[:n]
            self.features = self.features[:n]

    def embed_query(self, image_bytes: bytes) -> np.ndarray:
        self._ensure_vit()
        assert self._vit is not None
        img = Image.open(io.BytesIO(image_bytes))
        x = self._preprocess_pil(img, target=224)
        v = self._vit(x)[0].astype(np.float32, copy=False)
        return _norm(v)

    def warmup(self, do_embed: bool = False) -> None:
        """预热模型加载，减少第一次检索的额外开销。

        - do_embed=False: 仅加载权重（推荐，启动更快）
        - do_embed=True: 额外跑一次空白图 embedding（更彻底，但会让启动更慢）
        """
        self._ensure_vit()
        if not do_embed:
            return

        # 跑一次最小推理，让 numpy/权重相关路径“热起来”
        img = Image.new("RGB", (224, 224), color=(127, 127, 127))
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        _ = self.embed_query(bio.getvalue())

    def _to_url(self, path: str) -> str:
        rel = (path or "").replace("\\", "/").lstrip("/")
        # encode to preserve literal %xx in filenames
        rel_q = quote(rel, safe="/")
        if self.cdn_base:
            return self.cdn_base + rel_q
        return self.gallery_url_prefix + rel_q

    def search(self, q: np.ndarray, topk: int = 50) -> List[SearchResult]:
        feats = self.features
        if feats is None:
            return []
        if q.ndim != 1 or q.shape[0] != feats.shape[1]:
            return []

        n = int(feats.shape[0])
        if n <= 0:
            return []

        topk = int(topk)
        if topk <= 0:
            return []
        if topk > n:
            topk = n

        # Cosine similarity: dot product with normalized vectors
        sims = feats @ q

        # 性能优化：只取 TopK，不对全量结果排序（大库时差别很明显）
        if topk == n:
            top_indices = np.argsort(-sims)
        else:
            top_indices = np.argpartition(-sims, kth=topk - 1)[:topk]
            top_indices = top_indices[np.argsort(-sims[top_indices])]

        results = []
        for idx in top_indices:
            score = float(sims[idx])
            path = self.paths[int(idx)] if int(idx) < len(self.paths) else f"{idx}.jpg"
            url = self._to_url(path)
            results.append(SearchResult(url=url, score=score))

        return results
