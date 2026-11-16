from django.urls import path

from main import api_views

app_name = 'auth_api'

urlpatterns = [
    path('login/', api_views.login_api, name='login'),
    path('register/', api_views.register_api, name='register'),
    path('logout/', api_views.logout_api, name='logout'),
    path('me/', api_views.me_api, name='me'),
    path('csrf/', api_views.csrf_api, name='csrf'),
]
