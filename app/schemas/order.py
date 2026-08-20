from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PickupType = Literal["ASAP", "SCHEDULED"]
OrderStatus = Literal["NEW", "CONFIRMED", "PREPARING", "READY", "COMPLETED", "CANCELLED"]


class CreateOrderItemRequest(BaseModel):
    productId: str
    quantity: int = Field(ge=1, le=20)
    optionIds: list[str] = []


class CreateOrderRequest(BaseModel):
    storeId: str
    customerName: str = Field(min_length=1, max_length=120)
    customerPhone: str = Field(min_length=3, max_length=30)
    pickupType: PickupType = "ASAP"
    pickupTime: str | None = None
    notes: str | None = Field(default=None, max_length=500)
    items: list[CreateOrderItemRequest] = Field(min_length=1)

    @field_validator("pickupTime")
    @classmethod
    def scheduled_requires_time(cls, value, info):
        pickup_type = info.data.get("pickupType")
        if pickup_type == "SCHEDULED" and not value:
            raise ValueError("pickupTime is required when pickupType is SCHEDULED.")
        return value


class OrderItemCustomization(BaseModel):
    id: str
    label: str
    priceDelta: Decimal


class OrderItemResponse(BaseModel):
    id: str
    productId: str
    productName: str
    unitPrice: Decimal
    quantity: int
    customizations: list[dict]
    total: Decimal

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: str
    orderNumber: str
    storeId: str
    customerName: str
    customerPhone: str
    status: OrderStatus
    pickupType: PickupType
    pickupTime: str | None = None
    notes: str | None = None
    subtotal: Decimal
    total: Decimal
    createdAt: str
    items: list[OrderItemResponse] = []

    class Config:
        from_attributes = True


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus
