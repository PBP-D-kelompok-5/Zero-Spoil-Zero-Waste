from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Recipe
from .serializers import RecipeSerializer


def _visible(request):
    """Publik, atau milik sendiri bila sudah login."""
    visible = Q(is_public=True)
    if request.user.is_authenticated:
        visible |= Q(user=request.user)
    return visible


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def recipe_list(request):
    context = {'request': request}

    if request.method == 'POST':
        serializer = RecipeSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    scope = request.query_params.get('scope', 'community')
    if scope == 'mine':
        if not request.user.is_authenticated:
            raise NotAuthenticated('Silakan masuk terlebih dahulu.')
        queryset = Recipe.objects.filter(user=request.user)
    elif scope == 'community':
        queryset = Recipe.objects.filter(is_public=True)
    else:
        return Response({'detail': "Parameter scope harus 'mine' atau 'community'."},
                        status=status.HTTP_400_BAD_REQUEST)

    q = request.query_params.get('q', '').strip()
    if q:
        queryset = queryset.filter(Q(title__icontains=q) | Q(ingredients__icontains=q))

    queryset = queryset.select_related('user')
    return Response(RecipeSerializer(queryset, many=True, context=context).data)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def recipe_detail(request, pk):
    context = {'request': request}

    if request.method == 'GET':
        recipe = get_object_or_404(Recipe.objects.select_related('user').filter(_visible(request)), pk=pk)
        return Response(RecipeSerializer(recipe, context=context).data)

    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)

    if request.method == 'DELETE':
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = RecipeSerializer(recipe, data=request.data, partial=request.method == 'PATCH', context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)