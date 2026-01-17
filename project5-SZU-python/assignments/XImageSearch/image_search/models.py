from __future__ import annotations
from django.db import models


class HistoryRecord(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    query_image = models.ImageField(upload_to="queries/", null=True, blank=True)
    query_feat = models.BinaryField(null=True, blank=True, editable=False)
    feat_dim = models.IntegerField(default=0)

    class Meta:
        ordering = ["-id"]

    @property
    def query_preview_url(self):
        try:
            return self.query_image.url if self.query_image else None
        except Exception:
            return None

    def __str__(self) -> str:
        return f"HistoryRecord(id={self.id})"


class HistoryItem(models.Model):
    record = models.ForeignKey(HistoryRecord, on_delete=models.CASCADE, related_name="items")
    rank = models.IntegerField(default=0)
    url = models.TextField()
    score = models.FloatField(default=0.0)
    quality = models.CharField(max_length=10, default="Poor")  # Strong/Medium/Weak/Poor

    class Meta:
        ordering = ["rank"]

    def __str__(self) -> str:
        return f"HistoryItem(record_id={self.record_id}, rank={self.rank}, score={self.score:.4f})"


class Favorite(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.TextField(default="", blank=True)
    score = models.FloatField(default=0.0)
    tags = models.CharField(max_length=256, default="", blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Favorite(id={self.id}, score={self.score:.4f})"
