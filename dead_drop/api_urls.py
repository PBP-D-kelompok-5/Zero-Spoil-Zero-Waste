"""Route API modul The Dead Drop. Di-include di PantryNecromancer/urls.py pada /api/dead-drop/."""
from django.urls import path

from dead_drop import api_views

app_name = 'dead_drop_api'

urlpatterns = [
    path('listings/', api_views.listing_list, name='listing-list'),
    path('listings/<int:pk>/', api_views.listing_detail, name='listing-detail'),
]
