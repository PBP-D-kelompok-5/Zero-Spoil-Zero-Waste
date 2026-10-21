from django.urls import path
from . import views

app_name = 'recipe_alchemist'

urlpatterns = [
    path('', views.recipe_list, name='recipe_list'),
    path('saya/', views.my_recipes, name='my_recipes'),
    path('komunitas/', views.community_recipes, name='community_recipes'),
    path('baru/', views.recipe_create, name='recipe_create'),
    path('simpan/', views.recipe_save_api, name='recipe_save_api'),
    path('<int:pk>/', views.recipe_detail, name='recipe_detail'),
    path('<int:pk>/ubah/', views.recipe_update, name='recipe_update'),
    path('<int:pk>/hapus/', views.recipe_delete, name='recipe_delete'),
]