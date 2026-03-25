from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Tag, CulturalObject


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'slug']
    ordering = ['name']


@admin.register(CulturalObject)
class CulturalObjectAdmin(admin.ModelAdmin):
    STATUS_COLORS = {
        'pending': '#f59e0b',
        'approved': '#10b981',
        'archived': '#ef4444',
    }

    list_display = [
        'title',
        'author_link',
        'colored_status',
        'created_at',
        'archived_at',
    ]

    list_filter = ['status', 'tags', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'

    readonly_fields = [
        'created_at',
        'updated_at',
        'archived_at',
        'map_link',
        'map_preview',
    ]

    fieldsets = (
        ('Основна інформація', {
            'fields': ('title', 'description', 'status')
        }),
        ('Геолокація', {
            'fields': ('latitude', 'longitude', 'map_link', 'map_preview')
        }),
        ('Класифікація', {
            'fields': ('tags',)
        }),
        ('Зовнішні посилання', {
            'fields': ('wikipedia_url', 'official_website', 'google_maps_url'),
            'classes': ('collapse',)
        }),
        ('Метадані', {
            'fields': ('author', 'created_at', 'updated_at', 'archived_at'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ['tags']
    actions = ['approve_objects', 'restore_objects']

    @admin.action(description="Затвердити обрані")
    def approve_objects(self, request, queryset):
        count = queryset.filter(
            status=CulturalObject.Status.PENDING
        ).update(status=CulturalObject.Status.APPROVED)
        self.message_user(request, f'Затверджено {count} об\'єкт(ів)')

    @admin.action(description="Відновити archived")
    def restore_objects(self, request, queryset):
        count = 0
        for obj in queryset.filter(status=CulturalObject.Status.ARCHIVED):
            obj.restore()
            count += 1
        self.message_user(request, f"Відновлено {count} об'єкт(ів)")

    @admin.display(description='Переглянути на карті')
    def map_link(self, obj):
        if obj.latitude and obj.longitude:
            url = f'https://www.google.com/maps?q={obj.latitude},{obj.longitude}'
            return format_html('<a href="{}" target="_blank">🗺️ Відкрити в Google Maps</a>', url)
        return '-'

    @admin.display(description='Карта')
    def map_preview(self, obj):
        if not obj.latitude or not obj.longitude:
            return '-'
        lat = float(obj.latitude)
        lng = float(obj.longitude)
        src = (
            f'https://www.openstreetmap.org/export/embed.html'
            f'?bbox={lng - 0.01}%2C{lat - 0.01}%2C{lng + 0.01}%2C{lat + 0.01}'
            f'&layer=mapnik&marker={lat}%2C{lng}'
        )
        return mark_safe(
            f'<div style="position:relative;">'
            f'<iframe id="admin-map-iframe" width="100%" height="300" frameborder="0" '
            f'scrolling="no" style="border-radius:8px;margin-top:5px;" allowfullscreen '
            f'src="{src}"></iframe>'
            f'<button type="button" onclick="'
            f"var f=document.getElementById('admin-map-iframe');"
            f'if(!document.fullscreenElement){{f.requestFullscreen();}}'
            f'else{{document.exitFullscreen();}}'
            f'" style="position:absolute;top:12px;right:8px;z-index:999;'
            f'background:#fff;border:2px solid rgba(0,0,0,0.2);border-radius:4px;'
            f'padding:4px 8px;cursor:pointer;font-size:16px;font-weight:bold;" '
            f'title="На весь екран">'
            f'<svg width="14" height="14" viewBox="0 0 14 14" fill="none" '
            f'stroke="black" stroke-width="2">'
            f'<path d="M1 5V1h4M9 1h4v4M13 9v4h-4M5 13H1V9"/>'
            f'</svg></button></div>'
        )

    @admin.display(description='Статус', ordering='status')
    def colored_status(self, obj):
        color = self.STATUS_COLORS.get(obj.status, '#6b7280')
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, label,
        )

    @admin.display(description='Автор', ordering='author__username')
    def author_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:objects_culturalobject_changelist') + f'?author__id__exact={obj.author_id}'
        return format_html('<a href="{}">{}</a>', url, obj.author)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author').prefetch_related('tags')
