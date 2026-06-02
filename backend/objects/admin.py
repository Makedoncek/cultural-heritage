from datetime import timedelta
from adminsortable2.admin import SortableAdminBase, SortableTabularInline
from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext, gettext_lazy as _
from .models import (
    Tag, CulturalObject, Favorite, FavoriteAuthor, ObjectPhoto, ObjectAudio,
    InaccuracyReport, Visit, PlannedVisit, Route, RouteStop,
    CulturalObjectTranslation, RouteTranslation, TagTranslation, TranslationStatus,
)

MODERATION_SECTION = _('Модерація')
LINK_HTML = '<a href="{}">{}</a>'
STATUS_BADGE_HTML = (
    '<span style="background:{};color:#fff;padding:3px 10px;'
    'border-radius:12px;font-size:11px;font-weight:600;">{}</span>'
)
TARGET_TYPE_LABELS = {
    'object': _("об'єкт"),
    'route': _('маршрут'),
    'photo': _('фото'),
    'audio': _('аудіо'),
    'object_translation': _("переклад об'єкта"),
    'route_translation': _('переклад маршруту'),
}


class TagTranslationInline(admin.TabularInline):
    model = TagTranslation
    extra = 1
    fields = ['language', 'name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'tag_type']
    list_filter = ['tag_type']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'slug']
    ordering = ['name']
    inlines = [TagTranslationInline]


class ObjectPhotoInline(SortableTabularInline):
    model = ObjectPhoto
    extra = 0
    readonly_fields = ['thumbnail_preview_inline', 'uploaded_by', 'is_author_photo', 'created_at']
    fields = ['thumbnail_preview_inline', 'uploaded_by', 'caption', 'status', 'is_author_photo', 'order', 'created_at']
    can_delete = True
    ordering_field = 'order'

    class Media:
        css = {'all': ('admin/css/photo_inline_sortable.css',)}

    @admin.display(description=_('Превью (клік для редагування)'))
    def thumbnail_preview_inline(self, obj):
        if not obj.id:
            return '-'
        from django.urls import reverse
        url = reverse('admin:objects_objectphoto_change', args=[obj.id])
        return format_html(
            '<div style="display:flex;flex-direction:column;align-items:flex-start;gap:6px;">'
            '<a href="{0}" title="{2}" '
            'style="display:inline-block;border-radius:6px;overflow:hidden;'
            'transition:transform 0.15s, box-shadow 0.15s;border:2px solid transparent;" '
            'onmouseover="this.style.transform=\'scale(1.05)\';this.style.borderColor=\'#79aec8\';this.style.boxShadow=\'0 4px 12px rgba(0,0,0,0.3)\';" '
            'onmouseout="this.style.transform=\'\';this.style.borderColor=\'transparent\';this.style.boxShadow=\'\';">'
            '<img src="{1}" style="height:90px;width:120px;object-fit:cover;display:block;" />'
            '</a>'
            '<a href="{0}" '
            'style="font-size:13px;padding:4px 10px;background:#417690;color:#fff;'
            'border-radius:4px;text-decoration:none;font-weight:500;">'
            '{3}</a>'
            '</div>',
            url, obj.thumbnail_url, _('Відкрити сторінку фото'), _('Редагувати фото'),
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
        (_('Основна інформація'), {
            'fields': ('title', 'description', 'status')
        }),
        (_('Подія'), {
            'fields': ('object_type', 'event_start_date', 'event_end_date'),
            'classes': ('collapse',),
        }),
        (_('Геолокація'), {
            'fields': ('latitude', 'longitude', 'map_link', 'map_preview')
        }),
        (_('Класифікація'), {
            'fields': ('tags',)
        }),
        (_('Зовнішні посилання'), {
            'fields': ('wikipedia_url', 'official_website', 'google_maps_url'),
            'classes': ('collapse',)
        }),
        (_('Метадані'), {
            'fields': ('author', 'created_at', 'updated_at', 'archived_at'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ['tags']
    actions = ['approve_objects', 'archive_objects', 'restore_objects']

    @admin.action(description=_('Затвердити обрані'))
    def approve_objects(self, request, queryset):
        count = 0
        for obj in queryset.filter(status=CulturalObject.Status.PENDING).select_related('author'):
            obj.status = CulturalObject.Status.APPROVED
            obj.save(update_fields=['status'])
            count += 1
        self.message_user(request, gettext("Затверджено %(count)d об'єкт(ів)") % {'count': count})

    @admin.action(description=_('Архівувати обрані'))
    def archive_objects(self, request, queryset):
        count = 0
        for obj in queryset.exclude(status=CulturalObject.Status.ARCHIVED):
            obj.archive()
            count += 1
        self.message_user(request, gettext("Архівовано %(count)d об'єкт(ів)") % {'count': count})

    @admin.action(description=_('Відновити з архіву'))
    def restore_objects(self, request, queryset):
        count = 0
        for obj in queryset.filter(status=CulturalObject.Status.ARCHIVED):
            obj.restore()
            count += 1
        self.message_user(request, gettext("Відновлено %(count)d об'єкт(ів)") % {'count': count})

    def get_queryset(self, request):
        from django.db.models import Count, Q
        qs = super().get_queryset(request).select_related('author').prefetch_related('tags')
        return qs.annotate(
            _pending_reports=Count(
                'inaccuracy_reports',
                filter=Q(inaccuracy_reports__status='pending'),
            ),
        )

    @admin.display(description=_('⚠ Репорти'), ordering='_pending_reports')
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

    @admin.display(description=_('Переглянути на карті'))
    def map_link(self, obj):
        if obj.latitude and obj.longitude:
            url = f'https://www.google.com/maps?q={obj.latitude},{obj.longitude}'
            return format_html('<a href="{}" target="_blank">{}</a>', url, _('🗺️ Відкрити в Google Maps'))
        return '-'

    @admin.display(description=_('Карта'))
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
            f'title="{gettext("На весь екран")}">'
            f'<svg width="14" height="14" viewBox="0 0 14 14" fill="none" '
            f'stroke="black" stroke-width="2">'
            f'<path d="M1 5V1h4M9 1h4v4M13 9v4h-4M5 13H1V9"/>'
            f'</svg></button>'
            f'</div>'
        )

    @admin.display(description=_('Статус'), ordering='status')
    def colored_status(self, obj):
        color = self.STATUS_COLORS.get(obj.status, '#6b7280')
        label = obj.get_status_display()
        return format_html(
            STATUS_BADGE_HTML,
            color, label,
        )

    @admin.display(description=_('Автор'), ordering='author__username')
    def author_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:objects_culturalobject_changelist') + f'?author__id__exact={obj.author_id}'
        return format_html(LINK_HTML, url, obj.author)


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
        # Відхилення/затвердження через форму тримаємо консистентним із масовими діями:
        # ставимо moderated_at і плануємо/скасовуємо очищення Cloudinary.
        if obj.status == ObjectPhoto.Status.REJECTED:
            if obj.moderated_at is None:
                obj.moderated_at = timezone.now()
            if obj.rejected_cleanup_at is None:
                obj.rejected_cleanup_at = timezone.now() + timedelta(days=settings.PHOTO_REJECTED_RETENTION_DAYS)
        elif obj.status == ObjectPhoto.Status.APPROVED:
            if obj.moderated_at is None:
                obj.moderated_at = timezone.now()
            obj.rejected_cleanup_at = None
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

    fieldsets = (
        (_('Фото'), {
            'fields': ('large_preview', 'caption', 'order', 'is_author_photo'),
        }),
        (MODERATION_SECTION, {
            'fields': ('status', 'moderation_note', 'moderated_at', 'rejected_cleanup_at'),
        }),
        (_("Об'єкт і автор"), {
            'fields': ('cultural_object', 'uploaded_by'),
        }),
        ('Cloudinary', {
            'fields': ('cloudinary_public_id', 'image_url', 'thumbnail_url'),
            'classes': ('collapse',),
        }),
        (_('Дати'), {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_('Превью'))
    def thumbnail_preview(self, obj):
        return format_html(
            '<img src="{}" style="height:60px;border-radius:4px;" />', obj.thumbnail_url,
        )

    @admin.display(description=_('Зображення'))
    def large_preview(self, obj):
        return format_html(
            '<img src="{}" style="max-width:600px;border-radius:8px;" />', obj.image_url,
        )

    @admin.display(description=_('Культурний об\'єкт'), ordering='cultural_object__title')
    def cultural_object_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:objects_culturalobject_change', args=[obj.cultural_object_id])
        return format_html(LINK_HTML, url, obj.cultural_object)

    @admin.display(description=_('Статус'), ordering='status')
    def colored_status(self, obj):
        color = self.STATUS_COLORS.get(obj.status, '#6b7280')
        return format_html(
            STATUS_BADGE_HTML,
            color, obj.get_status_display(),
        )

    @admin.action(description=_('Затвердити обрані фото'))
    def approve_photos(self, request, queryset):
        count = queryset.exclude(status=ObjectPhoto.Status.APPROVED).update(
            status=ObjectPhoto.Status.APPROVED,
            moderated_at=timezone.now(),
            rejected_cleanup_at=None,
        )
        self.message_user(request, gettext('Затверджено %(count)d фото.') % {'count': count})

    @admin.action(description=_('Відхилити обрані фото'))
    def reject_photos(self, request, queryset):
        cleanup_at = timezone.now() + timedelta(days=settings.PHOTO_REJECTED_RETENTION_DAYS)
        count = queryset.exclude(status=ObjectPhoto.Status.REJECTED).update(
            status=ObjectPhoto.Status.REJECTED,
            moderated_at=timezone.now(),
            rejected_cleanup_at=cleanup_at,
        )
        self.message_user(request, gettext('Відхилено %(count)d фото. Видалення з Cloudinary через %(days)d днів.') % {'count': count, 'days': settings.PHOTO_REJECTED_RETENTION_DAYS})


@admin.register(InaccuracyReport)
class InaccuracyReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'target_display', 'reporter', 'reason_type', 'status', 'created_at', 'target_edit_link']
    list_display_links = ['id', 'target_display']
    list_filter = ['status', 'reason_type', 'content_type', 'created_at']
    search_fields = ['reporter__username', 'note']
    readonly_fields = ['reporter', 'target_link_field', 'content_owner', 'reason_type', 'note', 'created_at', 'resolved_at', 'resolved_by']
    fieldsets = (
        (_('Репорт'), {
            'fields': ('target_link_field', 'content_owner', 'reporter', 'reason_type', 'note', 'created_at'),
        }),
        (MODERATION_SECTION, {
            'fields': ('status', 'admin_response', 'resolved_by', 'resolved_at'),
        }),
    )
    actions = ['resolve_reports', 'dismiss_reports']

    def _target_admin_url(self, obj):
        from django.urls import reverse, NoReverseMatch
        ct = obj.content_type
        if not ct:
            return None
        try:
            return reverse(f'admin:{ct.app_label}_{ct.model}_change', args=[obj.object_id])
        except NoReverseMatch:
            return None

    @admin.display(description=_('Ціль'))
    def target_display(self, obj):
        from .report_targets import describe_target
        d = describe_target(obj.target)
        kind = d['target_type'] or (obj.content_type.model if obj.content_type else '?')
        return f"[{TARGET_TYPE_LABELS.get(kind, kind)}] {d['target_title']}"

    @admin.display(description=_('Дія'))
    def target_edit_link(self, obj):
        url = self._target_admin_url(obj)
        if not url:
            return '—'
        return format_html(
            '<a class="button" href="{}" style="white-space:nowrap;">{}</a>', url, _('Відкрити ціль'),
        )

    @admin.display(description=_('Ціль'))
    def target_link_field(self, obj):
        from .report_targets import describe_target
        d = describe_target(obj.target)
        url = self._target_admin_url(obj)
        if not url:
            return d['target_title']
        kind = d['target_type'] or '?'
        return format_html(
            '[{}] {} &nbsp; <a class="button" href="{}" target="_blank" style="white-space:nowrap;">{}</a>',
            TARGET_TYPE_LABELS.get(kind, kind), d['target_title'], url, _('Відкрити'),
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

    @admin.action(description=_('Вирішити репорт'))
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
        self.message_user(request, gettext('Вирішено %(count)d репортів.') % {'count': len(pending)})

    @admin.action(description=_('Відхилити репорт'))
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
        self.message_user(request, gettext('Відхилено %(count)d репортів.') % {'count': len(pending)})


class RouteStopInline(SortableTabularInline):
    model = RouteStop
    extra = 0
    fields = ['order', 'cultural_object', 'note']
    raw_id_fields = ['cultural_object']
    ordering = ['order']
    ordering_field = 'order'

    class Media:
        css = {'all': ('admin/css/route_stop_inline_sortable.css',)}


@admin.register(Route)
class RouteAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ['title', 'author', 'visibility', 'status', 'stops_count', 'is_featured', 'created_at']
    list_filter = ['visibility', 'status', 'is_featured', 'created_at']
    search_fields = ['title', 'description', 'author__username']
    raw_id_fields = ['author', 'copied_from']
    filter_horizontal = ['tags']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [RouteStopInline]
    actions = ['approve_routes', 'archive_routes']

    fieldsets = (
        (_('Основна інформація'), {'fields': ('title', 'description', 'visibility', 'status')}),
        (_('Метадані'), {'fields': ('author', 'tags', 'is_featured',
                                  'estimated_duration_minutes', 'copied_from')}),
        (_('Дати'), {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description=_('Зупинок'))
    def stops_count(self, obj):
        return obj.stops.count()

    @admin.action(description=_('Затвердити обрані маршрути'))
    def approve_routes(self, request, queryset):
        n = queryset.exclude(status=Route.Status.APPROVED).update(status=Route.Status.APPROVED)
        self.message_user(request, gettext('Затверджено %(count)d маршрут(ів).') % {'count': n})

    @admin.action(description=_('Архівувати обрані маршрути'))
    def archive_routes(self, request, queryset):
        n = queryset.exclude(status=Route.Status.ARCHIVED).update(status=Route.Status.ARCHIVED)
        self.message_user(request, gettext('Архівовано %(count)d маршрут(ів).') % {'count': n})


@admin.register(ObjectAudio)
class ObjectAudioAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'cultural_object', 'language', 'audio_player_short',
                    'duration_seconds', 'status', 'plays_count', 'uploaded_by', 'created_at']
    list_filter = ['status', 'language', 'created_at']
    search_fields = ['title', 'narrator_name', 'cultural_object__title', 'uploaded_by__username']
    readonly_fields = ['cloudinary_public_id', 'cloudinary_url', 'audio_player',
                       'duration_seconds', 'plays_count', 'uploaded_by',
                       'created_at', 'updated_at', 'moderated_at']
    raw_id_fields = ['cultural_object']
    actions = ['approve_audios', 'reject_audios']

    fieldsets = (
        (_('Аудіо'), {
            'fields': ('audio_player', 'title', 'language', 'narrator_name',
                       'duration_seconds', 'plays_count'),
        }),
        (MODERATION_SECTION, {
            'fields': ('status', 'moderation_note', 'moderated_at'),
        }),
        (_("Об'єкт і автор"), {
            'fields': ('cultural_object', 'uploaded_by', 'copyright_confirmed'),
        }),
        ('Cloudinary', {
            'fields': ('cloudinary_public_id', 'cloudinary_url'),
            'classes': ('collapse',),
        }),
        (_('Дати'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_('Послухати'))
    def audio_player(self, obj):
        if not obj.cloudinary_url:
            return '—'
        return mark_safe(
            f'<audio src="{obj.cloudinary_url}" controls preload="metadata" '
            f'style="display:block;width:480px;max-width:100%;height:40px;margin-top:6px;"></audio>'
            f'<a href="{obj.cloudinary_url}" target="_blank" '
            f'style="display:inline-block;margin-top:8px;font-size:15px;font-weight:500;">'
            f'{gettext("⬇ Завантажити файл")}</a>'
        )

    @admin.display(description=_('Запис'))
    def audio_player_short(self, obj):
        if not obj.cloudinary_url:
            return '—'
        return mark_safe(
            f'<audio controls preload="none" style="height:32px;width:200px;">'
            f'<source src="{obj.cloudinary_url}" /></audio>'
        )

    @admin.action(description=_('Затвердити обрані аудіо'))
    def approve_audios(self, request, queryset):
        from django.utils import timezone
        n = queryset.exclude(status=ObjectAudio.Status.APPROVED).update(
            status=ObjectAudio.Status.APPROVED, moderated_at=timezone.now(),
        )
        self.message_user(request, gettext('Затверджено %(count)d аудіо.') % {'count': n})

    @admin.action(description=_('Відхилити обрані аудіо'))
    def reject_audios(self, request, queryset):
        from django.utils import timezone
        n = queryset.exclude(status=ObjectAudio.Status.REJECTED).update(
            status=ObjectAudio.Status.REJECTED, moderated_at=timezone.now(),
        )
        self.message_user(request, gettext('Відхилено %(count)d аудіо.') % {'count': n})


# --- Translation moderation ---


class _TranslationAdminForm(forms.ModelForm):
    """Skips the partial unique-approved constraint check at form level.

    The invariant (one approved translation per language) is maintained by
    ModelAdmin.save_model, which deletes the previous approved translation before
    saving. Without this, re-approving via the change page would be blocked by
    ModelForm's constraint validation (which runs before save_model)."""

    def _post_clean(self):
        original = self.instance.validate_constraints
        self.instance.validate_constraints = lambda *a, **k: None
        try:
            super()._post_clean()
        finally:
            self.instance.validate_constraints = original


class _TranslationAdminMixin:
    """Shared moderation actions for CulturalObjectTranslation / RouteTranslation.

    Approving an original-language proposal copies its text into the parent's
    canonical title/description; the proposal row is kept (status=approved) as an
    audit record. Approving / rejecting always notifies the submitter by email.
    """

    # 'object' | 'route' — used to dispatch the outcome email task.
    email_kind = None

    STATUS_COLORS = {
        'pending': '#f59e0b',
        'approved': '#10b981',
        'rejected': '#ef4444',
    }

    @admin.display(description=_('Статус'), ordering='status')
    def colored_status(self, obj):
        color = self.STATUS_COLORS.get(obj.status, '#6b7280')
        return format_html(
            STATUS_BADGE_HTML,
            color, obj.get_status_display(),
        )

    def _apply_approval(self, translation):
        """Free the approved slot for this (parent, language) and, for the original
        language, write the text back into the parent's canonical fields."""
        self._get_siblings(translation).filter(status=TranslationStatus.APPROVED).delete()
        parent = self._get_parent(translation)
        if translation.language == parent.original_language:
            parent.title = translation.title
            parent.description = translation.description
            parent.save(update_fields=['title', 'description'])

    def _notify(self, translation):
        from .email import send_translation_outcome_email
        send_translation_outcome_email.delay(self.email_kind, translation.pk)

    @admin.action(description=_('Затвердити обрані переклади'))
    def approve_translations(self, request, queryset):
        n = 0
        for translation in queryset.filter(status=TranslationStatus.PENDING):
            self._apply_approval(translation)
            translation.status = TranslationStatus.APPROVED
            translation.save(update_fields=['status', 'updated_at'])
            self._notify(translation)
            n += 1
        self.message_user(request, gettext('Затверджено %(count)d переклад(ів).') % {'count': n})

    @admin.action(description=_('Відхилити обрані переклади'))
    def reject_translations(self, request, queryset):
        n = 0
        for translation in queryset.filter(status=TranslationStatus.PENDING):
            translation.status = TranslationStatus.REJECTED
            translation.save(update_fields=['status', 'updated_at'])
            self._notify(translation)
            n += 1
        self.message_user(request, gettext('Відхилено %(count)d переклад(ів). Додайте нотатку рецензента у конкретному перекладі, щоб пояснити причину.') % {'count': n})

    def save_model(self, request, obj, form, change):
        prev_status = (
            type(obj).objects.filter(pk=obj.pk).values_list('status', flat=True).first()
            if change else None
        )
        becomes_approved = obj.status == TranslationStatus.APPROVED and prev_status != TranslationStatus.APPROVED
        becomes_rejected = obj.status == TranslationStatus.REJECTED and prev_status != TranslationStatus.REJECTED
        # Free the unique-approved slot before saving to avoid an integrity error.
        if becomes_approved:
            self._apply_approval(obj)
        super().save_model(request, obj, form, change)
        if becomes_approved or becomes_rejected:
            self._notify(obj)

    def _get_parent(self, translation):
        raise NotImplementedError

    def _get_siblings(self, translation):
        raise NotImplementedError


@admin.register(CulturalObjectTranslation)
class CulturalObjectTranslationAdmin(_TranslationAdminMixin, admin.ModelAdmin):
    email_kind = 'object'
    form = _TranslationAdminForm
    list_display = ['id', 'cultural_object_link', 'language', 'colored_status', 'submitted_by', 'updated_at']
    list_filter = ['status', 'language', 'updated_at']
    search_fields = ['cultural_object__title', 'title', 'submitted_by__username']
    raw_id_fields = ['cultural_object', 'submitted_by']
    readonly_fields = ['submitted_by', 'created_at', 'updated_at']
    actions = ['approve_translations', 'reject_translations']
    fieldsets = (
        (_('Джерело'), {'fields': ('cultural_object', 'language', 'submitted_by')}),
        (_('Переклад'), {'fields': ('title', 'description')}),
        (MODERATION_SECTION, {'fields': ('status', 'reviewer_note')}),
        (_('Дати'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description=_('Культурний об\'єкт'), ordering='cultural_object__title')
    def cultural_object_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:objects_culturalobject_change', args=[obj.cultural_object_id])
        return format_html(LINK_HTML, url, obj.cultural_object)

    def _get_parent(self, translation):
        return translation.cultural_object

    def _get_siblings(self, translation):
        return CulturalObjectTranslation.objects.filter(
            cultural_object=translation.cultural_object,
            language=translation.language,
        ).exclude(pk=translation.pk)


@admin.register(RouteTranslation)
class RouteTranslationAdmin(_TranslationAdminMixin, admin.ModelAdmin):
    email_kind = 'route'
    form = _TranslationAdminForm
    list_display = ['id', 'route_link', 'language', 'colored_status', 'submitted_by', 'updated_at']
    list_filter = ['status', 'language', 'updated_at']
    search_fields = ['route__title', 'title', 'submitted_by__username']
    raw_id_fields = ['route', 'submitted_by']
    readonly_fields = ['submitted_by', 'created_at', 'updated_at']
    actions = ['approve_translations', 'reject_translations']
    fieldsets = (
        (_('Джерело'), {'fields': ('route', 'language', 'submitted_by')}),
        (_('Переклад'), {'fields': ('title', 'description')}),
        (MODERATION_SECTION, {'fields': ('status', 'reviewer_note')}),
        (_('Дати'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description=_('Маршрут'), ordering='route__title')
    def route_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:objects_route_change', args=[obj.route_id])
        return format_html(LINK_HTML, url, obj.route)

    def _get_parent(self, translation):
        return translation.route

    def _get_siblings(self, translation):
        return RouteTranslation.objects.filter(
            route=translation.route,
            language=translation.language,
        ).exclude(pk=translation.pk)
