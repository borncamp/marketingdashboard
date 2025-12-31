"""
Pydantic models for shipping rules and order management.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date as DateType


class ShippingProfileCreate(BaseModel):
    """Model for creating a new shipping profile."""
    name: str = Field(..., description="Name of the shipping rule")
    description: Optional[str] = Field(None, description="Optional description")
    priority: int = Field(100, description="Priority (lower number = higher priority)")
    is_active: bool = Field(True, description="Whether this rule is active")
    is_default: bool = Field(False, description="Whether this is the default rule")
    match_conditions: Dict[str, Any] = Field(
        ...,
        description="Match conditions as JSON (e.g., {'field': 'product_title', 'operator': 'contains', 'value': '2 plug'})"
    )
    cost_rules: Dict[str, Any] = Field(
        ...,
        description="Cost calculation rules as JSON (e.g., {'type': 'fixed', 'base_cost': 12.0})"
    )


class ShippingProfileUpdate(BaseModel):
    """Model for updating an existing shipping profile."""
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    match_conditions: Optional[Dict[str, Any]] = None
    cost_rules: Optional[Dict[str, Any]] = None


class ShippingProfile(BaseModel):
    """Model for shipping profile response."""
    id: str
    name: str
    description: Optional[str]
    priority: int
    is_active: bool
    is_default: bool
    match_conditions: Dict[str, Any]
    cost_rules: Dict[str, Any]
    created_at: str
    updated_at: str


class OrderItem(BaseModel):
    """Model for order line item."""
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    product_title: str
    variant_title: Optional[str] = None
    quantity: int
    price: float
    total: float


class Order(BaseModel):
    """Model for Shopify order."""
    id: str
    order_number: int
    order_date: DateType
    customer_email: Optional[str] = None
    subtotal: float
    total_price: float
    shipping_charged: float
    shipping_cost_estimated: Optional[float] = None
    currency: str = "USD"
    financial_status: Optional[str] = None
    fulfillment_status: Optional[str] = None
    items: List[OrderItem] = []


class OrderListResponse(BaseModel):
    """Response model for list of orders."""
    orders: List[Order]
    total: int
    limit: int
    offset: int


class ShippingCalculationBreakdown(BaseModel):
    """Breakdown of shipping cost calculation."""
    profile_id: Optional[str]
    profile_name: str
    items: List[str]  # Product titles
    subtotal: float
    cost: float


class ShippingCalculationResult(BaseModel):
    """Result of shipping cost calculation for an order."""
    order_id: str
    total_cost: float
    breakdown: List[ShippingCalculationBreakdown]
    matched_items: List[Dict[str, Any]]  # Details of which rule matched each item


class CalculateShippingRequest(BaseModel):
    """Request to calculate shipping for one or more orders."""
    order_ids: List[str] = Field(..., description="List of order IDs to calculate shipping for")


class ProfileTestRequest(BaseModel):
    """Request to test a shipping profile against sample data."""
    profile: ShippingProfileCreate
    test_data: Dict[str, Any] = Field(
        ...,
        description="Test data (e.g., {'product_title': '2 plug outlet', 'order_subtotal': 35.00})"
    )


class ProfileTestResponse(BaseModel):
    """Response from testing a shipping profile."""
    matched: bool
    calculated_cost: Optional[float] = None
    details: Dict[str, Any]
