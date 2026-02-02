from pydantic import BaseModel
from decimal import Decimal
from uuid import UUID


class CompanyCreate(BaseModel):
    name: str


class CompanyRead(CompanyCreate):
    id: UUID
