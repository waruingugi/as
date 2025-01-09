from decimal import Decimal

from django.test import TestCase

from commons.errors import ErrorCodes
from observers.utils import parse_multipliers


class ParsePayoutsTestCase(TestCase):
    def test_valid_input(self):
        """Test with a valid input string"""
        input_string = "1.82x, 2.45x, 3.50x"
        expected_output = [Decimal("1.82"), Decimal("2.45"), Decimal("3.50")]
        self.assertEqual(parse_multipliers(input_string), expected_output)

    def test_valid_input_no_spaces(self):
        """Test with valid input string without spaces"""
        input_string = "1.82x,2.45x,3.50x"
        expected_output = [Decimal("1.82"), Decimal("2.45"), Decimal("3.50")]
        self.assertEqual(parse_multipliers(input_string), expected_output)

    def test_empty_input(self):
        """Test with an empty input string"""
        with self.assertRaises(ValueError) as context:
            parse_multipliers("")
        self.assertEqual(str(context.exception), ErrorCodes.EMPTY_MULTIPLIER_STRING)

    def test_invalid_format(self):
        """Test with an invalid format"""
        input_string = "1.82, 2.45x, 3.50y"
        with self.assertRaises(ValueError) as context:
            parse_multipliers(input_string)
        self.assertEqual(str(context.exception), ErrorCodes.INVALID_MULTIPLIER_STRING)

    def test_non_numeric_values(self):
        """Test with non-numeric values"""
        input_string = "abcx, 2.45x, 3.50x"
        with self.assertRaises(ValueError) as context:
            parse_multipliers(input_string)
        self.assertEqual(str(context.exception), ErrorCodes.INVALID_MULTIPLIER_STRING)

    def test_non_string_input(self):
        """Test with non-string input"""
        input_data = 12345
        with self.assertRaises(ValueError) as context:
            parse_multipliers(input_data)
        self.assertEqual(str(context.exception), ErrorCodes.EMPTY_MULTIPLIER_STRING)

    def test_extra_whitespace(self):
        """Test with extra whitespace in the string"""
        input_string = "  1.82x  ,   2.45x  , 3.50x "
        expected_output = [Decimal("1.82"), Decimal("2.45"), Decimal("3.50")]
        self.assertEqual(parse_multipliers(input_string), expected_output)

    def test_large_numbers(self):
        """Test with large numbers"""
        input_string = "12345.67x, 98765.43x"
        expected_output = [Decimal("12345.67"), Decimal("98765.43")]
        self.assertEqual(parse_multipliers(input_string), expected_output)

    def test_single_value(self):
        """Test with a single valid multiplier"""
        input_string = "5.67x"
        expected_output = [Decimal("5.67")]
        self.assertEqual(parse_multipliers(input_string), expected_output)
