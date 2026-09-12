from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None


class UserOut(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None
    role: UserRole
    department_id: int | None
    zone_id: int | None

    model_config = {"from_attributes": True}


class WardOut(BaseModel):
    id: int
    ward_name: str
    zone_id: int
    population: int | None
    sc_population: int | None
    st_population: int | None
    has_boundary: bool

    model_config = {"from_attributes": True}


class ZoneOut(BaseModel):
    id: int
    zone_name: str
    jurisdiction_description: str | None

    model_config = {"from_attributes": True}


class DepartmentOut(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}
