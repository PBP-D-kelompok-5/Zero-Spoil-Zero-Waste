from django.urls import path
from . import views

app_name = 'preservation_grimoire'

urlpatterns = [
    path('', views.grimoire_list, name='grimoire_list'),
    path('<int:pk>/', views.grimoire_detail, name='grimoire_detail'),
    path('create/', views.grimoire_create, name='grimoire_create'),
    path('<int:pk>/edit/', views.grimoire_update, name='grimoire_update'),
    path('<int:pk>/delete/', views.grimoire_delete, name='grimoire_delete'),
    path('<int:pk>/upvote/', views.toggle_upvote, name='toggle_upvote'),
]