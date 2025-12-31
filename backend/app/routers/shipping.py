"""
Shipping rules management and calculation endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from app.database import ShippingDatabase
from app.auth import verify_credentials
from app.models.shipping import (
    ShippingProfile,
    ShippingProfileCreate,
    ShippingProfileUpdate,
    ShippingCalculationResult,
    ProfileTestRequest,
    ProfileTestResponse
)
import json

router = APIRouter(
    prefix="/api/shipping",
    tags=["shipping"],
    dependencies=[Depends(verify_credentials)]
)


# ============================================================================
# Shipping Profiles Management
# ============================================================================

@router.get("/profiles", response_model=List[ShippingProfile])
async def get_shipping_profiles(active_only: bool = False):
    """
    Get all shipping profiles ordered by priority.

    Args:
        active_only: If True, only return active profiles

    Returns:
        List of shipping profiles
    """
    try:
        profiles = ShippingDatabase.get_shipping_profiles(active_only=active_only)
        return profiles
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch shipping profiles: {str(e)}"
        )


@router.post("/profiles")
async def create_shipping_profile(profile: ShippingProfileCreate):
    """
    Create a new shipping profile.

    Args:
        profile: Shipping profile data

    Returns:
        Created profile ID and success status
    """
    try:
        profile_id = ShippingDatabase.upsert_shipping_profile(profile.dict())

        return {
            "success": True,
            "profile_id": profile_id,
            "message": "Shipping profile created successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create shipping profile: {str(e)}"
        )


@router.put("/profiles/{profile_id}")
async def update_shipping_profile(profile_id: str, profile: ShippingProfileUpdate):
    """
    Update an existing shipping profile.

    Args:
        profile_id: ID of profile to update
        profile: Updated profile data

    Returns:
        Success status
    """
    try:
        # Get existing profile
        profiles = ShippingDatabase.get_shipping_profiles()
        existing = next((p for p in profiles if p['id'] == profile_id), None)

        if not existing:
            raise HTTPException(status_code=404, detail="Shipping profile not found")

        # Merge updates with existing data
        updated_data = existing.copy()
        for key, value in profile.dict(exclude_unset=True).items():
            if value is not None:
                updated_data[key] = value

        ShippingDatabase.upsert_shipping_profile(updated_data)

        return {
            "success": True,
            "message": "Shipping profile updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update shipping profile: {str(e)}"
        )


@router.delete("/profiles/{profile_id}")
async def delete_shipping_profile(profile_id: str):
    """
    Delete a shipping profile.

    Args:
        profile_id: ID of profile to delete

    Returns:
        Success status
    """
    try:
        ShippingDatabase.delete_shipping_profile(profile_id)

        return {
            "success": True,
            "message": "Shipping profile deleted successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete shipping profile: {str(e)}"
        )


# ============================================================================
# Rule Testing
# ============================================================================

@router.post("/profiles/test", response_model=ProfileTestResponse)
async def test_profile_match(test_request: ProfileTestRequest):
    """
    Test a shipping profile against sample data to see if it matches
    and what cost it would calculate.

    Args:
        test_request: Profile and test data

    Returns:
        Match result and calculated cost
    """
    try:
        profile_data = test_request.profile.dict()
        test_data = test_request.test_data

        # Check if profile matches test data
        matched = evaluate_match_conditions(
            profile_data['match_conditions'],
            test_data
        )

        calculated_cost = None
        details = {}

        if matched:
            # Calculate cost using test data
            calculated_cost = evaluate_cost_rules(
                profile_data['cost_rules'],
                test_data
            )
            details = {
                "match_conditions": profile_data['match_conditions'],
                "cost_rules": profile_data['cost_rules'],
                "test_data": test_data
            }

        return {
            "matched": matched,
            "calculated_cost": calculated_cost,
            "details": details
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test profile: {str(e)}"
        )


# ============================================================================
# Rule Matching and Calculation Engine
# ============================================================================

def evaluate_match_conditions(match_conditions: Dict[str, Any], data: Dict[str, Any]) -> bool:
    """
    Evaluate if data matches the given conditions.

    Args:
        match_conditions: Conditions to check (field, operator, value, case_sensitive)
        data: Data to check against

    Returns:
        True if matches, False otherwise
    """
    field = match_conditions.get('field')
    operator = match_conditions.get('operator', 'contains')
    match_value = str(match_conditions.get('value', ''))
    case_sensitive = match_conditions.get('case_sensitive', False)

    # Get field value from data
    field_value = str(data.get(field, ''))

    # Apply case sensitivity
    if not case_sensitive:
        field_value = field_value.lower()
        match_value = match_value.lower()

    # Apply operator
    if operator == 'contains':
        return match_value in field_value
    elif operator == 'equals':
        return match_value == field_value
    elif operator == 'starts_with':
        return field_value.startswith(match_value)
    elif operator == 'ends_with':
        return field_value.endswith(match_value)
    elif operator == 'regex':
        import re
        try:
            pattern = re.compile(match_value, re.IGNORECASE if not case_sensitive else 0)
            return bool(pattern.search(field_value))
        except:
            return False

    return False


def evaluate_cost_rules(cost_rules: Dict[str, Any], data: Dict[str, Any]) -> float:
    """
    Evaluate cost calculation rules.

    Args:
        cost_rules: Cost calculation rules
        data: Order/item data for calculation

    Returns:
        Calculated cost
    """
    rule_type = cost_rules.get('type', 'fixed')

    if rule_type == 'fixed':
        return float(cost_rules.get('base_cost', 0))

    elif rule_type == 'per_item':
        quantity = int(data.get('quantity', 1))
        per_item_cost = float(cost_rules.get('per_item_cost', 0))
        return per_item_cost * quantity

    elif rule_type == 'percentage':
        subtotal = float(data.get('order_subtotal', 0))
        percentage = float(cost_rules.get('percentage', 0))
        return subtotal * (percentage / 100)

    elif rule_type == 'based_on_shipping_charged':
        # Calculate cost based on what customer was charged for shipping
        # e.g., shipping_charged - $5
        shipping_charged = float(data.get('shipping_charged', 0))
        adjustment = float(cost_rules.get('adjustment', 0))
        return max(0, shipping_charged + adjustment)  # Prevent negative costs

    elif rule_type == 'conditional':
        # Evaluate conditional rules
        conditions = cost_rules.get('conditions', [])

        for condition in conditions:
            if_clause = condition.get('if', '')

            # Replace variables with actual values
            expression = if_clause
            for key, value in data.items():
                expression = expression.replace(key, str(value))

            # Safely evaluate expression
            try:
                if eval_safe_expression(expression):
                    return float(condition.get('then', 0))
            except:
                continue

        # If no condition matched, use else or base_cost
        if conditions:
            return float(conditions[-1].get('else', cost_rules.get('base_cost', 0)))
        return float(cost_rules.get('base_cost', 0))

    return 0.0


def eval_safe_expression(expr: str) -> bool:
    """
    Safely evaluate simple comparison expressions.
    Only allows numbers, comparison operators, and basic math.

    Args:
        expr: Expression to evaluate

    Returns:
        Boolean result of evaluation
    """
    # Only allow safe characters
    allowed_chars = set('0123456789.+-*/()><=! ')
    if not all(c in allowed_chars for c in expr):
        return False

    # Additional safety: check for dangerous patterns
    dangerous_patterns = ['__', 'import', 'exec', 'eval', 'compile', 'open']
    if any(pattern in expr.lower() for pattern in dangerous_patterns):
        return False

    try:
        result = eval(expr)
        return bool(result)
    except:
        return False


def match_shipping_profile(item: Dict[str, Any], order: Dict[str, Any], profiles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Find the first matching shipping profile for an item.

    Args:
        item: Item data
        order: Order data
        profiles: List of profiles sorted by priority

    Returns:
        Matching profile or None
    """
    for profile in profiles:
        if not profile.get('is_active', True):
            continue

        match_conditions = profile.get('match_conditions', {})

        # Combine item and order data for matching
        combined_data = {**order, **item}

        if evaluate_match_conditions(match_conditions, combined_data):
            return profile

    # Return default profile if no match
    return next((p for p in profiles if p.get('is_default')), None)


def calculate_order_shipping_cost(order: Dict[str, Any], items: List[Dict[str, Any]], profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate shipping cost for an order using user-defined rules.

    Args:
        order: Order data
        items: List of order items
        profiles: List of shipping profiles

    Returns:
        Calculation result with breakdown
    """
    matched_items = []
    total_cost = 0.0

    # Sort profiles by priority (lower number = higher priority)
    sorted_profiles = sorted(profiles, key=lambda p: p.get('priority', 100))

    # Match each item to a profile
    for item in items:
        profile = match_shipping_profile(item, order, sorted_profiles)

        matched_items.append({
            'item': item,
            'profile': profile,
            'profile_id': profile['id'] if profile else None,
            'profile_name': profile['name'] if profile else 'No Rule Match'
        })

    # Group by profile for cost calculation
    profile_groups = {}
    for matched in matched_items:
        profile_id = matched['profile_id'] or 'no_match'

        if profile_id not in profile_groups:
            profile_groups[profile_id] = {
                'profile': matched['profile'],
                'items': [],
                'subtotal': 0.0
            }

        profile_groups[profile_id]['items'].append(matched['item'])
        profile_groups[profile_id]['subtotal'] += float(matched['item'].get('total', 0))

    # Calculate cost per profile
    breakdown = []
    for profile_id, group in profile_groups.items():
        if not group['profile']:
            continue

        profile = group['profile']
        cost_rules = profile.get('cost_rules', {})

        # Prepare data for cost calculation
        calc_data = {
            'order_subtotal': float(order.get('subtotal', 0)),
            'group_subtotal': group['subtotal'],
            'item_count': len(group['items']),
            'quantity': sum(item.get('quantity', 1) for item in group['items']),
            'shipping_charged': float(order.get('shipping_charged', 0))
        }

        # Evaluate user-defined cost logic
        cost = evaluate_cost_rules(cost_rules, calc_data)

        total_cost += cost
        breakdown.append({
            'profile_id': profile_id,
            'profile_name': profile['name'],
            'items': [item.get('product_title', '') for item in group['items']],
            'subtotal': group['subtotal'],
            'cost': cost
        })

    return {
        'total_cost': total_cost,
        'breakdown': breakdown,
        'matched_items': matched_items
    }
