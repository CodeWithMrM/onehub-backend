from pydantic import BaseModel, Field


class StoreResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    phone: str | None = None
    address: str | None = None
    isActive: bool

    class Config:
        from_attributes = True


class StoreDashboardResponse(BaseModel):
    newOrders: int
    preparingOrders: int
    readyOrders: int
    todayOrders: int
    todayRevenue: float


class CreateStoreRequest(BaseModel):
    # Reserved for future multi-store onboarding flows. Not exposed
    # via a route in this MVP, kept here so the shape is ready.
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120)
    description: str | None = None
    phone: str | None = None
    address: str | None = None
