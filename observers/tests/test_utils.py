from uuid import uuid4

from django.test import TestCase

from commons.constants import BettingApps, SeedNames
from observers.models import Multiplier

# from observers.utils import get_new_multipliers, parse_multipliers
from observers.utils import calculate_jaccard_similarity, get_new_multipliers
from workers.models import Worker

# class ParsePayoutsTestCase(TestCase):
#     def test_valid_input(self):
#         """Test with a valid input string"""
#         input_string = "1.82x, 2.45x, 3.50x"
#         expected_output = [1.82, 2.45, 3.50]
#         self.assertEqual(parse_multipliers(input_string), expected_output)

#     def test_valid_input_no_spaces(self):
#         """Test with valid input string without spaces"""
#         input_string = "1.82x,2.45x,3.50x"
#         expected_output = [1.82, 2.45, 3.50]
#         self.assertEqual(parse_multipliers(input_string), expected_output)

#     def test_empty_input(self):
#         """Test with an empty input string"""
#         with self.assertRaises(ValueError) as context:
#             parse_multipliers("")
#         self.assertEqual(str(context.exception), ErrorCodes.EMPTY_MULTIPLIER_STRING)

#     def test_invalid_format(self):
#         """Test with an invalid format"""
#         input_string = "1.82, 2.45x, 3.50y"
#         with self.assertRaises(ValueError) as context:
#             parse_multipliers(input_string)
#         self.assertEqual(str(context.exception), ErrorCodes.INVALID_MULTIPLIER_STRING)

#     def test_non_numeric_values(self):
#         """Test with non-numeric values"""
#         input_string = "abcx, 2.45x, 3.50x"
#         with self.assertRaises(ValueError) as context:
#             parse_multipliers(input_string)
#         self.assertEqual(str(context.exception), ErrorCodes.INVALID_MULTIPLIER_STRING)

#     def test_non_string_input(self):
#         """Test with non-string input"""
#         input_data = 12345
#         with self.assertRaises(ValueError) as context:
#             parse_multipliers(input_data)
#         self.assertEqual(str(context.exception), ErrorCodes.EMPTY_MULTIPLIER_STRING)

#     def test_extra_whitespace(self):
#         """Test with extra whitespace in the string"""
#         input_string = "  1.82x  ,   2.45x  , 3.50x "
#         expected_output = [1.82, 2.45, 3.50]
#         self.assertEqual(parse_multipliers(input_string), expected_output)

#     def test_large_numbers(self):
#         """Test with large numbers"""
#         input_string = "12345.67x, 98765.43x"
#         expected_output = [12345.67, 98765.43]
#         self.assertEqual(parse_multipliers(input_string), expected_output)

#     def test_single_value(self):
#         """Test with a single valid multiplier"""
#         input_string = "5.67x"
#         expected_output = [5.67]
#         self.assertEqual(parse_multipliers(input_string), expected_output)


class GetNewPayoutsTestCase(TestCase):
    cleaned_payouts_string: list[float]
    worker: Worker

    @classmethod
    def setUpTestData(cls) -> None:
        cls.multipliers_list = [1.21, 4.33, 1.18]
        cls.worker = Worker.objects.create(
            app=BettingApps.BETIKA.value, name=SeedNames.list()[0], key=uuid4()
        )

    def test_new_multipliers_when_model_is_empty(self) -> None:
        """Test the func. returns all multipliers when the Multiplier model is empty"""
        new_multipliers = get_new_multipliers(
            worker_id=self.worker.id, new_multipliers_list=self.multipliers_list
        )
        self.assertListEqual(new_multipliers, self.multipliers_list)

    def test_new_multipliers_when_model_is_not_empty(self) -> None:
        """Test the func. returns only the new payouts"""
        # Reverse the payouts_list because the last element is the earliest payout
        objs = [
            Multiplier(worker=self.worker, crash=crash)
            for crash in self.multipliers_list[::-1]
        ]  # type: ignore
        Multiplier.objects.bulk_create(objs)

        new_multipliers_list = get_new_multipliers(
            worker_id=self.worker.id,
            new_multipliers_list=[5.67, 1.00, 1.21] + self.multipliers_list,
        )

        self.assertListEqual(new_multipliers_list, [5.67, 1.00, 1.21])


class TestJaccardSimilarity(TestCase):
    def test_identical_sets(self) -> None:
        set_1 = {1, 2, 3}
        set_2 = {1, 2, 3}
        similarity = calculate_jaccard_similarity(set_1, set_2)
        self.assertEqual(
            similarity, 1.0, "Identical sets should have similarity of 1.0"
        )

    def test_completely_different_sets(self) -> None:
        set_1 = {1, 2, 3}
        set_2 = {4, 5, 6}
        similarity = calculate_jaccard_similarity(set_1, set_2)
        self.assertEqual(
            similarity, 0.0, "Completely different sets should have similarity of 0.0"
        )

    def test_partially_overlapping_sets(self) -> None:
        set_1 = {1, 2, 3}
        set_2 = {2, 3, 4}
        similarity = calculate_jaccard_similarity(set_1, set_2)
        expected_similarity = 2 / 4  # Intersection: {2, 3}, Union: {1, 2, 3, 4}
        self.assertAlmostEqual(similarity, expected_similarity, places=2)

    def test_empty_sets(self) -> None:
        set_1 = set()
        set_2 = set()
        similarity = calculate_jaccard_similarity(set_1, set_2)
        self.assertEqual(similarity, 0.0, "Empty sets should have similarity of 0.0")

    def test_one_empty_one_non_empty_set(self) -> None:
        set_1 = {1, 2, 3}
        set_2 = set()
        similarity = calculate_jaccard_similarity(set_1, set_2)
        self.assertEqual(similarity, 0.0, "One empty set should have similarity of 0.0")
