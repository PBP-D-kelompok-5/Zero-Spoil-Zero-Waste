"""Views Pantry Death Clock.

Setiap aksi bisa dipakai dua cara:
* biasa (form HTML, tanpa JavaScript) -> redirect + pesan flash;
* AJAX (header X-Requested-With: XMLHttpRequest) -> JsonResponse, dipakai
  static/death_clock/death_clock.js agar halaman tidak dimuat ulang.
Endpoint /json/ mengembalikan data mentah untuk web service (Flutter nanti).
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from death_clock.forms import BulkAddForm, FilterForm, PantryItemForm, QuantityForm
from death_clock.models import CRITICAL_DAYS, STATUS_TONES, PantryItem, Status

LIST_URL = 'death_clock:pantry_list'


# ---------- Helper ----------
def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def login_required_ajax(view):
    """Seperti @login_required, tetapi permintaan AJAX/JSON mendapat 401 JSON, bukan redirect."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        if is_ajax(request) or request.path.startswith(reverse('death_clock:pantry_json')):
            return JsonResponse(
                {'ok': False, 'detail': 'Silakan masuk terlebih dahulu.', 'login_url': reverse('main:login')},
                status=401,
            )
        return redirect_to_login(request.get_full_path())

    return wrapper


def user_items(request):
    return PantryItem.objects.filter(user=request.user)


def get_user_item(request, pk):
    # Bahan milik pengguna lain dianggap tidak ada (404), bukan 403, agar keberadaannya tidak bocor.
    return get_object_or_404(PantryItem, pk=pk, user=request.user)


def filter_items(queryset, values):
    status = values['status']
    queryset = queryset.with_status(status)
    if status == Status.RESURRECTED:
        queryset = queryset.order_by('-resurrected_at')
    if values['q']:
        queryset = queryset.filter(Q(name__icontains=values['q']) | Q(notes__icontains=values['q']))
    if values['category']:
        queryset = queryset.filter(category=values['category'])
    if values['storage']:
        queryset = queryset.filter(storage=values['storage'])
    return queryset


def status_tiles(counts):
    return [
        {'status': status, 'label': Status(status).label, 'hint': hint, 'tone': STATUS_TONES[status], 'count': counts[status]}
        for status, hint in (
            (Status.FLATLINING, 'Hari ini atau sudah lewat'),
            (Status.CRITICAL, f'Sisa 1–{CRITICAL_DAYS} hari'),
            (Status.STABLE, f'Lebih dari {CRITICAL_DAYS} hari'),
            (Status.RESURRECTED, 'Sudah diolah'),
        )
    ]


def list_context(request):
    filter_form = FilterForm(request.GET)
    values = filter_form.values
    items = list(filter_items(user_items(request), values))
    counts = user_items(request).status_counts()
    return {
        'items': items,
        'counts': counts,
        'tiles': status_tiles(counts),
        'filter_form': filter_form,
        'filters': values,
        'is_filtered': any(values.values()),
        'critical_days': CRITICAL_DAYS,
    }


def render_card(request, item):
    return render_to_string('death_clock/partials/item_card.html', {'item': item}, request=request)


def action_response(request, message, item=None, status=200, tone='ecto'):
    """Respons standar untuk aksi: JSON jika AJAX, selain itu redirect ke daftar + pesan flash."""
    if is_ajax(request):
        payload = {'ok': True, 'message': message, 'tone': tone, 'counts': user_items(request).status_counts()}
        if item is not None:
            payload['item'] = item.to_dict()
            payload['html'] = render_card(request, item)
        return JsonResponse(payload, status=status)
    messages.success(request, message)
    return redirect(LIST_URL)


def form_response(request, form, template_context):
    """GET form / POST tidak valid: fragmen HTML untuk modal (AJAX) atau halaman penuh."""
    context = {'form': form, **template_context}
    if is_ajax(request):
        html = render_to_string('death_clock/partials/item_form.html', context, request=request)
        return JsonResponse({'ok': not form.errors, 'html': html}, status=400 if form.errors else 200)
    return render(request, 'death_clock/item_form_page.html', context)


# ---------- Read ----------
@require_GET
def pantry_list(request):
    if not request.user.is_authenticated:
        # Tamu hanya melihat penjelasan modul; inventaris bersifat privat.
        return render(request, 'death_clock/guest.html', {'critical_days': CRITICAL_DAYS})

    context = list_context(request)
    if is_ajax(request):
        html = render_to_string('death_clock/partials/item_list.html', context, request=request)
        return JsonResponse({'html': html, 'counts': context['counts'], 'count': len(context['items'])})
    return render(request, 'death_clock/pantry_list.html', context)


@require_GET
@login_required_ajax
def pantry_json(request):
    values = FilterForm(request.GET).values
    items = filter_items(user_items(request), values)
    return JsonResponse({
        'count': len(items),
        'counts': user_items(request).status_counts(),
        'items': [item.to_dict() for item in items],
    })


@require_GET
@login_required_ajax
def item_json(request, pk):
    return JsonResponse(get_user_item(request, pk).to_dict())


# ---------- Create ----------
@require_http_methods(['GET', 'POST'])
@login_required_ajax
def item_create(request):
    form = PantryItemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.user = request.user
        item.save()
        return action_response(request, f'{item.name} masuk ke Death Clock.', item=item, status=201)
    return form_response(request, form, {
        'title': 'Tambah bahan',
        'action': reverse('death_clock:item_create'),
        'submit_label': 'Simpan bahan',
    })


@require_http_methods(['GET', 'POST'])
@login_required_ajax
def item_bulk_create(request):
    form = BulkAddForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        items = form.save(request.user)
        return action_response(request, f'{len(items)} bahan masuk ke Death Clock.', status=201)
    return form_response(request, form, {
        'title': 'Tambah massal',
        'action': reverse('death_clock:item_bulk_create'),
        'submit_label': 'Tambahkan semua',
        'is_bulk': True,
    })


# ---------- Update ----------
@require_http_methods(['GET', 'POST'])
@login_required_ajax
def item_update(request, pk):
    item = get_user_item(request, pk)
    form = PantryItemForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        return action_response(request, f'{item.name} diperbarui.', item=item)
    return form_response(request, form, {
        'title': f'Ubah {item.name}',
        'action': reverse('death_clock:item_update', args=[item.pk]),
        'submit_label': 'Simpan perubahan',
        'item': item,
    })


@require_POST
@login_required_ajax
def item_quantity(request, pk):
    item = get_user_item(request, pk)
    form = QuantityForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'detail': 'Perubahan jumlah tidak valid.'}, status=400)
    item.quantity = max(1, min(9999, item.quantity + form.cleaned_data['delta']))
    item.save(update_fields=['quantity', 'updated_at'])
    return action_response(request, f'Jumlah {item.name} sekarang {item.quantity} {item.get_unit_display()}.', item=item)


@require_POST
@login_required_ajax
def item_resurrect(request, pk):
    """Tandai bahan sudah diolah/dikonsumsi (Resurrected), atau batalkan tanda itu."""
    item = get_user_item(request, pk)
    if item.is_resurrected:
        item.revive()
        return action_response(request, f'{item.name} dikembalikan ke inventaris.', item=item, tone='frost')
    item.resurrect()
    return action_response(request, f'{item.name} berhasil diselamatkan. Satu bahan batal jadi sampah!', item=item, tone='hex')


# ---------- Delete ----------
@require_POST
@login_required_ajax
def item_delete(request, pk):
    item = get_user_item(request, pk)
    name = item.name
    item.delete()
    return action_response(request, f'{name} dihapus dari inventaris.', tone='blood')
