from django.contrib import admin

from death_clock.models import PantryItem


@admin.register(PantryItem)
class PantryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'storage', 'quantity', 'unit', 'expiry_date', 'status_label', 'resurrected_at')
    list_filter = ('category', 'storage', 'expiry_is_estimate')
    search_fields = ('name', 'notes', 'user__username')
    date_hierarchy = 'expiry_date'
    autocomplete_fields = ('user',)

    @admin.display(description='Status')
    def status_label(self, obj):
        return obj.status_label
