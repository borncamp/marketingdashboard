"""
Unit tests for shipping calculation engine.
"""
import pytest
from app.routers.shipping import (
    evaluate_match_conditions,
    evaluate_cost_rules,
    eval_safe_expression,
    match_shipping_profile,
    calculate_order_shipping_cost
)


@pytest.mark.unit
class TestEvaluateMatchConditions:
    """Test evaluate_match_conditions function."""

    def test_contains_match_case_insensitive(self):
        """Test contains operator with case insensitivity."""
        conditions = {
            'field': 'product_title',
            'operator': 'contains',
            'value': '2 plug',
            'case_sensitive': False
        }
        data = {'product_title': 'Test 2 Plug Product'}

        assert evaluate_match_conditions(conditions, data) is True

    def test_contains_match_case_sensitive(self):
        """Test contains operator with case sensitivity."""
        conditions = {
            'field': 'product_title',
            'operator': 'contains',
            'value': '2 plug',
            'case_sensitive': True
        }
        data = {'product_title': 'Test 2 Plug Product'}

        assert evaluate_match_conditions(conditions, data) is False

        # Should match with correct case
        data = {'product_title': 'Test 2 plug Product'}
        assert evaluate_match_conditions(conditions, data) is True

    def test_contains_no_match(self):
        """Test contains operator with no match."""
        conditions = {
            'field': 'product_title',
            'operator': 'contains',
            'value': 'tree',
            'case_sensitive': False
        }
        data = {'product_title': 'Test 2 Plug Product'}

        assert evaluate_match_conditions(conditions, data) is False

    def test_equals_match(self):
        """Test equals operator."""
        conditions = {
            'field': 'category',
            'operator': 'equals',
            'value': 'electronics',
            'case_sensitive': False
        }
        data = {'category': 'Electronics'}

        assert evaluate_match_conditions(conditions, data) is True

    def test_equals_no_match(self):
        """Test equals operator with no match."""
        conditions = {
            'field': 'category',
            'operator': 'equals',
            'value': 'electronics',
            'case_sensitive': False
        }
        data = {'category': 'clothing'}

        assert evaluate_match_conditions(conditions, data) is False

    def test_starts_with_match(self):
        """Test starts_with operator."""
        conditions = {
            'field': 'product_title',
            'operator': 'starts_with',
            'value': 'premium',
            'case_sensitive': False
        }
        data = {'product_title': 'Premium Product Name'}

        assert evaluate_match_conditions(conditions, data) is True

    def test_starts_with_no_match(self):
        """Test starts_with operator with no match."""
        conditions = {
            'field': 'product_title',
            'operator': 'starts_with',
            'value': 'premium',
            'case_sensitive': False
        }
        data = {'product_title': 'Standard Product Name'}

        assert evaluate_match_conditions(conditions, data) is False

    def test_ends_with_match(self):
        """Test ends_with operator."""
        conditions = {
            'field': 'product_title',
            'operator': 'ends_with',
            'value': 'special',
            'case_sensitive': False
        }
        data = {'product_title': 'Product Name Special'}

        assert evaluate_match_conditions(conditions, data) is True

    def test_ends_with_no_match(self):
        """Test ends_with operator with no match."""
        conditions = {
            'field': 'product_title',
            'operator': 'ends_with',
            'value': 'special',
            'case_sensitive': False
        }
        data = {'product_title': 'Product Name Regular'}

        assert evaluate_match_conditions(conditions, data) is False

    def test_regex_match(self):
        """Test regex operator."""
        conditions = {
            'field': 'product_title',
            'operator': 'regex',
            'value': r'\d+ plug',
            'case_sensitive': False
        }
        data = {'product_title': 'Test 2 Plug Product'}

        assert evaluate_match_conditions(conditions, data) is True

    def test_regex_no_match(self):
        """Test regex operator with no match."""
        conditions = {
            'field': 'product_title',
            'operator': 'regex',
            'value': r'\d+ tree',
            'case_sensitive': False
        }
        data = {'product_title': 'Test 2 Plug Product'}

        assert evaluate_match_conditions(conditions, data) is False

    def test_regex_invalid_pattern(self):
        """Test regex operator with invalid pattern."""
        conditions = {
            'field': 'product_title',
            'operator': 'regex',
            'value': '[invalid(',
            'case_sensitive': False
        }
        data = {'product_title': 'Test Product'}

        assert evaluate_match_conditions(conditions, data) is False

    def test_missing_field(self):
        """Test matching when field is missing from data."""
        conditions = {
            'field': 'nonexistent_field',
            'operator': 'contains',
            'value': 'test',
            'case_sensitive': False
        }
        data = {'product_title': 'Test Product'}

        assert evaluate_match_conditions(conditions, data) is False

    def test_empty_value(self):
        """Test matching with empty value."""
        conditions = {
            'field': 'product_title',
            'operator': 'contains',
            'value': '',
            'case_sensitive': False
        }
        data = {'product_title': 'Test Product'}

        assert evaluate_match_conditions(conditions, data) is True  # Empty string is in any string


@pytest.mark.unit
class TestEvaluateCostRules:
    """Test evaluate_cost_rules function."""

    def test_fixed_cost(self):
        """Test fixed cost rule."""
        cost_rules = {
            'type': 'fixed',
            'base_cost': 12.0
        }
        data = {'order_subtotal': 100.0}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 12.0

    def test_per_item_cost(self):
        """Test per-item cost rule."""
        cost_rules = {
            'type': 'per_item',
            'per_item_cost': 5.0
        }
        data = {'quantity': 3}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 15.0

    def test_per_item_default_quantity(self):
        """Test per-item cost with default quantity."""
        cost_rules = {
            'type': 'per_item',
            'per_item_cost': 5.0
        }
        data = {}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 5.0  # Default quantity is 1

    def test_percentage_cost(self):
        """Test percentage-based cost."""
        cost_rules = {
            'type': 'percentage',
            'percentage': 10
        }
        data = {'order_subtotal': 100.0}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 10.0

    def test_percentage_zero_subtotal(self):
        """Test percentage cost with zero subtotal."""
        cost_rules = {
            'type': 'percentage',
            'percentage': 10
        }
        data = {'order_subtotal': 0}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 0.0

    def test_based_on_shipping_charged(self):
        """Test cost based on shipping charged."""
        cost_rules = {
            'type': 'based_on_shipping_charged',
            'adjustment': -5.0
        }
        data = {'shipping_charged': 12.0}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 7.0

    def test_based_on_shipping_charged_negative_prevention(self):
        """Test that shipping cost can't be negative."""
        cost_rules = {
            'type': 'based_on_shipping_charged',
            'adjustment': -20.0
        }
        data = {'shipping_charged': 10.0}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 0.0  # Should be clamped to 0

    def test_conditional_cost_true(self):
        """Test conditional cost rule when condition is true."""
        cost_rules = {
            'type': 'conditional',
            'conditions': [
                {
                    'if': 'order_subtotal >= 49',
                    'then': 0,
                    'else': 12
                }
            ]
        }
        data = {'order_subtotal': 50.0}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 0.0

    def test_conditional_cost_false(self):
        """Test conditional cost rule when condition is false."""
        cost_rules = {
            'type': 'conditional',
            'conditions': [
                {
                    'if': 'order_subtotal >= 49',
                    'then': 0,
                    'else': 12
                }
            ]
        }
        data = {'order_subtotal': 30.0}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 12.0

    def test_conditional_multiple_conditions(self):
        """Test conditional with multiple conditions."""
        cost_rules = {
            'type': 'conditional',
            'conditions': [
                {
                    'if': 'order_subtotal >= 100',
                    'then': 0
                },
                {
                    'if': 'order_subtotal >= 49',
                    'then': 5,
                    'else': 12
                }
            ]
        }

        # First condition matches
        cost = evaluate_cost_rules(cost_rules, {'order_subtotal': 100.0})
        assert cost == 0.0

        # Second condition matches
        cost = evaluate_cost_rules(cost_rules, {'order_subtotal': 50.0})
        assert cost == 5.0

        # No condition matches, use else
        cost = evaluate_cost_rules(cost_rules, {'order_subtotal': 30.0})
        assert cost == 12.0

    def test_conditional_with_base_cost_fallback(self):
        """Test conditional falling back to base_cost."""
        cost_rules = {
            'type': 'conditional',
            'base_cost': 10.0,
            'conditions': []
        }
        data = {'order_subtotal': 50.0}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 10.0

    def test_unknown_rule_type(self):
        """Test unknown rule type defaults to 0."""
        cost_rules = {
            'type': 'unknown_type'
        }
        data = {}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 0.0

    def test_default_rule_type(self):
        """Test default rule type when not specified."""
        cost_rules = {
            'base_cost': 8.0
        }
        data = {}

        cost = evaluate_cost_rules(cost_rules, data)
        assert cost == 8.0  # Defaults to fixed type


@pytest.mark.unit
class TestEvalSafeExpression:
    """Test eval_safe_expression function."""

    def test_valid_comparison_greater_than(self):
        """Test valid greater than comparison."""
        assert eval_safe_expression('50 > 30') is True
        assert eval_safe_expression('30 > 50') is False

    def test_valid_comparison_less_than(self):
        """Test valid less than comparison."""
        assert eval_safe_expression('30 < 50') is True
        assert eval_safe_expression('50 < 30') is False

    def test_valid_comparison_greater_equal(self):
        """Test valid greater than or equal comparison."""
        assert eval_safe_expression('50 >= 50') is True
        assert eval_safe_expression('49 >= 50') is False

    def test_valid_comparison_less_equal(self):
        """Test valid less than or equal comparison."""
        assert eval_safe_expression('30 <= 50') is True
        assert eval_safe_expression('50 <= 30') is False

    def test_valid_comparison_equals(self):
        """Test valid equals comparison."""
        assert eval_safe_expression('50 == 50') is True
        assert eval_safe_expression('50 == 30') is False

    def test_valid_comparison_not_equals(self):
        """Test valid not equals comparison."""
        assert eval_safe_expression('50 != 30') is True
        assert eval_safe_expression('50 != 50') is False

    def test_arithmetic_operations(self):
        """Test arithmetic in expressions."""
        assert eval_safe_expression('10 + 5 > 12') is True
        assert eval_safe_expression('100 - 50 == 50') is True
        assert eval_safe_expression('10 * 5 >= 50') is True
        assert eval_safe_expression('100 / 2 <= 50') is True

    def test_decimal_numbers(self):
        """Test decimal numbers in expressions."""
        assert eval_safe_expression('49.99 < 50.0') is True
        assert eval_safe_expression('50.01 > 50.0') is True

    def test_parentheses(self):
        """Test parentheses in expressions."""
        assert eval_safe_expression('(10 + 5) * 2 == 30') is True

    def test_invalid_characters(self):
        """Test rejection of invalid characters."""
        assert eval_safe_expression('50 > 30 and True') is False  # 'and' contains letters
        assert eval_safe_expression('import os') is False
        assert eval_safe_expression('__import__') is False

    def test_dangerous_patterns(self):
        """Test rejection of dangerous patterns."""
        assert eval_safe_expression('__import__("os")') is False
        assert eval_safe_expression('import os') is False
        assert eval_safe_expression('exec("code")') is False
        assert eval_safe_expression('eval("code")') is False
        assert eval_safe_expression('open("file")') is False

    def test_invalid_syntax(self):
        """Test handling of invalid syntax."""
        assert eval_safe_expression('50 > > 30') is False
        assert eval_safe_expression('((50 > 30') is False

    def test_empty_expression(self):
        """Test empty expression."""
        assert eval_safe_expression('') is False

    def test_spaces(self):
        """Test expressions with various spacing."""
        assert eval_safe_expression('  50  >  30  ') is True


@pytest.mark.unit
class TestMatchShippingProfile:
    """Test match_shipping_profile function."""

    def test_match_first_matching_profile(self):
        """Test that first matching profile is returned."""
        item = {'product_title': '2 Plug Adapter'}
        order = {'order_subtotal': 100.0}
        profiles = [
            {
                'id': 'profile-1',
                'name': 'Low Priority',
                'priority': 100,
                'is_active': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'plug'
                }
            },
            {
                'id': 'profile-2',
                'name': 'High Priority',
                'priority': 10,
                'is_active': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'adapter'
                }
            }
        ]

        # Profiles should be pre-sorted by priority
        sorted_profiles = sorted(profiles, key=lambda p: p['priority'])
        matched = match_shipping_profile(item, order, sorted_profiles)

        assert matched is not None
        assert matched['id'] == 'profile-2'  # Higher priority (lower number)

    def test_skip_inactive_profiles(self):
        """Test that inactive profiles are skipped."""
        item = {'product_title': '2 Plug Adapter'}
        order = {'order_subtotal': 100.0}
        profiles = [
            {
                'id': 'profile-1',
                'name': 'Inactive',
                'priority': 1,
                'is_active': False,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'plug'
                }
            },
            {
                'id': 'profile-2',
                'name': 'Active',
                'priority': 10,
                'is_active': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'adapter'
                }
            }
        ]

        matched = match_shipping_profile(item, order, profiles)

        assert matched is not None
        assert matched['id'] == 'profile-2'

    def test_return_default_if_no_match(self):
        """Test that default profile is returned if no match."""
        item = {'product_title': 'Regular Product'}
        order = {'order_subtotal': 100.0}
        profiles = [
            {
                'id': 'profile-1',
                'name': 'Specific',
                'priority': 10,
                'is_active': True,
                'is_default': False,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'special'
                }
            },
            {
                'id': 'profile-2',
                'name': 'Default',
                'priority': 100,
                'is_active': True,
                'is_default': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'never-matches'
                }
            }
        ]

        matched = match_shipping_profile(item, order, profiles)

        assert matched is not None
        assert matched['id'] == 'profile-2'
        assert matched['is_default'] is True

    def test_return_none_if_no_match_and_no_default(self):
        """Test that None is returned if no match and no default."""
        item = {'product_title': 'Regular Product'}
        order = {'order_subtotal': 100.0}
        profiles = [
            {
                'id': 'profile-1',
                'name': 'Specific',
                'priority': 10,
                'is_active': True,
                'is_default': False,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'special'
                }
            }
        ]

        matched = match_shipping_profile(item, order, profiles)

        assert matched is None

    def test_combines_item_and_order_data(self):
        """Test that item and order data are combined for matching."""
        item = {'product_title': 'Test Product', 'quantity': 2}
        order = {'order_subtotal': 100.0, 'shipping_charged': 10.0}
        profiles = [
            {
                'id': 'profile-1',
                'name': 'Order-based',
                'priority': 10,
                'is_active': True,
                'match_conditions': {
                    'field': 'order_subtotal',
                    'operator': 'equals',
                    'value': '100.0'
                }
            }
        ]

        matched = match_shipping_profile(item, order, profiles)

        assert matched is not None
        assert matched['id'] == 'profile-1'


@pytest.mark.unit
class TestCalculateOrderShippingCost:
    """Test calculate_order_shipping_cost function."""

    def test_calculate_single_item_fixed_cost(self):
        """Test calculation for single item with fixed cost."""
        order = {'id': 'order-1', 'subtotal': 100.0, 'shipping_charged': 12.0}
        items = [
            {'product_title': '2 Plug Adapter', 'quantity': 1, 'total': 100.0}
        ]
        profiles = [
            {
                'id': 'profile-1',
                'name': '2-Plug Rule',
                'priority': 10,
                'is_active': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': '2 plug'
                },
                'cost_rules': {
                    'type': 'fixed',
                    'base_cost': 12.0
                }
            }
        ]

        result = calculate_order_shipping_cost(order, items, profiles)

        assert result['total_cost'] == 12.0
        assert len(result['breakdown']) == 1
        assert result['breakdown'][0]['cost'] == 12.0

    def test_calculate_multiple_items_different_rules(self):
        """Test calculation for multiple items with different rules."""
        order = {'id': 'order-1', 'subtotal': 150.0, 'shipping_charged': 20.0}
        items = [
            {'product_title': '2 Plug Adapter', 'quantity': 1, 'total': 50.0},
            {'product_title': 'Tree Decoration', 'quantity': 2, 'total': 100.0}
        ]
        profiles = [
            {
                'id': 'profile-1',
                'name': '2-Plug Rule',
                'priority': 10,
                'is_active': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': '2 plug'
                },
                'cost_rules': {
                    'type': 'fixed',
                    'base_cost': 12.0
                }
            },
            {
                'id': 'profile-2',
                'name': 'Tree Rule',
                'priority': 20,
                'is_active': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'tree'
                },
                'cost_rules': {
                    'type': 'per_item',
                    'per_item_cost': 15.0
                }
            }
        ]

        result = calculate_order_shipping_cost(order, items, profiles)

        assert result['total_cost'] == 42.0  # 12 + 30 (15 * 2)
        assert len(result['breakdown']) == 2

    def test_calculate_conditional_rule_free_shipping(self):
        """Test conditional rule for free shipping over threshold."""
        order = {'id': 'order-1', 'subtotal': 100.0, 'shipping_charged': 0.0}
        items = [
            {'product_title': 'Test Product', 'quantity': 1, 'total': 100.0}
        ]
        profiles = [
            {
                'id': 'profile-1',
                'name': 'Free Shipping Rule',
                'priority': 10,
                'is_active': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'test'
                },
                'cost_rules': {
                    'type': 'conditional',
                    'conditions': [
                        {
                            'if': 'order_subtotal >= 49',
                            'then': 0,
                            'else': 12
                        }
                    ]
                }
            }
        ]

        result = calculate_order_shipping_cost(order, items, profiles)

        assert result['total_cost'] == 0.0

    def test_calculate_with_inactive_profile(self):
        """Test that inactive profiles are skipped."""
        order = {'id': 'order-1', 'subtotal': 50.0, 'shipping_charged': 10.0}
        items = [
            {'product_title': 'Test Product', 'quantity': 1, 'total': 50.0}
        ]
        profiles = [
            {
                'id': 'profile-1',
                'name': 'Inactive Rule',
                'priority': 1,
                'is_active': False,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'test'
                },
                'cost_rules': {
                    'type': 'fixed',
                    'base_cost': 100.0
                }
            },
            {
                'id': 'profile-2',
                'name': 'Active Rule',
                'priority': 10,
                'is_active': True,
                'is_default': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'never'
                },
                'cost_rules': {
                    'type': 'fixed',
                    'base_cost': 8.0
                }
            }
        ]

        result = calculate_order_shipping_cost(order, items, profiles)

        # Should use default rule since active specific rule doesn't match
        assert result['total_cost'] == 8.0

    def test_calculate_groups_items_by_profile(self):
        """Test that items are grouped by matched profile."""
        order = {'id': 'order-1', 'subtotal': 200.0, 'shipping_charged': 20.0}
        items = [
            {'product_title': '2 Plug Adapter A', 'quantity': 1, 'total': 50.0},
            {'product_title': '2 Plug Adapter B', 'quantity': 1, 'total': 50.0},
            {'product_title': 'Regular Product', 'quantity': 1, 'total': 100.0}
        ]
        profiles = [
            {
                'id': 'profile-1',
                'name': '2-Plug Rule',
                'priority': 10,
                'is_active': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': '2 plug'
                },
                'cost_rules': {
                    'type': 'fixed',
                    'base_cost': 12.0
                }
            },
            {
                'id': 'profile-2',
                'name': 'Default Rule',
                'priority': 100,
                'is_active': True,
                'is_default': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'never'
                },
                'cost_rules': {
                    'type': 'fixed',
                    'base_cost': 8.0
                }
            }
        ]

        result = calculate_order_shipping_cost(order, items, profiles)

        # Should have two groups: one for 2-plug items, one for default
        assert len(result['breakdown']) == 2
        assert result['total_cost'] == 20.0  # 12 + 8

        # Check that breakdown shows correct grouping
        plug_group = next((b for b in result['breakdown'] if b['profile_id'] == 'profile-1'), None)
        assert plug_group is not None
        assert len(plug_group['items']) == 2

    def test_calculate_empty_items(self):
        """Test calculation with no items."""
        order = {'id': 'order-1', 'subtotal': 0.0, 'shipping_charged': 0.0}
        items = []
        profiles = []

        result = calculate_order_shipping_cost(order, items, profiles)

        assert result['total_cost'] == 0.0
        assert len(result['breakdown']) == 0
        assert len(result['matched_items']) == 0

    def test_matched_items_structure(self):
        """Test that matched_items contains proper structure."""
        order = {'id': 'order-1', 'subtotal': 50.0, 'shipping_charged': 10.0}
        items = [
            {'product_title': 'Test Product', 'quantity': 1, 'total': 50.0}
        ]
        profiles = [
            {
                'id': 'profile-1',
                'name': 'Test Rule',
                'priority': 10,
                'is_active': True,
                'match_conditions': {
                    'field': 'product_title',
                    'operator': 'contains',
                    'value': 'test'
                },
                'cost_rules': {
                    'type': 'fixed',
                    'base_cost': 10.0
                }
            }
        ]

        result = calculate_order_shipping_cost(order, items, profiles)

        assert len(result['matched_items']) == 1
        matched_item = result['matched_items'][0]
        assert 'item' in matched_item
        assert 'profile' in matched_item
        assert 'profile_id' in matched_item
        assert 'profile_name' in matched_item
        assert matched_item['profile_id'] == 'profile-1'
        assert matched_item['profile_name'] == 'Test Rule'
