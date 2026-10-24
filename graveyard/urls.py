from django.urls import path

from graveyard import views

app_name = 'graveyard'

urlpatterns = [
    path('', views.graveyard_list, name='graveyard_list'),
    path('json/', views.graveyard_json, name='graveyard_json'),
    path('create/', views.graveyard_create, name='graveyard_create'),
    path('move/<int:pantry_item_id>/', views.move_from_death_clock, name='move_from_death_clock'),
    path('<int:pk>/edit/', views.graveyard_edit, name='graveyard_edit'),
    path('<int:pk>/delete/', views.graveyard_delete, name='graveyard_delete'),
]
