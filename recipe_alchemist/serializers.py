from rest_framework import serializers

from .forms import DIETS
from .models import Recipe

ALLOWED_DIETS = {value for value, _ in DIETS if value}


class RecipeSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    ingredient_list = serializers.ListField(child=serializers.CharField(), read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'title', 'username', 'source', 'spoonacular_id', 'source_url', 'image_url',
            'ingredients', 'ingredient_list', 'instructions', 'cook_time_minutes', 'diet',
            'notes', 'is_public', 'is_owner', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'source', 'spoonacular_id', 'source_url', 'image_url',
                            'created_at', 'updated_at']

    def get_is_owner(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)

    def validate_diet(self, value):
        if value and value not in ALLOWED_DIETS:
            raise serializers.ValidationError('Diet tidak dikenal.')
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data['is_owner']:
            data.pop('notes', None)
        return data