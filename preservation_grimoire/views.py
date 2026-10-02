from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import PreservationGuide
from .forms import PreservationGuideForm

def grimoire_list(request):
    category_filter = request.GET.get('category', '')
    query = request.GET.get('q', '')
    
    guides = PreservationGuide.objects.all().order_by('-created_at')
    
    if category_filter:
        guides = guides.filter(category=category_filter)
    if query:
        guides = guides.filter(title__icontains=query) | guides.filter(content__icontains=query)

    context = {
        'guides': guides,
        'selected_category': category_filter,
        'search_query': query,
    }
    return render(request, 'preservation_grimoire/grimoire_list.html', context)

def grimoire_detail(request, pk):
    guide = get_object_or_404(PreservationGuide, pk=pk)
    has_upvoted = guide.upvotes.filter(id=request.user.id).exists() if request.user.is_authenticated else False
    return render(request, 'preservation_grimoire/grimoire_detail.html', {
        'guide': guide,
        'has_upvoted': has_upvoted
    })

@login_required
def grimoire_create(request):
    if request.method == 'POST':
        form = PreservationGuideForm(request.POST)
        if form.is_valid():
            guide = form.save(commit=False)
            guide.author = request.user
            guide.save()
            return redirect('preservation_grimoire:grimoire_list')
    else:
        form = PreservationGuideForm()
    return render(request, 'preservation_grimoire/grimoire_form.html', {'form': form, 'title': 'Tambah Panduan Pengawetan Baru'})

@login_required
def grimoire_update(request, pk):
    guide = get_object_or_404(PreservationGuide, pk=pk)
    if guide.author != request.user and not request.user.is_staff:
        return redirect('preservation_grimoire:grimoire_list')

    if request.method == 'POST':
        form = PreservationGuideForm(request.POST, instance=guide)
        if form.is_valid():
            form.save()
            return redirect('preservation_grimoire:grimoire_detail', pk=guide.pk)
    else:
        form = PreservationGuideForm(instance=guide)
    return render(request, 'preservation_grimoire/grimoire_form.html', {'form': form, 'title': 'Edit Panduan Pengawetan'})

@login_required
def grimoire_delete(request, pk):
    guide = get_object_or_404(PreservationGuide, pk=pk)
    if guide.author == request.user or request.user.is_staff:
        guide.delete()
    return redirect('preservation_grimoire:grimoire_list')

@login_required
@require_POST
def toggle_upvote(request, pk):
    guide = get_object_or_404(PreservationGuide, pk=pk)
    if guide.upvotes.filter(id=request.user.id).exists():
        guide.upvotes.remove(request.user)
        upvoted = False
    else:
        guide.upvotes.add(request.user)
        upvoted = True
    
    return JsonResponse({
        'upvoted': upvoted,
        'total_upvotes': guide.total_upvotes()
    })