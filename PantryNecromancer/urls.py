"""
URL configuration for PantryNecromancer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('grimoire/', include('preservation_grimoire.urls')),
    path('dead-drop/', include('dead_drop.urls')),
    path('', include('main.urls')),
    path('death-clock/', include('death_clock.urls')),
    path('graveyard/', include('graveyard.urls')),
    path('recipes/', include('recipe_alchemist.urls')),

    # Web service DRF untuk aplikasi Flutter. Endpoint /json/ lama tetap dipakai situs web.
    path('api/auth/', include('main.api_urls')),
    path('api/death-clock/', include('death_clock.api_urls')),
    path('api/recipes/', include('recipe_alchemist.api_urls')),
    path('api/dead-drop/', include('dead_drop.api_urls')),
    path('api/graveyard/', include('graveyard.api_urls')),
    path('api/grimoire/', include('preservation_grimoire.api_urls')),
    # Login/logout untuk Browsable API DRF (cek endpoint lewat browser), seperti Tutorial 07
    path('api-auth/', include('rest_framework.urls')),
]
