from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id: str
    storeId: str
    name: str
    slug: str
    description: str | None = None
    sortOrder: int
    isActive: bool

    class Config:
        from_attributes = True


class CreateCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(min_length=1, max_length=80)
    description: str | None = None
    sortOrder: int = 0
    isActive: bool = True


class UpdateCategoryRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    slug: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    sortOrder: int | None = None
    isActive: bool | None = None
