from decimal import Decimal

from pydantic import BaseModel, Field


class ProductOptionResponse(BaseModel):
    id: str
    name: str
    price: Decimal
    isAvailable: bool
    sortOrder: int

    class Config:
        from_attributes = True


class ProductOptionGroupResponse(BaseModel):
    id: str
    name: str
    required: bool
    multiSelect: bool
    minSelections: int
    maxSelections: int
    sortOrder: int
    options: list[ProductOptionResponse] = []

    class Config:
        from_attributes = True


class CategorySummary(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class ProductListItem(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    price: Decimal
    imageUrl: str | None = None
    isAvailable: bool
    category: CategorySummary

    class Config:
        from_attributes = True


class ProductDetailResponse(ProductListItem):
    optionGroups: list[ProductOptionGroupResponse] = []


class CreateProductRequest(BaseModel):
    categoryId: str
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120)
    description: str | None = None
    price: Decimal = Field(gt=0)
    imageUrl: str | None = None
    isAvailable: bool = True
    sortOrder: int = 0


class UpdateProductRequest(BaseModel):
    categoryId: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    imageUrl: str | None = None
    isAvailable: bool | None = None
    sortOrder: int | None = None


class CreateOptionGroupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    required: bool = False
    multiSelect: bool = False
    minSelections: int = Field(default=0, ge=0)
    maxSelections: int = Field(default=1, ge=1)
    sortOrder: int = 0


class UpdateOptionGroupRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    required: bool | None = None
    multiSelect: bool | None = None
    minSelections: int | None = Field(default=None, ge=0)
    maxSelections: int | None = Field(default=None, ge=1)
    sortOrder: int | None = None


class CreateOptionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    price: Decimal = Field(default=Decimal("0.00"), ge=0)
    isAvailable: bool = True
    sortOrder: int = 0


class UpdateOptionRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    price: Decimal | None = Field(default=None, ge=0)
    isAvailable: bool | None = None
    sortOrder: int | None = None
