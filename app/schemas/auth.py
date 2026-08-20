from pydantic import BaseModel


class MeResponse(BaseModel):
    id: str
    clerkUserId: str
    name: str | None = None
    phone: str | None = None
    role: str

    class Config:
        from_attributes = True


class UpdateMeRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
