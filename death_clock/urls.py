from django.urls import path

from death_clock import views

app_name = 'death_clock'

urlpatterns = [
    path('', views.pantry_list, name='pantry_list'),
    path('add/', views.item_create, name='item_create'),
    path('bulk-add/', views.item_bulk_create, name='item_bulk_create'),
    path('<int:pk>/edit/', views.item_update, name='item_update'),
    path('<int:pk>/quantity/', views.item_quantity, name='item_quantity'),
    path('<int:pk>/resurrect/', views.item_resurrect, name='item_resurrect'),
    path('<int:pk>/delete/', views.item_delete, name='item_delete'),
    path('json/', views.pantry_json, name='pantry_json'),
    path('json/<int:pk>/', views.item_json, name='item_json'),
]
