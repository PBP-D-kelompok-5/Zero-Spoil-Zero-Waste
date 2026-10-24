from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from death_clock.models import PantryItem
from recipe_alchemist import services
from recipe_alchemist.forms import RecipeForm, SaveApiRecipeForm, SearchForm
from recipe_alchemist.models import Recipe
from recipe_alchemist.services import SpoonacularError, find_by_ingredients, to_english

User = get_user_model()
AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


def fake_response(status=200, payload=None):
    response = Mock()
    response.status_code = status
    response.json.return_value = payload if payload is not None else {}
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


def api_result(recipe_id=1, title='Egg Fried Rice', **overrides):
    result = {
        'id': recipe_id, 'title': title, 'image': '', 'used': ['eggs'], 'missed': ['soy sauce'],
        'ingredients': ['eggs', 'soy sauce'], 'minutes': 20, 'diets': [], 'source_url': 'https://example.com/r',
    }
    result.update(overrides)
    return result


# ---------------------------------------------------------------- services
class ToEnglishTests(SimpleTestCase):
    def test_translates_known_names(self):
        self.assertEqual(to_english('telur'), 'egg')
        self.assertEqual(to_english('bawang putih'), 'garlic')

    def test_ignores_case_and_whitespace(self):
        self.assertEqual(to_english('  Bayam '), 'spinach')

    def test_unknown_names_pass_through_lowercased(self):
        self.assertEqual(to_english('Quinoa'), 'quinoa')


@override_settings(SPOONACULAR_API_KEY='test-key')
class GetTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(SPOONACULAR_API_KEY=None)
    def test_missing_key_raises(self):
        with self.assertRaisesMessage(SpoonacularError, 'belum diatur'):
            services._get('/x', {})

    @patch('recipe_alchemist.services.requests.get')
    def test_quota_exhausted_message(self, mock_get):
        mock_get.return_value = fake_response(402)
        with self.assertRaisesMessage(SpoonacularError, 'Kuota harian'):
            services._get('/quota', {})

    @patch('recipe_alchemist.services.requests.get')
    def test_rejected_key_message(self, mock_get):
        mock_get.return_value = fake_response(401)
        with self.assertRaisesMessage(SpoonacularError, 'ditolak'):
            services._get('/auth', {})

    @patch('recipe_alchemist.services.requests.get')
    def test_other_http_error_includes_status_code(self, mock_get):
        mock_get.return_value = fake_response(500)
        with self.assertRaisesMessage(SpoonacularError, '500'):
            services._get('/server-error', {})

    @patch('recipe_alchemist.services.requests.get', side_effect=requests.Timeout)
    def test_timeout_message(self, _):
        with self.assertRaisesMessage(SpoonacularError, 'terlalu lama'):
            services._get('/slow', {})

    @patch('recipe_alchemist.services.requests.get', side_effect=requests.ConnectionError)
    def test_connection_error_message(self, _):
        with self.assertRaisesMessage(SpoonacularError, 'tidak dapat dihubungi'):
            services._get('/offline', {})

    @patch('recipe_alchemist.services.requests.get')
    def test_successful_responses_are_cached(self, mock_get):
        mock_get.return_value = fake_response(200, [{'id': 1}])
        first = services._get('/cached', {'a': 1})
        second = services._get('/cached', {'a': 1})
        self.assertEqual(first, second)
        self.assertEqual(mock_get.call_count, 1)

    @patch('recipe_alchemist.services.requests.get')
    def test_different_params_are_cached_separately(self, mock_get):
        mock_get.return_value = fake_response(200, [])
        services._get('/cached', {'a': 1})
        services._get('/cached', {'a': 2})
        self.assertEqual(mock_get.call_count, 2)

    @patch('recipe_alchemist.services.requests.get')
    def test_errors_are_not_cached(self, mock_get):
        mock_get.side_effect = [fake_response(402), fake_response(200, {'ok': True})]
        with self.assertRaises(SpoonacularError):
            services._get('/retry', {})
        self.assertEqual(services._get('/retry', {}), {'ok': True})


class FindByIngredientsTests(SimpleTestCase):
    FOUND = [
        {'id': 1, 'title': 'Fast Vegan Bowl', 'image': 'a.jpg',
         'usedIngredients': [{'name': 'rice'}], 'missedIngredients': [{'name': 'tofu'}]},
        {'id': 2, 'title': 'Slow Egg Pie', 'image': 'b.jpg',
         'usedIngredients': [{'name': 'eggs'}], 'missedIngredients': []},
        {'id': 3, 'title': 'Unknown Time Salad', 'image': '',
         'usedIngredients': [{'name': 'spinach'}], 'missedIngredients': []},
    ]
    INFO = [
        {'id': 1, 'readyInMinutes': 15, 'diets': ['Vegan', 'Gluten Free'], 'sourceUrl': 'https://x/1'},
        {'id': 2, 'readyInMinutes': 90, 'diets': [], 'sourceUrl': 'https://x/2'},
        {'id': 3, 'diets': ['vegan'], 'sourceUrl': 'https://x/3'},
    ]

    def run_search(self, **kwargs):
        with patch('recipe_alchemist.services._get', side_effect=[self.FOUND, self.INFO]) as mock_get:
            results = find_by_ingredients(['telur', 'nasi'], **kwargs)
        return results, mock_get

    @patch('recipe_alchemist.services._get')
    def test_empty_ingredients_skip_the_api(self, mock_get):
        self.assertEqual(find_by_ingredients(['', '  ']), [])
        mock_get.assert_not_called()

    def test_ingredients_are_translated_deduplicated_and_sorted(self):
        _, mock_get = self.run_search()
        self.assertEqual(mock_get.call_args_list[0].args[1]['ingredients'], 'egg,rice')

    def test_result_shape(self):
        results, _ = self.run_search()
        first = results[0]
        self.assertEqual(first['id'], 1)
        self.assertEqual(first['used'], ['rice'])
        self.assertEqual(first['missed'], ['tofu'])
        self.assertEqual(first['ingredients'], ['rice', 'tofu'])
        self.assertEqual(first['minutes'], 15)
        self.assertEqual(first['diets'], ['vegan', 'gluten free'])
        self.assertEqual(first['source_url'], 'https://x/1')

    def test_no_filters_returns_everything(self):
        results, _ = self.run_search()
        self.assertEqual([r['id'] for r in results], [1, 2, 3])

    def test_max_minutes_filters_slow_but_keeps_unknown_time(self):
        results, _ = self.run_search(max_minutes=30)
        self.assertEqual([r['id'] for r in results], [1, 3])

    def test_diet_filter(self):
        results, _ = self.run_search(diet='vegan')
        self.assertEqual([r['id'] for r in results], [1, 3])

    def test_number_caps_results(self):
        results, _ = self.run_search(number=1)
        self.assertEqual(len(results), 1)

    @patch('recipe_alchemist.services._get', return_value=[])
    def test_no_matches_skips_details_call(self, mock_get):
        self.assertEqual(find_by_ingredients(['telur']), [])
        self.assertEqual(mock_get.call_count, 1)


# ------------------------------------------------------------------ model
class RecipeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pw12345!')

    def test_ingredient_list_skips_blank_lines(self):
        recipe = Recipe(ingredients='2 butir telur\n\n  nasi  \n')
        self.assertEqual(recipe.ingredient_list, ['2 butir telur', 'nasi'])

    def test_same_api_recipe_cannot_be_saved_twice_by_one_user(self):
        Recipe.objects.create(user=self.user, title='A', ingredients='x', spoonacular_id=5)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Recipe.objects.create(user=self.user, title='A again', ingredients='x', spoonacular_id=5)

    def test_different_users_can_save_the_same_api_recipe(self):
        other = User.objects.create_user('bob', password='pw12345!')
        Recipe.objects.create(user=self.user, title='A', ingredients='x', spoonacular_id=5)
        Recipe.objects.create(user=other, title='A', ingredients='x', spoonacular_id=5)
        self.assertEqual(Recipe.objects.filter(spoonacular_id=5).count(), 2)

    def test_custom_recipes_without_api_id_do_not_collide(self):
        Recipe.objects.create(user=self.user, title='One', ingredients='x')
        Recipe.objects.create(user=self.user, title='Two', ingredients='y')
        self.assertEqual(Recipe.objects.filter(user=self.user).count(), 2)


# ------------------------------------------------------------------ forms
class FormTests(TestCase):
    def test_search_form_allows_empty_input(self):
        self.assertTrue(SearchForm({}).is_valid())

    def test_search_form_rejects_out_of_range_minutes(self):
        self.assertFalse(SearchForm({'max_minutes': 1}).is_valid())
        self.assertFalse(SearchForm({'max_minutes': 999}).is_valid())

    def test_search_form_rejects_unknown_diet(self):
        self.assertFalse(SearchForm({'diet': 'carnivore'}).is_valid())

    def test_recipe_form_strips_title(self):
        form = RecipeForm({'title': '  Nasi Goreng  ', 'ingredients': 'nasi'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['title'], 'Nasi Goreng')

    def test_recipe_form_requires_title_and_ingredients(self):
        form = RecipeForm({})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('ingredients', form.errors)

    def test_recipe_form_rejects_zero_cook_time(self):
        form = RecipeForm({'title': 'A', 'ingredients': 'x', 'cook_time_minutes': 0})
        self.assertFalse(form.is_valid())

    def test_save_api_form_joins_pipe_separated_ingredients(self):
        form = SaveApiRecipeForm({'spoonacular_id': 7, 'title': 'A', 'ingredients': 'eggs| rice |soy'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['ingredients'], 'eggs\nrice\nsoy')

    def test_save_api_form_rejects_blank_ingredients(self):
        self.assertFalse(SaveApiRecipeForm({'spoonacular_id': 7, 'title': 'A', 'ingredients': '|||'}).is_valid())

    def test_save_api_form_rejects_invalid_id(self):
        self.assertFalse(SaveApiRecipeForm({'spoonacular_id': 0, 'title': 'A', 'ingredients': 'x'}).is_valid())


# ------------------------------------------------------------------ views
class ViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('alice', password='pw12345!')
        cls.other = User.objects.create_user('bob', password='pw12345!')

    def make_recipe(self, user=None, **kwargs):
        defaults = {'title': 'Nasi Goreng Telur', 'ingredients': '2 butir telur\nnasi'}
        defaults.update(kwargs)
        return Recipe.objects.create(user=user or self.user, **defaults)

    def assertRequiresLogin(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('main:login'), response['Location'])


class SearchViewTests(ViewTestCase):
    url = reverse('recipe_alchemist:recipe_list')

    def test_page_loads_without_search(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['searched'])

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[api_result()])
    def test_search_passes_filters_and_shows_results(self, mock_find):
        response = self.client.get(self.url, {'ingredients': 'telur, nasi', 'max_minutes': 30, 'diet': 'vegan'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['results'][0]['title'], 'Egg Fried Rice')
        names, = mock_find.call_args.args
        self.assertEqual([n.strip() for n in names], ['telur', 'nasi'])
        self.assertEqual(mock_find.call_args.kwargs, {'max_minutes': 30, 'diet': 'vegan'})

    @patch('recipe_alchemist.views.find_by_ingredients', side_effect=SpoonacularError('Kuota harian habis'))
    def test_api_error_is_shown_without_crashing(self, _):
        response = self.client.get(self.url, {'ingredients': 'telur'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['error'], 'Kuota harian habis')
        self.assertContains(response, 'Kuota harian habis')

    @patch('recipe_alchemist.views.find_by_ingredients', side_effect=SpoonacularError('down'))
    def test_local_results_still_show_when_api_fails(self, _):
        self.make_recipe()
        response = self.client.get(self.url, {'ingredients': 'telur'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['local_results'], [])  # guest: private recipe hidden
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'ingredients': 'telur'})
        self.assertEqual(len(response.context['local_results']), 1)

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[])
    def test_search_includes_own_private_and_public_community_recipes(self, _):
        own_private = self.make_recipe(title='Mine')
        community = self.make_recipe(self.other, title='Theirs public', is_public=True)
        self.make_recipe(self.other, title='Theirs private')
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'ingredients': 'telur'})
        self.assertCountEqual(response.context['local_results'], [own_private, community])

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[])
    def test_search_matches_english_ingredient_text(self, _):
        saved = self.make_recipe(title='Saved API recipe', ingredients='eggs\nrice')
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'ingredients': 'telur'})
        self.assertEqual(list(response.context['local_results']), [saved])

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[])
    def test_local_results_are_ranked_by_matched_ingredients(self, _):
        one = self.make_recipe(title='One match', ingredients='telur')
        two = self.make_recipe(title='Two matches', ingredients='telur\nnasi')
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'ingredients': 'telur, nasi'})
        self.assertEqual(list(response.context['local_results']), [two, one])
        self.assertEqual(response.context['local_results'][0].matched, ['nasi', 'telur'])

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[])
    def test_local_diet_filter(self, _):
        vegan = self.make_recipe(title='Vegan', diet='vegan')
        self.make_recipe(title='No diet')
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'ingredients': 'telur', 'diet': 'vegan'})
        self.assertEqual(list(response.context['local_results']), [vegan])

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[])
    def test_local_time_filter_keeps_recipes_without_cook_time(self, _):
        fast = self.make_recipe(title='Fast', cook_time_minutes=20)
        unknown = self.make_recipe(title='Unknown')
        self.make_recipe(title='Slow', cook_time_minutes=60)
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'ingredients': 'telur', 'max_minutes': 30})
        self.assertCountEqual(response.context['local_results'], [fast, unknown])

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[api_result(recipe_id=111)])
    def test_saved_api_recipe_is_not_listed_twice(self, _):
        self.make_recipe(title='Saved copy', ingredients='eggs', spoonacular_id=111)
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'ingredients': 'eggs'})
        self.assertEqual(response.context['local_results'], [])
        self.assertIn(111, response.context['saved_ids'])
        self.assertContains(response, 'Tersimpan')

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[])
    def test_pantry_items_are_added_to_search(self, mock_find):
        soon = timezone.localdate() + timedelta(days=2)
        PantryItem.objects.create(user=self.user, name='Bayam', expiry_date=soon)
        PantryItem.objects.create(user=self.user, name='Wortel', expiry_date=soon, resurrected_at=timezone.now())
        PantryItem.objects.create(user=self.other, name='Keju', expiry_date=soon)
        self.client.force_login(self.user)
        self.client.get(self.url, {'ingredients': 'telur', 'use_pantry': 'on'})
        names = mock_find.call_args.args[0]
        self.assertIn('Bayam', names)
        self.assertNotIn('Wortel', names)  # sudah diolah
        self.assertNotIn('Keju', names)    # milik pengguna lain

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[])
    def test_pantry_not_used_when_unchecked_or_guest(self, mock_find):
        PantryItem.objects.create(
            user=self.user, name='Bayam', expiry_date=timezone.localdate() + timedelta(days=2)
        )
        self.client.force_login(self.user)
        self.client.get(self.url, {'ingredients': 'telur'})
        self.assertNotIn('Bayam', mock_find.call_args.args[0])
        self.client.logout()
        self.client.get(self.url, {'ingredients': 'telur', 'use_pantry': 'on'})
        self.assertNotIn('Bayam', mock_find.call_args.args[0])

    @patch('recipe_alchemist.views.find_by_ingredients', return_value=[])
    def test_no_match_message(self, _):
        response = self.client.get(self.url, {'ingredients': 'durian'})
        self.assertContains(response, 'Tidak ada resep yang cocok')


class CollectionViewTests(ViewTestCase):
    def test_my_recipes_shows_guest_page(self):
        url = reverse('recipe_alchemist:my_recipes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recipe_alchemist/guest.html')
        self.assertContains(response, f"{reverse('main:login')}?next={url}")

    def test_my_recipes_guest_ajax_gets_401(self):
        response = self.client.get(reverse('recipe_alchemist:my_recipes'), **AJAX)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['login_url'], reverse('main:login'))

    def test_community_shows_login_cta_to_guests(self):
        response = self.client.get(reverse('recipe_alchemist:community_recipes'))
        self.assertContains(response, 'Masuk untuk menulis resep')

    def test_my_recipes_lists_only_own_recipes(self):
        mine = self.make_recipe(title='Mine')
        self.make_recipe(self.other, title='Theirs', is_public=True)
        self.client.force_login(self.user)
        response = self.client.get(reverse('recipe_alchemist:my_recipes'))
        self.assertEqual(list(response.context['recipes']), [mine])

    def test_community_is_open_to_guests_and_public_only(self):
        public = self.make_recipe(self.other, title='Public', is_public=True)
        self.make_recipe(self.other, title='Private')
        response = self.client.get(reverse('recipe_alchemist:community_recipes'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['recipes']), [public])

    def test_community_includes_own_public_recipes(self):
        mine = self.make_recipe(title='My public', is_public=True)
        self.client.force_login(self.user)
        response = self.client.get(reverse('recipe_alchemist:community_recipes'))
        self.assertIn(mine, response.context['recipes'])

    def test_collection_search_matches_title_and_ingredients(self):
        by_title = self.make_recipe(title='Sup Ayam', ingredients='kaldu')
        by_ingredient = self.make_recipe(title='Lainnya', ingredients='1 ekor ayam')
        self.make_recipe(title='Tempe goreng', ingredients='tempe')
        self.client.force_login(self.user)
        response = self.client.get(reverse('recipe_alchemist:my_recipes'), {'q': 'ayam'})
        self.assertCountEqual(response.context['recipes'], [by_title, by_ingredient])


class DetailViewTests(ViewTestCase):
    def url(self, recipe):
        return reverse('recipe_alchemist:recipe_detail', args=[recipe.pk])

    def test_owner_sees_private_recipe_and_notes(self):
        recipe = self.make_recipe(notes='tambah cabai')
        self.client.force_login(self.user)
        response = self.client.get(self.url(recipe))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_owner'])
        self.assertContains(response, 'tambah cabai')

    def test_private_recipe_is_hidden_from_others_and_guests(self):
        recipe = self.make_recipe()
        self.assertEqual(self.client.get(self.url(recipe)).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url(recipe)).status_code, 404)

    def test_public_recipe_is_visible_but_notes_stay_private(self):
        recipe = self.make_recipe(is_public=True, notes='rahasia dapur')
        self.client.force_login(self.other)
        response = self.client.get(self.url(recipe))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_owner'])
        self.assertNotContains(response, 'rahasia dapur')

    def test_guest_can_view_public_recipe(self):
        recipe = self.make_recipe(is_public=True)
        self.assertEqual(self.client.get(self.url(recipe)).status_code, 200)

    def test_missing_recipe_is_404(self):
        self.assertEqual(self.client.get(reverse('recipe_alchemist:recipe_detail', args=[9999])).status_code, 404)


class CreateViewTests(ViewTestCase):
    url = reverse('recipe_alchemist:recipe_create')

    def test_requires_login(self):
        self.assertRequiresLogin(self.client.get(self.url))
        self.assertRequiresLogin(self.client.post(self.url, {'title': 'A', 'ingredients': 'x'}))
        self.assertEqual(Recipe.objects.count(), 0)

    def test_guest_ajax_gets_401(self):
        self.assertEqual(self.client.post(self.url, {'title': 'A', 'ingredients': 'x'}, **AJAX).status_code, 401)

    def test_form_page_loads(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_valid_post_creates_recipe_owned_by_user(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            'title': 'Telur Dadar', 'ingredients': '2 butir telur', 'cook_time_minutes': 10, 'is_public': 'on',
        })
        recipe = Recipe.objects.get()
        self.assertRedirects(
            response, reverse('recipe_alchemist:recipe_detail', args=[recipe.pk]), fetch_redirect_response=False
        )
        self.assertEqual(recipe.user, self.user)
        self.assertEqual(recipe.source, Recipe.Source.CUSTOM)
        self.assertTrue(recipe.is_public)

    def test_invalid_post_creates_nothing_and_shows_errors(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'title': '', 'ingredients': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Recipe.objects.count(), 0)
        self.assertTrue(response.context['form'].errors)


class UpdateViewTests(ViewTestCase):
    def url(self, recipe):
        return reverse('recipe_alchemist:recipe_update', args=[recipe.pk])

    def test_requires_login(self):
        self.assertRequiresLogin(self.client.get(self.url(self.make_recipe())))

    def test_owner_can_update(self):
        recipe = self.make_recipe()
        self.client.force_login(self.user)
        response = self.client.post(self.url(recipe), {'title': 'Baru', 'ingredients': 'x', 'notes': 'catatan'})
        self.assertEqual(response.status_code, 302)
        recipe.refresh_from_db()
        self.assertEqual((recipe.title, recipe.notes), ('Baru', 'catatan'))

    def test_owner_can_make_recipe_public(self):
        recipe = self.make_recipe()
        self.client.force_login(self.user)
        self.client.post(self.url(recipe), {'title': recipe.title, 'ingredients': 'x', 'is_public': 'on'})
        recipe.refresh_from_db()
        self.assertTrue(recipe.is_public)

    def test_other_users_cannot_update_even_public_recipes(self):
        recipe = self.make_recipe(is_public=True)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url(recipe)).status_code, 404)
        self.assertEqual(self.client.post(self.url(recipe), {'title': 'Hacked', 'ingredients': 'x'}).status_code, 404)
        recipe.refresh_from_db()
        self.assertNotEqual(recipe.title, 'Hacked')

    def test_invalid_update_keeps_old_data(self):
        recipe = self.make_recipe()
        self.client.force_login(self.user)
        response = self.client.post(self.url(recipe), {'title': '', 'ingredients': 'x'})
        self.assertEqual(response.status_code, 200)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, 'Nasi Goreng Telur')


class DeleteViewTests(ViewTestCase):
    def url(self, recipe):
        return reverse('recipe_alchemist:recipe_delete', args=[recipe.pk])

    def test_owner_can_delete_with_post(self):
        recipe = self.make_recipe()
        self.client.force_login(self.user)
        response = self.client.post(self.url(recipe))
        self.assertRedirects(response, reverse('recipe_alchemist:my_recipes'), fetch_redirect_response=False)
        self.assertFalse(Recipe.objects.filter(pk=recipe.pk).exists())

    def test_get_is_not_allowed(self):
        recipe = self.make_recipe()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url(recipe)).status_code, 405)
        self.assertTrue(Recipe.objects.filter(pk=recipe.pk).exists())

    def test_other_users_cannot_delete(self):
        recipe = self.make_recipe(is_public=True)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url(recipe)).status_code, 404)
        self.assertTrue(Recipe.objects.filter(pk=recipe.pk).exists())

    def test_guest_is_redirected_to_login(self):
        recipe = self.make_recipe()
        self.assertRequiresLogin(self.client.post(self.url(recipe)))
        self.assertTrue(Recipe.objects.filter(pk=recipe.pk).exists())


class SaveApiRecipeViewTests(ViewTestCase):
    url = reverse('recipe_alchemist:recipe_save_api')
    payload = {
        'spoonacular_id': 641890, 'title': 'Easy Cheesy Scrambled Eggs',
        'image_url': 'https://img.spoonacular.com/recipes/641890-312x231.jpg',
        'source_url': 'https://www.foodista.com/recipe/X5JCHLYL/easy-cheesy-scrambled-eggs',
        'cook_time_minutes': 45, 'ingredients': 'eggs|milk|jack cheese',
    }

    def test_guest_ajax_gets_401_json_with_login_url(self):
        response = self.client.post(self.url, self.payload, **AJAX)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['login_url'], reverse('main:login'))
        self.assertEqual(Recipe.objects.count(), 0)

    def test_guest_plain_post_redirects_to_login(self):
        self.assertRequiresLogin(self.client.post(self.url, self.payload))

    def test_get_is_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_ajax_save_creates_spoonacular_recipe(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.payload, **AJAX)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['ok'] and data['created'])
        recipe = Recipe.objects.get()
        self.assertEqual(data['url'], reverse('recipe_alchemist:recipe_detail', args=[recipe.pk]))
        self.assertEqual(recipe.user, self.user)
        self.assertEqual(recipe.source, Recipe.Source.SPOONACULAR)
        self.assertEqual(recipe.spoonacular_id, 641890)
        self.assertEqual(recipe.ingredient_list, ['eggs', 'milk', 'jack cheese'])
        self.assertEqual(recipe.cook_time_minutes, 45)
        self.assertFalse(recipe.is_public)

    def test_saving_twice_does_not_duplicate(self):
        self.client.force_login(self.user)
        self.client.post(self.url, self.payload, **AJAX)
        response = self.client.post(self.url, self.payload, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['created'])
        self.assertEqual(Recipe.objects.count(), 1)

    def test_two_users_can_each_save_the_same_recipe(self):
        self.client.force_login(self.user)
        self.client.post(self.url, self.payload, **AJAX)
        self.client.force_login(self.other)
        self.client.post(self.url, self.payload, **AJAX)
        self.assertEqual(Recipe.objects.count(), 2)

    def test_invalid_ajax_payload_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'title': 'No id', 'ingredients': 'x'}, **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])
        self.assertEqual(Recipe.objects.count(), 0)

    def test_plain_post_saves_and_redirects_to_collection(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.payload)
        self.assertRedirects(response, reverse('recipe_alchemist:my_recipes'), fetch_redirect_response=False)
        self.assertEqual(Recipe.objects.count(), 1)

    def test_plain_post_with_invalid_data_redirects_back_to_search(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'title': 'No id', 'ingredients': 'x'})
        self.assertRedirects(response, reverse('recipe_alchemist:recipe_list'), fetch_redirect_response=False)