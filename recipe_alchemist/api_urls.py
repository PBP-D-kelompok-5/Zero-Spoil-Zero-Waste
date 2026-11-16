"""Route API modul Recipe Alchemist. Di-include di PantryNecromancer/urls.py pada /api/recipes/."""
from django.urls import path  # noqa: F401

from recipe_alchemist import api_views  # noqa: F401

app_name = 'recipe_alchemist_api'

urlpatterns = [
    # TODO (Checkpoint 1): buka komentar setelah view-nya dibuat di api_views.py
    # path('', api_views.recipe_list, name='recipe-list'),
    # path('<int:pk>/', api_views.recipe_detail, name='recipe-detail'),
]
