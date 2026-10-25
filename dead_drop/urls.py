from django.urls import path

from . import views

app_name = 'dead_drop'

urlpatterns = [
    path('', views.listing_board, name='listing_board'),
]