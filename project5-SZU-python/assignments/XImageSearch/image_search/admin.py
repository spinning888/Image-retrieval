from django.contrib import admin
from .models import HistoryRecord, HistoryItem, Favorite


class HistoryItemInline(admin.TabularInline):
    model = HistoryItem
    extra = 0
    ordering = ("rank",)


@admin.register(HistoryRecord)
class HistoryRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "query_image", "feat_dim")
    inlines = [HistoryItemInline]
    search_fields = ("id",)
    readonly_fields = ("created_at", "feat_dim")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "url", "score", "tags", "created_at")
    search_fields = ("url", "tags")
    readonly_fields = ("created_at",)
