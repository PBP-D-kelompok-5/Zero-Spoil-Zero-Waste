from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from death_clock.models import Category, PantryItem, Storage

AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


def today():
    return timezone.localdate()


def days(n):
    return today() + timedelta(days=n)


def make_user(username='necro', password='Kulkas-Bersama-2026'):
    return User.objects.create_user(username, password=password)


def make_item(user, name='Bayam', expires_in=5, bought_ago=1, **extra):
    data = {
        'user': user,
        'name': name,
        'category': Category.VEG,
        'storage': Storage.FRIDGE,
        'purchase_date': days(-bought_ago),
        'expiry_date': days(expires_in),
    }
    data.update(extra)
    return PantryItem.objects.create(**data)
