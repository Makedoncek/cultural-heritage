from django.test import TestCase
from django.core.exceptions import ValidationError
from objects.validators import is_within_ukraine, validate_coordinates_within_ukraine


class IsWithinUkraineTest(TestCase):
    """Tests for the is_within_ukraine function."""

    def test_kyiv_is_within(self):
        self.assertTrue(is_within_ukraine(50.4501, 30.5234))

    def test_lviv_is_within(self):
        self.assertTrue(is_within_ukraine(49.8397, 24.0297))

    def test_odesa_is_within(self):
        self.assertTrue(is_within_ukraine(46.4825, 30.7233))

    def test_kharkiv_is_within(self):
        self.assertTrue(is_within_ukraine(49.9935, 36.2304))

    def test_crimea_is_within(self):
        self.assertTrue(is_within_ukraine(44.4307, 34.1286))

    def test_bucharest_is_outside(self):
        self.assertFalse(is_within_ukraine(44.4268, 26.1025))

    def test_minsk_is_outside(self):
        self.assertFalse(is_within_ukraine(53.9006, 27.5590))

    def test_warsaw_is_outside(self):
        self.assertFalse(is_within_ukraine(52.2297, 21.0122))


class ValidateCoordinatesWithinUkraineTest(TestCase):
    """Tests for the validate_coordinates_within_ukraine function."""

    def test_valid_coordinates_no_error(self):
        validate_coordinates_within_ukraine(50.4501, 30.5234)

    def test_invalid_coordinates_raises_error(self):
        with self.assertRaises(ValidationError):
            validate_coordinates_within_ukraine(52.2297, 21.0122)
