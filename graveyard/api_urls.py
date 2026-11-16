"""Route API modul The Graveyard & Waste Analytics. Di-include di PantryNecromancer/urls.py pada /api/graveyard/."""
from django.urls import path

from graveyard import api_views

app_name = 'graveyard_api'

urlpatterns = [
    path('items/', api_views.item_list, name='item-list'),
    path('items/<int:pk>/', api_views.item_detail, name='item-detail'),
]
