from django.contrib import admin
from graveyard.models import GraveyardItem


@admin.register(GraveyardItem)
class GraveyardItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'reason', 'disposed_at', 'estimated_loss', 'weight_g')
    list_filter = ('category', 'reason', 'disposed_at')
    search_fields = ('name', 'notes', 'user__username')
    date_hierarchy = 'disposed_at'
