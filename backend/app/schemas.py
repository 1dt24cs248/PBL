from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str
    category: str | None = None
    department: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    number: str
    floor: int
    capacity: int
    room_type: str
    facilities: str
    status: str
    version: int
    provenance: str


class RoomCreate(BaseModel):
    building_id: int
    number: str = Field(min_length=1, max_length=20)
    floor: int = Field(ge=0, le=30)
    capacity: int = Field(gt=0, le=1000)
    room_type: str = "classroom"
    facilities: str = ""


class RoomStatusUpdate(BaseModel):
    status: str
