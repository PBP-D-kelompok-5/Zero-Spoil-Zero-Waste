"""Route API modul Preservation Grimoire & Smell Test. Di-include di PantryNecromancer/urls.py pada /api/grimoire/."""
from django.urls import path 

from preservation_grimoire import api_views  

app_name = 'preservation_grimoire_api'

urlpatterns = [
    path('guides/', api_views.guide_list, name='api_guide_list'),
    path('guides/<int:pk>/', api_views.guide_detail, name='api_guide_detail'),
]
