import os
from django.apps import AppConfig
from django.conf import settings


class ImageSearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'image_search'

    def ready(self) -> None:
        # 只在 runserver 主进程预热，避免 autoreload 触发两次
        if os.environ.get("RUN_MAIN") != "true":
            return

        if not getattr(settings, "ENGINE_WARMUP", True):
            return

        try:
            from .views import get_engine

            engine = get_engine()
            engine.warmup(do_embed=bool(getattr(settings, "ENGINE_WARMUP_EMBED", False)))
        except Exception:
            # 预热失败不影响页面可用性
            return
