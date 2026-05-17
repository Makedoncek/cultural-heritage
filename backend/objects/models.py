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
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

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
        verbose_name = 'Cultural Object'
        verbose_name_plural = 'Cultural Objects'

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

    def __str__(self):
        return f'{self.user.username} → {self.cultural_object.title}'


class FavoriteAuthor(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_authors')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'author')
        ordering = ['-created_at']

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

    def __str__(self):
        return f'Photo {self.id} ({self.status}) for {self.cultural_object.title}'
