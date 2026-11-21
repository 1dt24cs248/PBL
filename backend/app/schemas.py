from pydantic import AliasChoices, BaseModel, ConfigDict, Field


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
    real_label: str
    aliases: list[str] = Field(validation_alias=AliasChoices("alias_values", "aliases"))
    data_status: str
    capacity_effective: int


class RoomCreate(BaseModel):
    building_id: int
    number: str = Field(min_length=1, max_length=20)
    floor: int = Field(ge=0, le=30)
    capacity: int = Field(gt=0, le=1000)
    room_type: str = "classroom"
    facilities: str = ""


class RoomStatusUpdate(BaseModel):
    status: str


class TimetableSessionCreate(BaseModel):
    term_code: str
    section_code: str
    batch: str = "ALL"
    day: str
    periods: list[int]
    subject_code: str
    faculty_id: int | None = None
    room_id: str | None = None
    room_required: bool = True
    raw_label: str
    block_id: str | None = None


class TimetableSessionPatch(BaseModel):
    expected_version: int
    section_code: str | None = None
    batch: str | None = None
    day: str | None = None
    periods: list[int] | None = None
    subject_code: str | None = None
    faculty_id: int | None = None
    room_id: str | None = None
    room_required: bool | None = None
    raw_label: str | None = None
    block_id: str | None = None
