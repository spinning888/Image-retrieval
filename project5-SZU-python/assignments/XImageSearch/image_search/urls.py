from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("results/", views.results, name="results"),
    path("history/", views.history, name="history"),
    path("history/<int:record_id>/", views.history_detail, name="history_detail"),
    path("favorites/", views.favorites, name="favorites"),

    path("api/results/", views.api_results, name="api_results"),
    path("api/history/remove/", views.api_history_remove, name="api_history_remove"),
    path("api/favorite/remove/", views.api_favorite_remove, name="api_favorite_remove"),
    path("api/favorite/add/", views.api_favorite_add, name="api_favorite_add"),
]
