from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("image_search.urls")),
]

# 开发环境：Django 直接服务 media/gallery
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.GALLERY_URL, document_root=settings.GALLERY_ROOT)

# 生产兜底：可选用 Django 服务 media/gallery（不推荐长期使用）
elif getattr(settings, "SERVE_MEDIA_GALLERY", False):
    from django.views.static import serve

    urlpatterns += [
        path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
        path(settings.GALLERY_URL.lstrip("/") + "<path:path>", serve, {"document_root": settings.GALLERY_ROOT}),
    ]
