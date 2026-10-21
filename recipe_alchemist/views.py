from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from death_clock.models import PantryItem
from .forms import RecipeForm, SaveApiRecipeForm, SearchForm
from .models import Recipe
from .services import SpoonacularError, find_by_ingredients


def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def login_required_ajax(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        if is_ajax(request):
            return JsonResponse(
                {'ok': False, 'detail': 'Silakan masuk terlebih dahulu.', 'login_url': reverse('main:login')},
                status=401,
            )
        return redirect_to_login(request.get_full_path())
    return wrapper


# ---------- Cari (Spoonacular) ----------
@require_GET
def recipe_list(request):
    form = SearchForm(request.GET or None)
    results, error, searched = [], None, False

    if request.GET and form.is_valid():
        names = form.cleaned_data['ingredients'].split(',')
        if form.cleaned_data['use_pantry'] and request.user.is_authenticated:
            names += list(
                PantryItem.objects.filter(user=request.user).active().values_list('name', flat=True)
            )
        searched = True
        try:
            results = find_by_ingredients(
                names,
                max_minutes=form.cleaned_data['max_minutes'],
                diet=form.cleaned_data['diet'],
            )
        except SpoonacularError as exc:
            error = str(exc)

    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(
            Recipe.objects.filter(user=request.user, spoonacular_id__isnull=False)
            .values_list('spoonacular_id', flat=True)
        )

    return render(request, 'recipe_alchemist/recipe_list.html', {
        'form': form, 'results': results, 'error': error, 'searched': searched, 'saved_ids': saved_ids,
    })


# ---------- Read ----------
def _collection(request, queryset, scope):
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(Q(title__icontains=q) | Q(ingredients__icontains=q))
    return render(request, 'recipe_alchemist/recipe_collection.html', {
        'recipes': queryset.select_related('user'), 'scope': scope, 'q': q,
    })


@require_GET
@login_required
def my_recipes(request):
    return _collection(request, Recipe.objects.filter(user=request.user), 'mine')


@require_GET
def community_recipes(request):
    return _collection(request, Recipe.objects.filter(is_public=True), 'community')


@require_GET
def recipe_detail(request, pk):
    visible = Q(is_public=True)
    if request.user.is_authenticated:
        visible |= Q(user=request.user)
    recipe = get_object_or_404(Recipe.objects.select_related('user').filter(visible), pk=pk)
    return render(request, 'recipe_alchemist/recipe_detail.html', {
        'recipe': recipe, 'is_owner': recipe.user_id == getattr(request.user, 'id', None),
    })


# ---------- Create ----------
@require_http_methods(['GET', 'POST'])
@login_required
def recipe_create(request):
    form = RecipeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        recipe = form.save(commit=False)
        recipe.user = request.user
        recipe.save()
        messages.success(request, f'{recipe.title} dibuat.')
        return redirect('recipe_alchemist:recipe_detail', pk=recipe.pk)
    return render(request, 'recipe_alchemist/recipe_form.html', {'form': form, 'title': 'Resep baru'})


@require_POST
@login_required_ajax
def recipe_save_api(request):
    form = SaveApiRecipeForm(request.POST)
    if not form.is_valid():
        if is_ajax(request):
            return JsonResponse({'ok': False, 'detail': 'Data resep tidak valid.'}, status=400)
        messages.error(request, 'Data resep tidak valid.')
        return redirect('recipe_alchemist:recipe_list')

    data = form.cleaned_data
    recipe, created = Recipe.objects.get_or_create(
        user=request.user,
        spoonacular_id=data['spoonacular_id'],
        defaults={**{k: v for k, v in data.items() if k != 'spoonacular_id'},
                  'source': Recipe.Source.SPOONACULAR},
    )
    message = f'{recipe.title} disimpan ke koleksimu.' if created else f'{recipe.title} sudah ada di koleksimu.'
    if is_ajax(request):
        return JsonResponse({'ok': True, 'created': created, 'message': message,
                             'url': reverse('recipe_alchemist:recipe_detail', args=[recipe.pk])},
                            status=201 if created else 200)
    messages.success(request, message)
    return redirect('recipe_alchemist:my_recipes')


# ---------- Update ----------
@require_http_methods(['GET', 'POST'])
@login_required
def recipe_update(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    form = RecipeForm(request.POST or None, instance=recipe)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{recipe.title} diperbarui.')
        return redirect('recipe_alchemist:recipe_detail', pk=recipe.pk)
    return render(request, 'recipe_alchemist/recipe_form.html', {
        'form': form, 'title': f'Ubah {recipe.title}', 'recipe': recipe,
    })


# ---------- Delete ----------
@require_POST
@login_required
def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    title = recipe.title
    recipe.delete()
    messages.success(request, f'{title} dihapus.')
    return redirect('recipe_alchemist:my_recipes')