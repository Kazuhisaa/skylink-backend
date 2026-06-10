from pydantic import BaseModel
from typing import Optional


class AirportBase(BaseModel):
    iata_code: str
    name: str
    city: str
    country: str
    timezone: str
    about: Optional[str] = None
    highlights: Optional[list[str]] = None
    best_time: Optional[str] = None
    image_url: Optional[str] = None


class AirportCreate(AirportBase):
    pass


class AirportUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    about: Optional[str] = None
    highlights: Optional[list[str]] = None
    best_time: Optional[str] = None
    image_url: Optional[str] = None


class AirportRead(AirportBase):
    id: int
    model_config = {"from_attributes": True}