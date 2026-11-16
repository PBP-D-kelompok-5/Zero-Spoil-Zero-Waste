"""Route API modul Preservation Grimoire & Smell Test. Di-include di PantryNecromancer/urls.py pada /api/grimoire/."""
from django.urls import path  # noqa: F401

from preservation_grimoire import api_views  # noqa: F401

app_name = 'preservation_grimoire_api'

urlpatterns = [
    # TODO (Checkpoint 1): buka komentar setelah view-nya dibuat di api_views.py
    # path('guides/', api_views.guide_list, name='guide-list'),
    # path('guides/<int:pk>/', api_views.guide_detail, name='guide-detail'),
]
