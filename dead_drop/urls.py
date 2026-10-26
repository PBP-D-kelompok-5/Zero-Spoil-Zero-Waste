from django.urls import path

from . import views

app_name = 'dead_drop'

urlpatterns = [
    path('', views.listing_board, name='listing_board'),
    path("create/", views.create_listing, name="create_listing"),
    path("<int:listing_id>/reserve/", views.reserve_listing, name="reserve_listing",),
    path("<int:listing_id>/cancel-reservation/", views.cancel_reserve_listing, name="cancel_reserve_listing",),
    path("<int:listing_id>/claim-reservation/", views.claim_listing, name="claim_listing",),
]