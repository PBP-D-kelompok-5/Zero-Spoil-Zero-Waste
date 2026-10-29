from django.contrib import messages
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from main.auth import is_ajax, login_required_ajax, safe_next_url

from .forms import PreservationGuideForm
from .models import PreservationGuide

# Alur autentikasi (login_required_ajax) ada di main/auth.py dan dipakai semua modul.
# Daftar & detail panduan terbuka untuk tamu; menulis, mengubah, menghapus, dan upvote butuh login.


def get_editable_guide(request, pk):
    """Panduan hanya bisa diubah/dihapus penulisnya (atau staf/moderator); selain itu 404."""
    guide = get_object_or_404(PreservationGuide, pk=pk)
    if guide.author_id != request.user.id and not request.user.is_staff:
        raise Http404('Panduan tidak ditemukan.')
    return guide


def filter_guides(params):
    """Filter bersama untuk halaman, AJAX, dan JSON: ?q= (judul, isi, metode), ?category=, ?method=."""
    guides = PreservationGuide.objects.select_related('author').order_by('-created_at')
    category = params.get('category', '').strip()
    method = params.get('method', '').strip()
    query = params.get('q', '').strip()
    if category:
        guides = guides.filter(category=category)
    if method:
        guides = guides.filter(preservation_method__iexact=method)
    if query:
        guides = guides.filter(
            Q(title__icontains=query) | Q(content__icontains=query) | Q(preservation_method__icontains=query)
        )
    return guides, {'search_query': query, 'selected_category': category, 'selected_method': method}


def method_choices():
    """Daftar metode pengawetan yang sudah dipakai (tanpa duplikat beda huruf besar/kecil)."""
    seen = {}
    for method in PreservationGuide.objects.values_list('preservation_method', flat=True):
        cleaned = method.strip()
        if cleaned:
            seen.setdefault(cleaned.casefold(), cleaned)
    return sorted(seen.values(), key=str.casefold)


@require_GET
def grimoire_list(request):
    guides, filters = filter_guides(request.GET)
    if is_ajax(request):
        # Pencarian instan: kirim ulang potongan daftar saja.
        html = render_to_string('preservation_grimoire/partials/guide_list.html', {'guides': guides, **filters}, request=request)
        return JsonResponse({'ok': True, 'count': guides.count(), 'html': html})

    context = {
        'guides': guides,
        'categories': PreservationGuide.CATEGORY_CHOICES,
        'methods': method_choices(),
        **filters,
    }
    return render(request, 'preservation_grimoire/grimoire_list.html', context)


@require_GET
def grimoire_json(request):
    """Web service daftar panduan (filter sama dengan halaman: q, category, method)."""
    guides, _ = filter_guides(request.GET)
    guides = guides.prefetch_related('upvotes')
    data = [guide.to_dict() for guide in guides]
    return JsonResponse({'ok': True, 'count': len(data), 'guides': data})


@require_GET
def grimoire_detail_json(request, pk):
    guide = get_object_or_404(PreservationGuide.objects.select_related('author'), pk=pk)
    return JsonResponse(guide.to_dict())


@require_GET
def grimoire_detail(request, pk):
    guide = get_object_or_404(PreservationGuide, pk=pk)
    has_upvoted = guide.upvotes.filter(id=request.user.id).exists() if request.user.is_authenticated else False
    return render(request, 'preservation_grimoire/grimoire_detail.html', {
        'guide': guide,
        'has_upvoted': has_upvoted,
        'can_edit': request.user.is_authenticated and (guide.author_id == request.user.id or request.user.is_staff),
    })


@require_http_methods(['GET', 'POST'])
@login_required_ajax
def grimoire_create(request):
    form = PreservationGuideForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        guide = form.save(commit=False)
        guide.author = request.user
        guide.save()
        messages.success(request, f'Panduan "{guide.title}" ditambahkan ke Grimoire.')
        return redirect('preservation_grimoire:grimoire_detail', pk=guide.pk)
    return render(request, 'preservation_grimoire/grimoire_form.html', {
        'form': form, 'title': 'Tambah Panduan Pengawetan Baru',
    })


@require_http_methods(['GET', 'POST'])
@login_required_ajax
def grimoire_update(request, pk):
    guide = get_editable_guide(request, pk)
    form = PreservationGuideForm(request.POST or None, instance=guide)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Panduan "{guide.title}" diperbarui.')
        return redirect('preservation_grimoire:grimoire_detail', pk=guide.pk)
    return render(request, 'preservation_grimoire/grimoire_form.html', {
        'form': form, 'title': 'Edit Panduan Pengawetan',
    })


@require_POST
@login_required_ajax
def grimoire_delete(request, pk):
    guide = get_editable_guide(request, pk)
    title = guide.title
    guide.delete()
    message = f'Panduan "{title}" dihapus.'
    if is_ajax(request):
        return JsonResponse({'ok': True, 'message': message})
    messages.success(request, message)
    return redirect('preservation_grimoire:grimoire_list')


@require_POST
@login_required_ajax
def toggle_upvote(request, pk):
    guide = get_object_or_404(PreservationGuide, pk=pk)
    if guide.upvotes.filter(id=request.user.id).exists():
        guide.upvotes.remove(request.user)
        upvoted = False
    else:
        guide.upvotes.add(request.user)
        upvoted = True

    if is_ajax(request):
        return JsonResponse({
            'ok': True,
            'upvoted': upvoted,
            'total_upvotes': guide.total_upvotes(),
        })
    messages.success(request, 'Upvote tersimpan.' if upvoted else 'Upvote dibatalkan.')
    return redirect(safe_next_url(request, reverse('preservation_grimoire:grimoire_detail', args=[guide.pk])))
