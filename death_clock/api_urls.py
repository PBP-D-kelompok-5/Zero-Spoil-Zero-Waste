"""Route API modul Pantry Death Clock. Di-include di PantryNecromancer/urls.py pada /api/death-clock/."""
from django.urls import path  # noqa: F401

from death_clock import api_views  # noqa: F401

app_name = 'death_clock_api'

urlpatterns = [
    # TODO (Checkpoint 1): buka komentar setelah view-nya dibuat di api_views.py
    # path('items/', api_views.item_list, name='item-list'),
    # path('items/<int:pk>/', api_views.item_detail, name='item-detail'),
]
