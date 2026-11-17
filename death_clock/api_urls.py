"""Route API modul Pantry Death Clock. Di-include di PantryNecromancer/urls.py pada /api/death-clock/."""
from django.urls import path

from death_clock import api_views

app_name = 'death_clock_api'

urlpatterns = [
    path('items/', api_views.item_list, name='item-list'),
    path('items/<int:pk>/', api_views.item_detail, name='item-detail'),
]
