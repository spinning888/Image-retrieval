from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
ASSIGNMENTS_DIR = Path(os.getenv("ASSIGNMENTS_DIR", str(BASE_DIR.parent)))
PROJECT_DIR = Path(os.getenv("PROJECT_DIR", str(ASSIGNMENTS_DIR.parent)))
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_DIR / "data")))

# ====== 必须项 ======
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

# 如果你用域名/https，建议配置：
_csrf = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [x.strip() for x in _csrf.split(",") if x.strip()]

# ====== 应用 ======
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "image_search.apps.ImageSearchConfig",
]

# ====== 中间件 ======
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # ✅ 关键：生产也能直接服务 /static/，避免页面“像没样式”
    # "whitenoise.middleware.WhiteNoiseMiddleware",  # 临时禁用以排查问题

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mysite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "mysite.wsgi.application"
ASGI_APPLICATION = "mysite.asgi.application"

# ====== DB ======
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ====== i18n ======
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True

# ====== Static ======
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # ✅ 生产 collectstatic 输出目录
STATICFILES_DIRS = [
    BASE_DIR / "static",  # 如果你有项目级 static/ 目录就启用；没有也不影响
]

# WhiteNoise 压缩与缓存（生产推荐）
if DEBUG:
    # 开发环境不要用 ManifestStorage：没有 collectstatic/manifest 时会导致页面 500（静态文件找不到映射）
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ====== Media（上传 query 图片）=====
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ====== Gallery（用于展示检索结果图片 & 检索底库）=====
GALLERY_URL = os.getenv("GALLERY_URL", "/gallery/")
GALLERY_ROOT = Path(os.getenv("GALLERY_ROOT", str(DATA_DIR / "images")))
GALLERY_INDEX = os.getenv("GALLERY_INDEX", str(DATA_DIR / "features" / "gallery_index.csv"))
GALLERY_FEATURES = os.getenv("GALLERY_FEATURES", str(DATA_DIR / "features" / "gallery_features.npy"))
GALLERY_CDN_BASE = os.getenv("GALLERY_CDN_BASE") or None

# DINOv2 NumPy 权重
DINO_WEIGHTS = os.getenv("DINO_WEIGHTS", str(DATA_DIR / "models" / "vit-dinov2-base.npz"))

# ====== DINO Backend (CPU/GPU) ======
# 默认用 numpy（CPU）。如要上 GPU，推荐用 ONNX Runtime：
# - Windows 有独显/核显都可以优先试 onnxruntime-directml（DmlExecutionProvider）
# - NVIDIA CUDA 可用 onnxruntime-gpu（CUDAExecutionProvider）
DINO_BACKEND = os.getenv("DINO_BACKEND", "numpy").strip().lower()  # numpy | onnx

# 仅当 DINO_BACKEND=onnx 时需要：ONNX 模型路径
DINO_ONNX_PATH = os.getenv("DINO_ONNX_PATH", "")

# 可选：手动指定 ORT providers 顺序（逗号分隔）
# 例：DINO_ORT_PROVIDERS=DmlExecutionProvider,CPUExecutionProvider
DINO_ORT_PROVIDERS = os.getenv("DINO_ORT_PROVIDERS", "")

# ====== Performance ======
# 预热引擎：用启动时间换首次检索速度
ENGINE_WARMUP = os.getenv("ENGINE_WARMUP", "1").lower() in ("1", "true", "yes")
# 更彻底预热（会更慢启动）：跑一次空白图 embedding
ENGINE_WARMUP_EMBED = os.getenv("ENGINE_WARMUP_EMBED", "0").lower() in ("1", "true", "yes")
# embedding 缓存：同一张图重复搜可以秒出
ENGINE_EMBED_CACHE_TTL = int(os.getenv("ENGINE_EMBED_CACHE_TTL", "86400"))

# 上传后在当前请求里最多等待多少毫秒，尽量做到“秒出”（0 表示不等待，完全异步）
INDEX_SYNC_WAIT_MS = int(os.getenv("INDEX_SYNC_WAIT_MS", "900"))

# ✅ 如果你想在 DEBUG=False 的情况下也临时用 Django 来服务 /media/ /gallery/
# （生产不推荐，但能“兜底避免页面打不开/图片404”）
SERVE_MEDIA_GALLERY = os.getenv("SERVE_MEDIA_GALLERY", "0").lower() in ("1", "true", "yes")

# ====== Security（生产建议）=====
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "1") in ("1", "true", "yes")
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "1") in ("1", "true", "yes")
