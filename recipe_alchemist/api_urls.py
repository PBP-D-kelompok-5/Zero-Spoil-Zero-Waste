from django.urls import path

from . import api_views

urlpatterns = [
    path('', api_views.recipe_list, name='recipe_list'),
    path('<int:pk>/', api_views.recipe_detail, name='recipe_detail'),
]