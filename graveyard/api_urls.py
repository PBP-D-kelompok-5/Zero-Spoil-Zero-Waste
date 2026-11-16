"""Route API modul The Graveyard & Waste Analytics. Di-include di PantryNecromancer/urls.py pada /api/graveyard/."""
from django.urls import path  # noqa: F401

from graveyard import api_views  # noqa: F401

app_name = 'graveyard_api'

urlpatterns = [
    # TODO (Checkpoint 1): buka komentar setelah view-nya dibuat di api_views.py
    # path('items/', api_views.item_list, name='item-list'),
    # path('items/<int:pk>/', api_views.item_detail, name='item-detail'),
]
