"""
Test suite for the objects app models.

Tests cover: model creation, field validation, methods, and relationships.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
from objects.models import Tag, CulturalObject
from django.db import IntegrityError


class TagModelTest(TestCase):
    """Test suite for the Tag model."""

    def test_tag_creation(self):
        """Test that a Tag can be created with valid data."""
        tag = Tag.objects.create(
            name="Castle",
            slug="castle",
            icon="🏰"
        )

        saved_tag = Tag.objects.get(id=tag.id)

        self.assertEqual(saved_tag.name, "Castle")
        self.assertEqual(saved_tag.slug, "castle")
        self.assertEqual(saved_tag.icon, "🏰")

    def test_tag_str_method(self):
        """Test the __str__ method returns the tag name."""
        tag = Tag.objects.create(name="Museum", slug="museum", icon="🏛️")

        tag_str = str(tag)

        self.assertEqual(tag_str, "Museum")

    def test_tag_unique_name(self):
        """Test that tag names must be unique."""
        Tag.objects.create(name="Church", slug="church", icon="⛪")

        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="Church", slug="church-2", icon="⛪")

    def test_tag_ordering(self):
        """Test that tags are ordered alphabetically by name."""
        Tag.objects.create(name="Zoo", slug="zoo", icon="🦁")
        Tag.objects.create(name="Castle", slug="castle", icon="🏰")
        Tag.objects.create(name="Museum", slug="museum", icon="🏛️")

        tags = list(Tag.objects.all())

        self.assertEqual(tags[0].name, "Castle")
        self.assertEqual(tags[1].name, "Museum")
        self.assertEqual(tags[2].name, "Zoo")

    def test_tag_slug_auto_generated(self):
        """Test that slug is auto-generated from name when not provided."""
        tag = Tag.objects.create(name="Historical Monument", icon="🏛️")

        self.assertEqual(tag.slug, "historical-monument")

    def test_tag_slug_not_overwritten(self):
        """Test that explicit slug is preserved, not overwritten."""
        tag = Tag.objects.create(name="Castle", slug="my-custom-slug", icon="🏰")

        self.assertEqual(tag.slug, "my-custom-slug")


class CulturalObjectModelTest(TestCase):
    """Test suite for the CulturalObject model."""

    def setUp(self):
        """Set up test data used across multiple tests."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

        self.tag_castle = Tag.objects.create(
            name="Castle",
            slug="castle",
            icon="🏰"
        )
        self.tag_museum = Tag.objects.create(
            name="Museum",
            slug="museum",
            icon="🏛️"
        )

    def test_cultural_object_creation(self):
        """Test creating a CulturalObject with valid data."""
        obj = CulturalObject.objects.create(
            title="Lviv Opera House",
            description="Beautiful opera house in Lviv",
            latitude=Decimal('49.843889'),
            longitude=Decimal('24.025556'),
            author=self.user
        )
        obj.tags.add(self.tag_museum)

        self.assertIsNotNone(obj.id)
        self.assertEqual(obj.title, "Lviv Opera House")
        self.assertEqual(obj.author, self.user)
        self.assertIn(self.tag_museum, obj.tags.all())

    def test_default_status_is_pending(self):
        """Test that new objects default to 'pending' status."""
        obj = CulturalObject.objects.create(
            title="Test Object",
            latitude=Decimal('50.0'),
            longitude=Decimal('30.0'),
            author=self.user
        )

        self.assertEqual(obj.status, CulturalObject.Status.PENDING)

    def test_latitude_validation_too_low(self):
        """Test that latitude below 44.0 is rejected (Ukraine boundary)."""
        obj = CulturalObject(
            title="Invalid South",
            latitude=Decimal('43.0'),
            longitude=Decimal('30.0'),
            author=self.user
        )

        with self.assertRaises(ValidationError) as context:
            obj.full_clean()

        self.assertIn('latitude', context.exception.message_dict)

    def test_latitude_validation_too_high(self):
        """Test that latitude above 52.5 is rejected (Ukraine boundary)."""
        obj = CulturalObject(
            title="Invalid North",
            latitude=Decimal('53.0'),
            longitude=Decimal('30.0'),
            author=self.user
        )

        with self.assertRaises(ValidationError):
            obj.full_clean()

    def test_longitude_validation(self):
        """Test that longitude must be between 22.0 and 40.5 (Ukraine)."""
        # Too far west (< 22.0)
        obj_west = CulturalObject(
            title="Too Far West",
            latitude=Decimal('50.0'),
            longitude=Decimal('21.0'),
            author=self.user
        )
        with self.assertRaises(ValidationError):
            obj_west.full_clean()

        # Too far east (> 40.5)
        obj_east = CulturalObject(
            title="Too Far East",
            latitude=Decimal('50.0'),
            longitude=Decimal('41.0'),
            author=self.user
        )
        with self.assertRaises(ValidationError):
            obj_east.full_clean()

    def test_archive_method(self):
        """Test the archive() method for soft delete."""
        obj = CulturalObject.objects.create(
            title="To Be Archived",
            latitude=Decimal('50.0'),
            longitude=Decimal('30.0'),
            author=self.user
        )
        original_status = obj.status

        obj.archive()

        self.assertEqual(obj.status, CulturalObject.Status.ARCHIVED)
        self.assertIsNotNone(obj.archived_at)
        self.assertEqual(original_status, CulturalObject.Status.PENDING)

        # Verify changes were saved
        obj_from_db = CulturalObject.objects.get(id=obj.id)
        self.assertEqual(obj_from_db.status, CulturalObject.Status.ARCHIVED)
        self.assertIsNotNone(obj_from_db.archived_at)

    def test_restore_method(self):
        """Test the restore() method returns object to 'pending' status."""
        obj = CulturalObject.objects.create(
            title="To Be Restored",
            latitude=Decimal('50.0'),
            longitude=Decimal('30.0'),
            author=self.user
        )
        obj.archive()

        obj.restore()

        self.assertEqual(obj.status, CulturalObject.Status.PENDING)
        self.assertIsNone(obj.archived_at)

        # Verify changes were saved
        obj_from_db = CulturalObject.objects.get(id=obj.id)
        self.assertEqual(obj_from_db.status, CulturalObject.Status.PENDING)
        self.assertIsNone(obj_from_db.archived_at)

    def test_str_method(self):
        """Test that __str__ returns 'title (status)' format."""
        obj = CulturalObject.objects.create(
            title="Kyiv Cathedral",
            latitude=Decimal('50.0'),
            longitude=Decimal('30.0'),
            author=self.user,
            status=CulturalObject.Status.APPROVED
        )

        obj_str = str(obj)

        self.assertEqual(obj_str, "Kyiv Cathedral (approved)")

    def test_timestamps_auto_set(self):
        """Test that created_at and updated_at are automatically set."""
        obj = CulturalObject.objects.create(
            title="Timestamp Test",
            latitude=Decimal('50.0'),
            longitude=Decimal('30.0'),
            author=self.user
        )

        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)

        original_created_at = obj.created_at
        original_updated_at = obj.updated_at

        # Modify and save object
        import time
        time.sleep(0.01)
        obj.title = "Modified Title"
        obj.save()

        # updated_at changed, but created_at didn't
        self.assertEqual(obj.created_at, original_created_at)
        self.assertNotEqual(obj.updated_at, original_updated_at)

    def test_many_to_many_tags(self):
        """Test the ManyToMany relationship with Tags."""
        obj = CulturalObject.objects.create(
            title="Multi-Tag Object",
            latitude=Decimal('50.0'),
            longitude=Decimal('30.0'),
            author=self.user
        )

        obj.tags.add(self.tag_castle, self.tag_museum)

        # Object has both tags
        self.assertEqual(obj.tags.count(), 2)
        self.assertIn(self.tag_castle, obj.tags.all())
        self.assertIn(self.tag_museum, obj.tags.all())

        # Reverse relationship: tag → objects
        castle_objects = self.tag_castle.cultural_objects.all()
        museum_objects = self.tag_museum.cultural_objects.all()
        self.assertIn(obj, museum_objects)
        self.assertIn(obj, castle_objects)

    def test_archive_already_archived_is_noop(self):
        """Test that archiving an already archived object does nothing."""
        obj = CulturalObject.objects.create(
            title="Already Archived",
            latitude=Decimal('50.0'),
            longitude=Decimal('30.0'),
            author=self.user
        )
        obj.archive()
        original_archived_at = obj.archived_at

        obj.archive()

        # archived_at should not be updated
        self.assertEqual(obj.archived_at, original_archived_at)

    def test_restore_non_archived_is_noop(self):
        """Test that restoring a non-archived object does nothing."""
        obj = CulturalObject.objects.create(
            title="Pending Object",
            latitude=Decimal('50.0'),
            longitude=Decimal('30.0'),
            author=self.user
        )
        obj.status = CulturalObject.Status.APPROVED

        obj.restore()

        # Status should remain same, without change
        self.assertEqual(obj.status, CulturalObject.Status.APPROVED)
