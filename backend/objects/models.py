"""
Models for the CultureMap Ukraine application.

Core models:
- Tag: Categories for cultural objects (Castle, Church, Museum, etc.)
- CulturalObject: Ukrainian cultural heritage sites with geographic coordinates
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Tag(models.Model):
    """
    Category/type for cultural objects.

    Admin-only creation, users select from existing tags.
    """

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

    class Meta:
        ordering = ['name']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

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

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(
        max_length=200,
        help_text="Name of the cultural object (e.g., 'Lviv Opera House')"
    )

    # Use empty string for "no data", not NULL (Django best practice for text fields)
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the object (optional)"
    )

    # DecimalField for precise coordinates (FloatField has rounding errors)
    # Ukraine boundaries: lat 44.0-52.5°N, lng 22.0-40.5°E
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(44.0, message="Latitude must be within Ukraine (44.0-52.5)"),
            MaxValueValidator(52.5, message="Latitude must be within Ukraine (44.0-52.5)")
        ],
        help_text="Latitude coordinate (44.0 to 52.5 for Ukraine)"
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(22.0, message="Longitude must be within Ukraine (22.0-40.5)"),
            MaxValueValidator(40.5, message="Longitude must be within Ukraine (22.0-40.5)")
        ],
        help_text="Longitude coordinate (22.0 to 40.5 for Ukraine)"
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
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Current moderation status"
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
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"

    def archive(self):
        """
        Soft-delete by changing status to 'archived'.

        Preserves data for recovery, unlike hard delete.
        """
        self.status = 'archived'
        self.archived_at = timezone.now()
        self.save(update_fields=['status', 'archived_at'])

    def restore(self):
        """
        Restore archived object to 'pending' status.

        Requires re-approval (admin review again).
        """
        self.status = 'pending'
        self.archived_at = None
        self.save(update_fields=['status', 'archived_at'])

    def clean(self):
        """Custom validation for multi-field business rules."""
        super().clean()
