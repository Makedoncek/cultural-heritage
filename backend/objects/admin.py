from datetime import timedelta
from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Tag, CulturalObject, Favorite, ObjectPhoto


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'tag_type']
    list_filter = ['tag_type']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'slug']
    ordering = ['name']


class ObjectPhotoInline(admin.TabularInline):
    model = ObjectPhoto
    extra = 0
    readonly_fields = ['thumbnail_preview_inline', 'uploaded_by', 'is_author_photo', 'created_at']
    fields = ['thumbnail_preview_inline', 'uploaded_by', 'caption', 'status', 'is_author_photo', 'order', 'created_at']
    can_delete = False

    @admin.display(description='Превью')
    def thumbnail_preview_inline(self, obj):
        if not obj.id:
            return '-'
        return format_html('<img src="{}" style="height:60px;" />', obj.thumbnail_url)


@admin.register(CulturalObject)
class CulturalObjectAdmin(admin.ModelAdmin):
    inlines = [ObjectPhotoInline]
    STATUS_COLORS = {
        'pending': '#f59e0b',
        'approved': '#10b981',
        'archived': '#ef4444',
    }

    list_display = [
        'title',
        'author_link',
        'colored_status',
        'object_type',
        'created_at',
        'archived_at',
    ]

    list_filter = ['status', 'object_type', 'tags', 'created_at']
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
        ('Подія', {
            'fields': ('object_type', 'event_start_date', 'event_end_date'),
            'classes': ('collapse',),
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
    actions = ['approve_objects', 'archive_objects', 'restore_objects']

    @admin.action(description="Затвердити обрані")
    def approve_objects(self, request, queryset):
        from .email import send_status_notification
        count = 0
        for obj in queryset.filter(status=CulturalObject.Status.PENDING).select_related('author'):
            obj.status = CulturalObject.Status.APPROVED
            obj.save(update_fields=['status'])
            if obj.author.email:
                send_status_notification.delay(obj.id, 'approved')
            count += 1
        self.message_user(request, f'Затверджено {count} об\'єкт(ів)')

    @admin.action(description="Архівувати обрані")
    def archive_objects(self, request, queryset):
        count = 0
        for obj in queryset.exclude(status=CulturalObject.Status.ARCHIVED):
            obj.archive()
            count += 1
        self.message_user(request, f"Архівовано {count} об'єкт(ів)")

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


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'cultural_object', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']
    raw_id_fields = ['user', 'cultural_object']


@admin.register(ObjectPhoto)
class ObjectPhotoAdmin(admin.ModelAdmin):
    STATUS_COLORS = {
        'pending': '#f59e0b',
        'approved': '#10b981',
        'rejected': '#ef4444',
    }

    list_display = [
        'thumbnail_preview',
        'cultural_object',
        'uploaded_by',
        'colored_status',
        'is_author_photo',
        'created_at',
    ]
    list_filter = ['status', 'is_author_photo', 'created_at']
    search_fields = ['cultural_object__title', 'uploaded_by__username', 'caption']
    readonly_fields = [
        'cultural_object', 'uploaded_by',
        'cloudinary_public_id', 'image_url', 'thumbnail_url',
        'created_at', 'moderated_at', 'rejected_cleanup_at',
        'large_preview',
    ]
    actions = ['approve_photos', 'reject_photos']

    @admin.display(description='Превью')
    def thumbnail_preview(self, obj):
        return format_html(
            '<img src="{}" style="height:60px;border-radius:4px;" />', obj.thumbnail_url,
        )

    @admin.display(description='Зображення')
    def large_preview(self, obj):
        return format_html(
            '<img src="{}" style="max-width:600px;border-radius:8px;" />', obj.image_url,
        )

    @admin.display(description='Статус', ordering='status')
    def colored_status(self, obj):
        color = self.STATUS_COLORS.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.action(description='Затвердити обрані фото')
    def approve_photos(self, request, queryset):
        count = queryset.filter(status=ObjectPhoto.Status.PENDING).update(
            status=ObjectPhoto.Status.APPROVED,
            moderated_at=timezone.now(),
            rejected_cleanup_at=None,
        )
        self.message_user(request, f'Затверджено {count} фото.')

    @admin.action(description='Відхилити обрані фото')
    def reject_photos(self, request, queryset):
        cleanup_at = timezone.now() + timedelta(days=settings.PHOTO_REJECTED_RETENTION_DAYS)
        count = queryset.filter(status=ObjectPhoto.Status.PENDING).update(
            status=ObjectPhoto.Status.REJECTED,
            moderated_at=timezone.now(),
            rejected_cleanup_at=cleanup_at,
        )
        self.message_user(request, f'Відхилено {count} фото. Видалення з Cloudinary через {settings.PHOTO_REJECTED_RETENTION_DAYS} днів.')
