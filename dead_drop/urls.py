from django.urls import path

from . import views

app_name = 'dead_drop'

urlpatterns = [
    path('', views.listing_board, name='listing_board'),
    path("create/", views.create_listing, name="create_listing"),
    path("<int:listing_id>/reserve/", views.reserve_listing, name="reserve_listing",),
    path("<int:listing_id>/cancel/", views.cancel_reserve_listing, name="cancel_reserve_listing",),
    path("<int:listing_id>/claim/", views.claim_listing, name="claim_listing",),
    path("<int:listing_id>/edit/", views.edit_listing, name="edit_listing",),
    path("<int:listing_id>/delete/", views.delete_listing, name="delete_listing",),
]