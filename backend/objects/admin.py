from django.contrib import admin
from .models import Tag, CulturalObject


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'slug']
    ordering = ['name']


@admin.register(CulturalObject)
class CulturalObjectAdmin(admin.ModelAdmin):

    list_display = [
        'title',
        'author',
        'status',
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
    ]

    fieldsets = (
        ('Основна інформація', {
            'fields': ('title', 'description', 'status')
        }),
        ('Геолокація', {
            'fields': ('latitude', 'longitude')
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

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author').prefetch_related('tags')
