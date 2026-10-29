"""Views Modul 4 · The Graveyard & Waste Analytics.

Menyediakan:
1. graveyard_list: Daftar bahan makanan yang terbuang beserta ringkasan analitik
   (total item bulan ini, kategori paling sering terbuang, total kerugian uang, dan emisi CO₂).
2. graveyard_json: Web service format JSON untuk analitik dan daftar item.
3. graveyard_create: Menambahkan catatan bahan makanan terbuang secara langsung (Create).
4. move_from_death_clock: Memindahkan item dari inventaris Death Clock ke Graveyard ketika kedaluwarsa.
5. graveyard_edit: Memperbarui data catatan nisan limbah (Update).
6. graveyard_delete: Menghapus catatan pembuangan jika terjadi kesalahan input (Delete).
"""
from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.formats import date_format
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from death_clock.models import PantryItem
from graveyard.forms import BuryForm, GraveyardItemForm
from graveyard.models import Category, DisposalReason, GraveyardItem
from graveyard.wrapped import generate_haunting_wrapped
from main.auth import guest_page, is_ajax, login_required_ajax, safe_next_url


# ---------- Helper ----------
# Alur autentikasi (login_required_ajax, guest_page) ada di main/auth.py dan dipakai semua modul.
def parse_date_param(value):
    try:
        return parse_date((value or '').strip())
    except ValueError:  # format benar tetapi tanggal mustahil, mis. 2026-02-31
        return None


def calculate_analytics(user_items):
    """Menghitung metrik analitik limbah makanan milik pengguna."""
    today = timezone.localdate()

    # 1. Total item dan kerugian bulan ini
    this_month_items = user_items.filter(
        disposed_at__year=today.year,
        disposed_at__month=today.month,
    )
    total_this_month = this_month_items.count()
    loss_this_month = this_month_items.aggregate(total=Sum('estimated_loss'))['total'] or Decimal('0.00')
    weight_this_month_g = this_month_items.aggregate(total=Sum('weight_g'))['total'] or Decimal('0.00')

    # 2. Kategori yang paling sering terbuang
    category_ranking = list(
        user_items.values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    top_category = None
    if category_ranking:
        top_code = category_ranking[0]['category']
        top_count = category_ranking[0]['count']
        top_category = {
            'code': top_code,
            'label': Category(top_code).label,
            'count': top_count,
        }

    # 3. Alasan pembuangan yang paling dominan
    reason_ranking = list(
        user_items.values('reason')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    top_reason = None
    if reason_ranking:
        reason_code = reason_ranking[0]['reason']
        top_reason = {
            'code': reason_code,
            'label': DisposalReason(reason_code).label,
            'count': reason_ranking[0]['count'],
        }

    # 4. Total akumulasi seluruh waktu
    total_items = user_items.count()
    total_loss = user_items.total_loss()
    total_weight_kg = user_items.total_weight_kg()

    # Hitung total karbon berdasarkan method estimasi item
    items_list = list(user_items)
    total_carbon_kg = sum(
        (item.estimated_carbon_kg for item in items_list),
        Decimal('0.00'),
    ).quantize(Decimal('0.01'))

    return {
        'total_this_month': total_this_month,
        'loss_this_month': float(loss_this_month),
        'weight_this_month_kg': float((weight_this_month_g / Decimal('1000.0')).quantize(Decimal('0.01'))),
        'top_category': top_category,
        'top_reason': top_reason,
        'total_items': total_items,
        'total_loss': float(total_loss),
        'total_weight_kg': float(total_weight_kg),
        'total_carbon_kg': float(total_carbon_kg),
        'month_name': date_format(today, 'F Y'),  # nama bulan berbahasa Indonesia
        'category_breakdown': [
            {'code': c['category'], 'label': Category(c['category']).label, 'count': c['count']}
            for c in category_ranking
        ],
    }


# ---------- Views ----------
@require_GET
@guest_page('graveyard/guest.html')  # riwayat pembuangan privat
def graveyard_list(request):
    """Endpoint 1: Menampilkan daftar item terbuang dan ringkasan agregasi analitik."""
    user_items = GraveyardItem.objects.filter(user=request.user)

    # Filter opsional berdasarkan kategori dan kata kunci pencarian
    category_filter = request.GET.get('category', '').strip()
    reason_filter = request.GET.get('reason', '').strip()
    query = request.GET.get('q', '').strip()

    if category_filter:
        user_items = user_items.filter(category=category_filter)
    if reason_filter:
        user_items = user_items.filter(reason=reason_filter)
    if query:
        user_items = user_items.filter(
            Q(name__icontains=query) | Q(notes__icontains=query)
        )

    # Rentang tanggal pembuangan (YYYY-MM-DD); nilai tidak valid diabaikan.
    date_from = parse_date_param(request.GET.get('date_from'))
    date_to = parse_date_param(request.GET.get('date_to'))
    if date_from and date_to and date_from > date_to:
        date_from, date_to = date_to, date_from
    if date_from:
        user_items = user_items.filter(disposed_at__gte=date_from)
    if date_to:
        user_items = user_items.filter(disposed_at__lte=date_to)

    # Analitik dihitung dari keseluruhan bahan pengguna (unfiltered untuk keakuratan metrik)
    all_user_items = GraveyardItem.objects.filter(user=request.user)
    analytics = calculate_analytics(all_user_items)
    wrapped_slides = generate_haunting_wrapped(all_user_items, analytics)

    context = {
        'items': user_items,
        'analytics': analytics,
        'wrapped_slides': wrapped_slides,
        'categories': Category.choices,
        'reasons': DisposalReason.choices,
        'selected_category': category_filter,
        'selected_reason': reason_filter,
        'search_query': query,
        'date_from': date_from.isoformat() if date_from else '',
        'date_to': date_to.isoformat() if date_to else '',
    }

    # Jika meminta format JSON atau AJAX
    if is_ajax(request):
        html = render_to_string('graveyard/partials/item_list.html', context, request=request)
        return JsonResponse({
            'ok': True,
            'count': user_items.count(),
            'html': html,
            'analytics': analytics,
            'wrapped': wrapped_slides,
            'items': [item.to_dict() for item in user_items],
        })

    return render(request, 'graveyard/graveyard_list.html', context)


@require_GET
@login_required_ajax
def graveyard_json(request):
    """Endpoint khusus untuk integrasi Web Service / Flutter API data Graveyard."""
    user_items = GraveyardItem.objects.filter(user=request.user)
    analytics = calculate_analytics(user_items)
    wrapped_slides = generate_haunting_wrapped(user_items, analytics)
    return JsonResponse({
        'ok': True,
        'count': user_items.count(),
        'analytics': analytics,
        'wrapped': wrapped_slides,
        'items': [item.to_dict() for item in user_items],
    })


@require_http_methods(['GET', 'POST'])
@login_required_ajax
def graveyard_create(request):
    """Endpoint Create: Menambahkan catatan bahan makanan terbuang secara langsung."""
    if request.method == 'POST':
        form = GraveyardItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()

            message = f'Catatan limbah "{item.name}" berhasil ditambahkan ke Graveyard.'
            if is_ajax(request):
                return JsonResponse({
                    'ok': True,
                    'message': message,
                    'graveyard_item': item.to_dict(),
                }, status=201)

            messages.success(request, message)
            return redirect(safe_next_url(request, reverse('graveyard:graveyard_list')))

        if is_ajax(request):
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

        return render(request, 'graveyard/item_form.html', {
            'form': form,
            'title': 'Catat Bahan Terbuang Baru',
            'submit_label': 'Catat ke Graveyard',
        }, status=400)

    form = GraveyardItemForm()
    return render(request, 'graveyard/item_form.html', {
        'form': form,
        'title': 'Catat Bahan Terbuang Baru',
        'submit_label': 'Catat ke Graveyard',
    })


@require_http_methods(['GET', 'POST'])
@login_required_ajax
def graveyard_edit(request, pk):
    """Endpoint Update: Memperbarui data catatan nisan limbah di Graveyard."""
    item = get_object_or_404(GraveyardItem, pk=pk, user=request.user)

    if request.method == 'POST':
        form = GraveyardItemForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            message = f'Catatan nisan "{item.name}" berhasil diperbarui.'

            if is_ajax(request):
                return JsonResponse({
                    'ok': True,
                    'message': message,
                    'graveyard_item': item.to_dict(),
                })

            messages.success(request, message)
            return redirect(safe_next_url(request, reverse('graveyard:graveyard_list')))

        if is_ajax(request):
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

        return render(request, 'graveyard/item_form.html', {
            'form': form,
            'item': item,
            'title': f'Ubah Catatan Nisan: {item.name}',
            'submit_label': 'Simpan Perubahan',
        }, status=400)

    form = GraveyardItemForm(instance=item)
    return render(request, 'graveyard/item_form.html', {
        'form': form,
        'item': item,
        'title': f'Ubah Catatan Nisan: {item.name}',
        'submit_label': 'Simpan Perubahan',
    })


@require_http_methods(['GET', 'POST'])
@login_required_ajax
def move_from_death_clock(request, pantry_item_id):
    """Endpoint 2: Memindahkan item dari 'death_clock' ke 'graveyard' ketika kedaluwarsa.
    
    Item diisolasi per pengguna; pengguna lain akan menerima respons 404.
    """
    pantry_item = get_object_or_404(PantryItem, pk=pantry_item_id, user=request.user)

    if request.method == 'POST':
        data = request.POST.copy()
        data.setdefault('notes', pantry_item.notes or '')  # klien AJAX boleh tidak mengirim catatan
        form = BuryForm(data)
        if not form.is_valid():
            detail = ' '.join(error for errors in form.errors.values() for error in errors)
            if is_ajax(request):
                return JsonResponse({'ok': False, 'detail': detail, 'errors': form.errors}, status=400)
            return render(request, 'graveyard/move_form.html', move_form_context(pantry_item, form), status=400)

        # Buat catatan di Graveyard
        graveyard_item = form.save(commit=False)
        graveyard_item.user = request.user
        graveyard_item.name = pantry_item.name
        graveyard_item.category = pantry_item.category
        graveyard_item.expiry_date = pantry_item.expiry_date
        graveyard_item.quantity = pantry_item.quantity
        graveyard_item.unit = pantry_item.unit
        graveyard_item.save()

        item_name = pantry_item.name
        # Hapus bahan dari Death Clock karena telah berakhir di Graveyard
        pantry_item.delete()

        success_message = f'"{item_name}" telah dikuburkan dan dipindahkan ke Graveyard.'

        if is_ajax(request):
            return JsonResponse({
                'ok': True,
                'message': success_message,
                'graveyard_item': graveyard_item.to_dict(),
            }, status=201)

        messages.warning(request, success_message)
        return redirect(safe_next_url(request, reverse('graveyard:graveyard_list')))

    # Permintaan GET: Menampilkan formulir konfirmasi pemindahan
    form = BuryForm(initial={'notes': pantry_item.notes})
    return render(request, 'graveyard/move_form.html', move_form_context(pantry_item, form))


def move_form_context(pantry_item, form):
    return {'pantry_item': pantry_item, 'form': form}


@require_POST
@login_required_ajax
def graveyard_delete(request, pk):
    """Menghapus entri bahan makanan dari riwayat Graveyard (koreksi data)."""
    item = get_object_or_404(GraveyardItem, pk=pk, user=request.user)
    name = item.name
    item.delete()

    message = f'Catatan "{name}" telah dihapus dari Graveyard.'
    if is_ajax(request):
        analytics = calculate_analytics(GraveyardItem.objects.filter(user=request.user))
        analytics_html = render_to_string('graveyard/partials/analytics.html', {'analytics': analytics}, request=request)
        return JsonResponse({'ok': True, 'message': message, 'analytics': analytics, 'analytics_html': analytics_html})

    messages.info(request, message)
    return redirect('graveyard:graveyard_list')
