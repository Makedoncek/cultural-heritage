from datetime import timedelta
from adminsortable2.admin import SortableAdminBase, SortableTabularInline
from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Tag, CulturalObject, Favorite, ObjectPhoto


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_en', 'slug', 'icon', 'tag_type']
    list_filter = ['tag_type']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'name_en', 'slug']
    ordering = ['name']


class ObjectPhotoInline(SortableTabularInline):
    model = ObjectPhoto
    extra = 0
    readonly_fields = ['thumbnail_preview_inline', 'uploaded_by', 'is_author_photo', 'created_at']
    fields = ['thumbnail_preview_inline', 'uploaded_by', 'caption', 'status', 'is_author_photo', 'order', 'created_at']
    can_delete = True
    ordering_field = 'order'

    class Media:
        css = {'all': ('admin/css/photo_inline_sortable.css',)}

    @admin.display(description='Превью (клік для редагування)')
    def thumbnail_preview_inline(self, obj):
        if not obj.id:
            return '-'
        from django.urls import reverse
        url = reverse('admin:objects_objectphoto_change', args=[obj.id])
        return format_html(
            '<div style="display:flex;flex-direction:column;align-items:flex-start;gap:6px;">'
            '<a href="{0}" title="Відкрити сторінку фото" '
            'style="display:inline-block;border-radius:6px;overflow:hidden;'
            'transition:transform 0.15s, box-shadow 0.15s;border:2px solid transparent;" '
            'onmouseover="this.style.transform=\'scale(1.05)\';this.style.borderColor=\'#79aec8\';this.style.boxShadow=\'0 4px 12px rgba(0,0,0,0.3)\';" '
            'onmouseout="this.style.transform=\'\';this.style.borderColor=\'transparent\';this.style.boxShadow=\'\';">'
            '<img src="{1}" style="height:90px;width:120px;object-fit:cover;display:block;" />'
            '</a>'
            '<a href="{0}" '
            'style="font-size:13px;padding:4px 10px;background:#417690;color:#fff;'
            'border-radius:4px;text-decoration:none;font-weight:500;">'
            'Редагувати фото</a>'
            '</div>',
            url, obj.thumbnail_url,
        )


@admin.register(CulturalObject)
class CulturalObjectAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [ObjectPhotoInline]

    def save_formset(self, request, form, formset, change):
        # Inline ObjectPhoto: admin caption edit не активує re-moderation.
        if formset.model is ObjectPhoto:
            instances = formset.save(commit=False)
            for instance in instances:
                instance._skip_status_reset = True
                instance.save()
            for instance in formset.deleted_objects:
                instance.delete()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)


    class Media:
        css = {'all': ('admin/leaflet/leaflet.css',)}
        js = (
            'admin/leaflet/leaflet.js',
            'admin/js/admin_map.js',
        )

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
        count = 0
        for obj in queryset.filter(status=CulturalObject.Status.PENDING).select_related('author'):
            obj.status = CulturalObject.Status.APPROVED
            obj.save(update_fields=['status'])
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
        map_id = f'admin-map-{obj.pk or "new"}'
        return mark_safe(
            f'<div style="position:relative;margin-top:5px;">'
            f'<div id="{map_id}" data-admin-map data-lat="{lat}" data-lng="{lng}" '
            f'style="height:300px;width:600px;max-width:100%;border-radius:8px;"></div>'
            f'<button type="button" onclick="'
            f"var f=document.getElementById('{map_id}');"
            f'if(!document.fullscreenElement){{f.requestFullscreen();}}'
            f'else{{document.exitFullscreen();}}'
            f'" style="position:absolute;top:12px;right:8px;z-index:999;'
            f'background:#fff;border:2px solid rgba(0,0,0,0.2);border-radius:4px;'
            f'padding:4px 8px;cursor:pointer;font-size:16px;font-weight:bold;" '
            f'title="На весь екран">'
            f'<svg width="14" height="14" viewBox="0 0 14 14" fill="none" '
            f'stroke="black" stroke-width="2">'
            f'<path d="M1 5V1h4M9 1h4v4M13 9v4h-4M5 13H1V9"/>'
            f'</svg></button>'
            f'</div>'
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
    def save_model(self, request, obj, form, change):
        # Admin edit не активує re-moderation при зміні caption.
        obj._skip_status_reset = True
        super().save_model(request, obj, form, change)

    STATUS_COLORS = {
        'pending': '#f59e0b',
        'approved': '#10b981',
        'rejected': '#ef4444',
    }

    list_display = [
        'thumbnail_preview',
        'cultural_object_link',
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

    @admin.display(description='Cultural object', ordering='cultural_object__title')
    def cultural_object_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:objects_culturalobject_change', args=[obj.cultural_object_id])
        return format_html('<a href="{}">{}</a>', url, obj.cultural_object)

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
        count = queryset.exclude(status=ObjectPhoto.Status.APPROVED).update(
            status=ObjectPhoto.Status.APPROVED,
            moderated_at=timezone.now(),
            rejected_cleanup_at=None,
        )
        self.message_user(request, f'Затверджено {count} фото.')

    @admin.action(description='Відхилити обрані фото')
    def reject_photos(self, request, queryset):
        cleanup_at = timezone.now() + timedelta(days=settings.PHOTO_REJECTED_RETENTION_DAYS)
        count = queryset.exclude(status=ObjectPhoto.Status.REJECTED).update(
            status=ObjectPhoto.Status.REJECTED,
            moderated_at=timezone.now(),
            rejected_cleanup_at=cleanup_at,
        )
        self.message_user(request, f'Відхилено {count} фото. Видалення з Cloudinary через {settings.PHOTO_REJECTED_RETENTION_DAYS} днів.')
