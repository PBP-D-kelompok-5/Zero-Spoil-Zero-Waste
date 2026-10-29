from django.urls import path

from . import views

app_name = 'dead_drop'

urlpatterns = [
    path('', views.listing_board, name='listing_board'),
    path("reserved/", views.listing_board, {"status": "reserved"}, name="reserved_board"),
    path("history/", views.listing_board, {"status": "claimed"}, name="claimed_history"),
    path("json/", views.listings_json, name="listings_json"),
    path("json/<int:listing_id>/", views.listing_json, name="listing_json"),
    path("create/", views.create_listing, name="create_listing"),
    path("<int:listing_id>/reserve/", views.reserve_listing, name="reserve_listing",),
    path("<int:listing_id>/cancel/", views.cancel_reserve_listing, name="cancel_reserve_listing",),
    path("<int:listing_id>/claim/", views.claim_listing, name="claim_listing",),
    path("<int:listing_id>/edit/", views.edit_listing, name="edit_listing",),
    path("<int:listing_id>/delete/", views.delete_listing, name="delete_listing",),
    path("geocode/", views.geocode_location, name="geocode_location"),
]