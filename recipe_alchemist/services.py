import hashlib
import json

import requests
from django.conf import settings
from django.core.cache import cache

BASE_URL = 'https://api.spoonacular.com'

# Spoonacular memakai nama bahan bahasa Inggris; inventaris Death Clock berbahasa Indonesia.
ID_TO_EN = {
    'bayam': 'spinach', 'wortel': 'carrot', 'tomat': 'tomato', 'kangkung': 'water spinach',
    'telur': 'egg', 'ayam': 'chicken', 'daging sapi': 'beef', 'ikan': 'fish', 'udang': 'shrimp',
    'tahu': 'tofu', 'tempe': 'tempeh', 'nasi': 'rice', 'mie': 'noodles', 'roti': 'bread',
    'bawang merah': 'shallot', 'bawang putih': 'garlic', 'bawang bombay': 'onion',
    'kentang': 'potato', 'cabai': 'chili', 'jagung': 'corn', 'brokoli': 'broccoli', 'kol': 'cabbage',
    'sawi': 'bok choy', 'timun': 'cucumber', 'pisang': 'banana', 'susu': 'milk', 'keju': 'cheese',
    'mentega': 'butter', 'santan': 'coconut milk',
}

CACHE_SECONDS = 60 * 60 * 6  # 6 jam


def to_english(name):
    name = name.strip().lower()
    return ID_TO_EN.get(name, name)


class SpoonacularError(Exception):
    pass


def _get(path, params):
    if not settings.SPOONACULAR_API_KEY:
        raise SpoonacularError('API key Spoonacular belum diatur.')

    # Pencarian yang sama dalam 6 jam tidak memakai kuota lagi.
    key = 'spoon:' + hashlib.md5(f'{path}{json.dumps(params, sort_keys=True)}'.encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f'{BASE_URL}{path}',
            params={**params, 'apiKey': settings.SPOONACULAR_API_KEY},
            timeout=15,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        code = exc.response.status_code
        if code == 402:
            raise SpoonacularError('Kuota harian Spoonacular habis. Coba lagi besok.') from exc
        if code in (401, 403):
            raise SpoonacularError('API key Spoonacular ditolak.') from exc
        raise SpoonacularError(f'Spoonacular mengembalikan galat {code}.') from exc
    except requests.Timeout as exc:
        raise SpoonacularError('Spoonacular terlalu lama merespons.') from exc
    except requests.RequestException as exc:
        raise SpoonacularError('Spoonacular tidak dapat dihubungi.') from exc

    data = response.json()
    cache.set(key, data, CACHE_SECONDS)  # galat tidak disimpan di cache
    return data


def find_by_ingredients(ingredients, *, max_minutes=None, diet='', number=12):
    names = ','.join(sorted({to_english(i) for i in ingredients if i.strip()}))
    if not names:
        return []

    found = _get('/recipes/findByIngredients', {
        'ingredients': names,
        'number': 12,          # ambil sedikit lebih banyak, karena filter lokal membuang sebagian
        'ranking': 2,          # minimalkan bahan yang kurang
        'ignorePantry': 'true',
    })
    if not found:
        return []

    info = _get('/recipes/informationBulk', {'ids': ','.join(str(r['id']) for r in found)})
    extra = {i['id']: i for i in info}

    results = []
    for r in found:
        detail = extra.get(r['id'], {})
        minutes = detail.get('readyInMinutes')
        diets = [d.lower() for d in detail.get('diets', [])]
        if max_minutes and minutes and minutes > max_minutes:
            continue
        if diet and diet not in diets:
            continue
        used = [i['name'] for i in r.get('usedIngredients', [])]
        missed = [i['name'] for i in r.get('missedIngredients', [])]
        results.append({
            'id': r['id'],
            'title': r['title'],
            'image': r.get('image', ''),
            'used': used,
            'missed': missed,
            'ingredients': used + missed,
            'minutes': minutes,
            'diets': diets,
            'source_url': detail.get('sourceUrl', ''),
        })
    return results[:number]