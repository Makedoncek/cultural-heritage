"""
Models for the CultureMap Ukraine application.

Core models:
- Tag: Categories for cultural objects (Castle, Church, Museum, etc.)
- CulturalObject: Ukrainian cultural heritage sites with geographic coordinates
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .validators import validate_coordinates_within_ukraine


class Tag(models.Model):
    """
    Category/type for cultural objects.

    Admin-only creation, users select from existing tags.
    """

    class TagType(models.TextChoices):
        OBJECT = 'object', 'Об\'єкт'
        EVENT = 'event', 'Подія'

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Display name of the tag (e.g., 'Castle', 'Church')"
    )

    name_en = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="English translation; falls back to `name` when empty."
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly version (auto-generated from name, e.g., 'castle')"
    )

    icon = models.CharField(
        max_length=10,
        help_text="Emoji icon for visual representation (e.g., '🏰' for Castle)"
    )

    tag_type = models.CharField(
        max_length=10,
        choices=TagType.choices,
        default=TagType.OBJECT,
        db_index=True,
    )

    class Meta:
        ordering = ['name']
        verbose_name = _('Тег')
        verbose_name_plural = _('Теги')

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CulturalObject(models.Model):
    """
    Ukrainian cultural heritage site with geographic coordinates.

    Features:
    - Geographic coordinates with Ukraine boundary validation
    - Three-status moderation workflow (pending → approved → archived)
    - Soft delete pattern (data preserved for recovery)
    - User ownership and tagging system

    Business Rules:
    - New objects start as 'pending' (require admin approval)
    - Users can only edit their own objects
    - Editing an 'approved' object resets it to 'pending'
    - Delete = archive (soft delete, not hard delete)
    """

    class ObjectType(models.TextChoices):
        PERMANENT = 'permanent', 'Пам\'ятка'
        EVENT = 'event', 'Подія'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        ARCHIVED = 'archived', 'Archived'

    title = models.CharField(
        max_length=200,
        help_text="Name of the cultural object (e.g., 'Lviv Opera House')"
    )

    # Use empty string for "no data", not NULL (Django best practice for text fields)
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the object (optional)"
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Latitude coordinate (within Ukraine)"
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Longitude coordinate (within Ukraine)"
    )

    # CASCADE: If user deleted, delete all their objects
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cultural_objects',
        help_text="User who created this object"
    )

    tags = models.ManyToManyField(
        Tag,
        related_name='cultural_objects',
        help_text="Categories for this object (select 1-5 tags)"
    )

    # Indexed for frequent filtering by status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current moderation status"
    )

    object_type = models.CharField(
        max_length=20,
        choices=ObjectType.choices,
        default=ObjectType.PERMANENT,
        db_index=True,
    )

    event_start_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    event_end_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    wikipedia_url = models.URLField(
        blank=True,
        null=True,
        help_text="Link to Wikipedia article (optional)"
    )

    official_website = models.URLField(
        blank=True,
        null=True,
        help_text="Official website of the object (optional)"
    )

    google_maps_url = models.URLField(
        blank=True,
        null=True,
        help_text="Google Maps link (optional)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this object was first created"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this object was last modified"
    )

    # Set only when status changes to 'archived'
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this object was archived (soft-deleted)"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Культурний об\'єкт')
        verbose_name_plural = _('Культурні об\'єкти')

        # Indexes for frequently filtered fields
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['author']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['object_type', 'event_end_date']),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"

    def archive(self):
        """
        Soft-delete by changing status to 'archived'.

        Preserves data for recovery, unlike hard delete.
        No-op if already archived.
        """
        if self.status == self.Status.ARCHIVED:
            return
        self.status = self.Status.ARCHIVED
        self.archived_at = timezone.now()
        self.save(update_fields=['status', 'archived_at'])

    def restore(self):
        """
        Restore archived object to 'pending' status.

        Requires re-approval (admin review again).
        No-op if not archived.
        """
        if self.status != self.Status.ARCHIVED:
            return
        self.status = self.Status.PENDING
        self.archived_at = None
        self.save(update_fields=['status', 'archived_at'])

    def clean(self):
        super().clean()
        if self.latitude is not None and self.longitude is not None:
            validate_coordinates_within_ukraine(self.latitude, self.longitude)

        if self.object_type == self.ObjectType.EVENT:
            if not self.event_start_date or not self.event_end_date:
                raise ValidationError('Для подій потрібно вказати дату початку та завершення.')
            if self.event_end_date < self.event_start_date:
                raise ValidationError('Дата завершення не може бути раніше дати початку.')

    @property
    def cover_url(self):
        """Thumbnail URL першого approved-фото (з урахуванням ordering: автор → контриб'ютори).

        Використовує annotated `_cover_thumbnail_url` з ObjectViewSet.get_queryset якщо доступне,
        інакше робить окремий запит (fallback для одиночних викликів).
        """
        annotated = getattr(self, '_cover_thumbnail_url', None)
        if annotated is not None or self._state.fields_cache.get('_cover_thumbnail_url') is not None:
            return annotated
        first = self.photos.filter(status='approved').first()
        return first.thumbnail_url if first else None


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    cultural_object = models.ForeignKey(CulturalObject, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'cultural_object')
        ordering = ['-created_at']
        verbose_name = _('Обране')
        verbose_name_plural = _('Обране')

    def __str__(self):
        return f'{self.user.username} → {self.cultural_object.title}'


class FavoriteAuthor(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_authors')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'author')
        ordering = ['-created_at']
        verbose_name = _('Підписка на автора')
        verbose_name_plural = _('Підписки на авторів')

    def __str__(self):
        return f'{self.user.username} → {self.author.username}'


class ObjectPhoto(models.Model):
    """Фото культурного об'єкта з модерацією і Cloudinary-зберіганням."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    cultural_object = models.ForeignKey(
        CulturalObject,
        on_delete=models.CASCADE,
        related_name='photos',
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_photos',
    )
    cloudinary_public_id = models.CharField(max_length=255, unique=True)
    image_url = models.URLField(max_length=500)
    thumbnail_url = models.URLField(max_length=500)
    caption = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_author_photo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    rejected_cleanup_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['cultural_object', 'status']),
            models.Index(fields=['status', 'rejected_cleanup_at']),
            models.Index(fields=['uploaded_by']),
        ]
        verbose_name = _('Фото об\'єкта')
        verbose_name_plural = _('Фото об\'єктів')

    def __str__(self):
        return f'Photo {self.id} ({self.status}) for {self.cultural_object.title}'


class ObjectAudio(models.Model):
    """Аудіо-нарратив для культурного об'єкта (Audio Tours feature)."""

    class Language(models.TextChoices):
        UK = 'uk', 'Українська'
        EN = 'en', 'English'
        PL = 'pl', 'Polski'
        DE = 'de', 'Deutsch'

    class Status(models.TextChoices):
        PENDING = 'pending', 'На модерації'
        APPROVED = 'approved', 'Опубліковано'
        REJECTED = 'rejected', 'Відхилено'

    cultural_object = models.ForeignKey(
        CulturalObject,
        on_delete=models.CASCADE,
        related_name='audios',
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_audios',
    )
    cloudinary_public_id = models.CharField(max_length=255, unique=True)
    cloudinary_url = models.URLField(max_length=500)
    duration_seconds = models.PositiveIntegerField()
    language = models.CharField(
        max_length=2,
        choices=Language.choices,
        default=Language.UK,
    )
    title = models.CharField(max_length=150)
    narrator_name = models.CharField(max_length=100, blank=True)
    # Affirms author has the right to publish (legal cover before moderation)
    copyright_confirmed = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    moderation_note = models.TextField(blank=True)
    plays_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cultural_object', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['cultural_object', 'language', 'status']),
        ]
        verbose_name = _("Аудіо-нарратив")
        verbose_name_plural = _("Аудіо-наративи")

    def __str__(self):
        return f'Audio {self.id} ({self.language}, {self.status}) for {self.cultural_object.title}'


class UserPreference(models.Model):
    """Налаштування користувача — мова інтерфейсу, email-сповіщень і тема."""

    class Language(models.TextChoices):
        UK = 'uk', 'Українська'
        EN = 'en', 'English'

    class Theme(models.TextChoices):
        LIGHT = 'light', 'Light'
        DARK = 'dark', 'Dark'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preference',
    )
    language = models.CharField(
        max_length=2,
        choices=Language.choices,
        default=Language.UK,
    )
    theme = models.CharField(
        max_length=5,
        choices=Theme.choices,
        default=Theme.LIGHT,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username}: lang={self.language}, theme={self.theme}'


class InaccuracyReport(models.Model):
    """User-submitted report of an issue with a cultural object (wrong data, duplicate, etc.)."""

    class ReasonType(models.TextChoices):
        WRONG_COORDS = 'wrong_coords', 'Невірні координати'
        WRONG_NAME = 'wrong_name', 'Неточна назва'
        WRONG_DESCRIPTION = 'wrong_description', 'Помилки в описі'
        WRONG_TAGS = 'wrong_tags', 'Невірні теги'
        DUPLICATE = 'duplicate', 'Дублікат іншого об\'єкта'
        OTHER = 'other', 'Інше'

    class Status(models.TextChoices):
        PENDING = 'pending', 'На розгляді'
        RESOLVED = 'resolved', 'Вирішено'
        DISMISSED = 'dismissed', 'Відхилено'

    cultural_object = models.ForeignKey(
        CulturalObject,
        related_name='inaccuracy_reports',
        on_delete=models.CASCADE,
    )
    reporter = models.ForeignKey(
        User,
        related_name='reports_made',
        on_delete=models.CASCADE,
    )
    reason_type = models.CharField(max_length=20, choices=ReasonType.choices)
    note = models.TextField(max_length=500, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    admin_response = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reports_resolved',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['cultural_object', 'status']),
        ]
        ordering = ['-created_at']
        verbose_name = _('Репорт про неточність')
        verbose_name_plural = _('Репорти про неточності')

    def __str__(self):
        return f'Report #{self.pk} on "{self.cultural_object.title}" by {self.reporter.username} ({self.status})'


class Visit(models.Model):
    """User check-in: 'I've visited this place' — with optional impression and privacy toggle."""

    user = models.ForeignKey(
        User,
        related_name='visits',
        on_delete=models.CASCADE,
    )
    cultural_object = models.ForeignKey(
        CulturalObject,
        related_name='visits',
        on_delete=models.CASCADE,
    )
    visited_at = models.DateTimeField(default=timezone.now)
    impression = models.TextField(
        max_length=1000,
        blank=True,
        help_text='Враження від візиту',
    )
    is_public = models.BooleanField(
        default=False,
        help_text='Чи показувати цей візит у публічному паспорті',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'cultural_object')]
        indexes = [
            models.Index(fields=['user', 'visited_at']),
            models.Index(fields=['cultural_object']),
            models.Index(fields=['is_public', 'user']),
        ]
        ordering = ['-visited_at']
        verbose_name = _('Візит')
        verbose_name_plural = _('Візити')

    def __str__(self):
        return f'{self.user.username} → {self.cultural_object.title} ({self.visited_at})'


class PlannedVisit(models.Model):
    """User wishlist: 'I plan to visit this place' — with optional planned date."""

    user = models.ForeignKey(
        User,
        related_name='planned_visits',
        on_delete=models.CASCADE,
    )
    cultural_object = models.ForeignKey(
        CulturalObject,
        related_name='planned_visits',
        on_delete=models.CASCADE,
    )
    planned_date = models.DateField(
        null=True, blank=True,
        help_text='Опційна планова дата',
    )
    note = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'cultural_object')]
        ordering = ['-created_at']
        verbose_name = _('Заплановане відвідування')
        verbose_name_plural = _('Заплановані відвідування')

    def __str__(self):
        return f'{self.user.username} plans → {self.cultural_object.title}'


class Route(models.Model):
    """Curated multi-stop tourist route through cultural objects."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Чернетка'
        PENDING = 'pending', 'На модерації'
        APPROVED = 'approved', 'Опубліковано'
        ARCHIVED = 'archived', 'В архіві'

    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Особистий'
        PUBLIC = 'public', 'Публічний'

    title = models.CharField(max_length=200)
    description = models.TextField(max_length=2000)
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        help_text='Private — only author sees, no moderation. Public — visible to everyone after approval.',
    )
    author = models.ForeignKey(
        User,
        related_name='routes',
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='routes')
    is_featured = models.BooleanField(default=False)
    cover_photo = models.URLField(blank=True)
    estimated_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    copied_from = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='copies',
        help_text='Якщо маршрут створений як копія',
    )
    # Cached real-road geometry computed via OpenRouteService.
    # geometry is a list of [lng, lat] pairs; null until first calculation.
    route_geometry = models.JSONField(null=True, blank=True)
    route_distance_m = models.PositiveIntegerField(null=True, blank=True)
    route_duration_s = models.PositiveIntegerField(null=True, blank=True)
    geometry_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['visibility', 'status', '-created_at']),
            models.Index(fields=['is_featured', '-created_at']),
            models.Index(fields=['author', 'visibility']),
        ]
        ordering = ['-created_at']
        verbose_name = _('Маршрут')
        verbose_name_plural = _('Маршрути')

    def __str__(self):
        return f'{self.title} ({self.status})'


class RouteStop(models.Model):
    """Single stop in a Route, pointing at a CulturalObject."""

    route = models.ForeignKey(Route, related_name='stops', on_delete=models.CASCADE)
    cultural_object = models.ForeignKey(CulturalObject, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()
    note = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('route', 'cultural_object')]
        ordering = ['order']
        verbose_name = _('Зупинка маршруту')
        verbose_name_plural = _('Зупинки маршруту')

    @property
    def is_unavailable(self) -> bool:
        """Stop is unavailable when its underlying object has been archived."""
        return self.cultural_object.status == CulturalObject.Status.ARCHIVED

    def __str__(self):
        return f'{self.route.title} #{self.order}: {self.cultural_object.title}'
