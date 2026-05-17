from datetime import timedelta
from adminsortable2.admin import SortableAdminBase, SortableTabularInline
from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    Tag, CulturalObject, Favorite, FavoriteAuthor, ObjectPhoto,
    InaccuracyReport, Visit, PlannedVisit, Route, RouteStop,
)


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
        'pending_reports_badge',
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

    def get_queryset(self, request):
        from django.db.models import Count, Q
        qs = super().get_queryset(request)
        return qs.annotate(
            _pending_reports=Count(
                'inaccuracy_reports',
                filter=Q(inaccuracy_reports__status='pending'),
            ),
        )

    @admin.display(description='⚠ Reports')
    def pending_reports_badge(self, obj):
        # `_pending_reports` annotation may be absent when SortableAdminBase
        # rebuilds the queryset (e.g. drag-to-reorder); fall back to a direct count.
        count = getattr(obj, '_pending_reports', None)
        if count is None:
            count = obj.inaccuracy_reports.filter(status='pending').count()
        if not count:
            return '—'
        return format_html(
            '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:10px;font-weight:600;">{}</span>',
            count,
        )

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


@admin.register(FavoriteAuthor)
class FavoriteAuthorAdmin(admin.ModelAdmin):
    list_display = ['user', 'author', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']
    raw_id_fields = ['user', 'author']
    search_fields = ['user__username', 'author__username']


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ['user', 'cultural_object', 'visited_at', 'is_public', 'created_at']
    list_filter = ['is_public', 'visited_at']
    search_fields = ['user__username', 'cultural_object__title', 'impression']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user', 'cultural_object']
    date_hierarchy = 'visited_at'


@admin.register(PlannedVisit)
class PlannedVisitAdmin(admin.ModelAdmin):
    list_display = ['user', 'cultural_object', 'planned_date', 'created_at']
    list_filter = ['planned_date', 'created_at']
    search_fields = ['user__username', 'cultural_object__title', 'note']
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


@admin.register(InaccuracyReport)
class InaccuracyReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'cultural_object_title', 'reporter', 'reason_type', 'status', 'created_at', 'object_edit_link']
    # Both id and the object title open the report — Django wraps these cells with the change-view link.
    list_display_links = ['id', 'cultural_object_title']
    list_filter = ['status', 'reason_type', 'created_at']
    search_fields = ['cultural_object__title', 'reporter__username', 'note']
    readonly_fields = ['reporter', 'cultural_object_link_field', 'reason_type', 'note', 'created_at', 'resolved_at', 'resolved_by']
    fieldsets = (
        ('Report', {
            'fields': ('cultural_object_link_field', 'reporter', 'reason_type', 'note', 'created_at'),
        }),
        ('Moderation', {
            'fields': ('status', 'admin_response', 'resolved_by', 'resolved_at'),
        }),
    )
    actions = ['resolve_reports', 'dismiss_reports']

    @admin.display(description='Cultural object', ordering='cultural_object__title')
    def cultural_object_title(self, obj):
        # Plain text — Django wraps the cell with the change-view link via list_display_links.
        return str(obj.cultural_object)

    @admin.display(description='Дія')
    def object_edit_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:objects_culturalobject_change', args=[obj.cultural_object_id])
        # Django admin's built-in .button class adapts to the current theme palette.
        return format_html(
            '<a class="button" href="{}" style="white-space:nowrap;">Виправити об\'єкт</a>',
            url,
        )

    @admin.display(description='Об\'єкт')
    def cultural_object_link_field(self, obj):
        from django.urls import reverse
        url = reverse('admin:objects_culturalobject_change', args=[obj.cultural_object_id])
        return format_html(
            '{} &nbsp; <a class="button" href="{}" target="_blank" style="white-space:nowrap;">Виправити</a>',
            obj.cultural_object,
            url,
        )

    def save_model(self, request, obj, form, change):
        from .email import send_inaccuracy_outcome_email
        prev_status = (
            InaccuracyReport.objects.filter(pk=obj.pk).values_list('status', flat=True).first()
            if change else None
        )
        if change and obj.status in (InaccuracyReport.Status.RESOLVED, InaccuracyReport.Status.DISMISSED):
            if not obj.resolved_by:
                obj.resolved_by = request.user
            if not obj.resolved_at:
                obj.resolved_at = timezone.now()
        super().save_model(request, obj, form, change)
        # Email the reporter when status transitions from pending to closed.
        if change and prev_status == InaccuracyReport.Status.PENDING and obj.status != InaccuracyReport.Status.PENDING:
            send_inaccuracy_outcome_email.delay(obj.pk)

    @admin.action(description='Вирішити репорт (resolved)')
    def resolve_reports(self, request, queryset):
        from .email import send_inaccuracy_outcome_email
        pending = list(queryset.filter(status=InaccuracyReport.Status.PENDING).values_list('pk', flat=True))
        InaccuracyReport.objects.filter(pk__in=pending).update(
            status=InaccuracyReport.Status.RESOLVED,
            resolved_by=request.user,
            resolved_at=timezone.now(),
        )
        for pk in pending:
            send_inaccuracy_outcome_email.delay(pk)
        self.message_user(request, f'Вирішено {len(pending)} репортів.')

    @admin.action(description='Відхилити репорт (dismissed)')
    def dismiss_reports(self, request, queryset):
        from .email import send_inaccuracy_outcome_email
        pending = list(queryset.filter(status=InaccuracyReport.Status.PENDING).values_list('pk', flat=True))
        InaccuracyReport.objects.filter(pk__in=pending).update(
            status=InaccuracyReport.Status.DISMISSED,
            resolved_by=request.user,
            resolved_at=timezone.now(),
        )
        for pk in pending:
            send_inaccuracy_outcome_email.delay(pk)
        self.message_user(request, f'Відхилено {len(pending)} репортів.')


class RouteStopInline(SortableTabularInline):
    model = RouteStop
    extra = 0
    fields = ['order', 'cultural_object', 'note']
    raw_id_fields = ['cultural_object']
    ordering = ['order']


@admin.register(Route)
class RouteAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'stops_count', 'is_featured', 'created_at']
    list_filter = ['status', 'is_featured', 'created_at']
    search_fields = ['title', 'description', 'author__username']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['author', 'copied_from']
    filter_horizontal = ['tags']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [RouteStopInline]
    actions = ['approve_routes', 'archive_routes']

    fieldsets = (
        ('Основна інформація', {'fields': ('title', 'slug', 'description', 'status')}),
        ('Метадані', {'fields': ('author', 'tags', 'is_featured', 'cover_photo',
                                  'estimated_duration_minutes', 'copied_from')}),
        ('Дати', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='Зупинок')
    def stops_count(self, obj):
        return obj.stops.count()

    @admin.action(description='Затвердити обрані маршрути')
    def approve_routes(self, request, queryset):
        n = queryset.exclude(status=Route.Status.APPROVED).update(status=Route.Status.APPROVED)
        self.message_user(request, f'Затверджено {n} маршрут(ів).')

    @admin.action(description='Архівувати обрані маршрути')
    def archive_routes(self, request, queryset):
        n = queryset.exclude(status=Route.Status.ARCHIVED).update(status=Route.Status.ARCHIVED)
        self.message_user(request, f'Архівовано {n} маршрут(ів).')
