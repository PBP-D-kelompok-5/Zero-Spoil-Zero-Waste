"""Route API modul The Dead Drop. Di-include di PantryNecromancer/urls.py pada /api/dead-drop/."""
from django.urls import path  # noqa: F401

from dead_drop import api_views  # noqa: F401

app_name = 'dead_drop_api'

urlpatterns = [
    # TODO (Checkpoint 1): buka komentar setelah view-nya dibuat di api_views.py
    # path('listings/', api_views.listing_list, name='listing-list'),
    # path('listings/<int:pk>/', api_views.listing_detail, name='listing-detail'),
]
