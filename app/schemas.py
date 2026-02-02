from pydantic import BaseModel, Field, validate_email, validate_call, ValidateAs
from typing import List, Optional, Union, Any, Dict, Type
from datetime import datetime as dt
from enum import Enum, auto, unique, IntEnum, Flag, IntFlag
from uuid import uuid4, UUID


class CompanyCreate(BaseModel):
    name: str
    company_email: str = unique(Field(..., max_length=255))
    validate_email('company_email')
    company_phone: str | None = unique(Field(..., max_length=20))
    default_gas_price: float = Field(3.0, gt=0)
    default_labor_per_hour: float = Field(20.0, gt=0)
    default_maintenance_cost_per_mile: float = Field(0.0, ge=0)
    class Config:
        orm_mode = True

class CompanyRead(CompanyCreate):
    id: UUID= Field(default_factory=uuid4)
    default_gas_price: float = Field(3.0, gt=0)
    default_labor_per_hour: float = Field(20.0, gt=0)
    default_maintenance_cost_per_mile: float = Field(0.0, ge=0)
    created_at: dt = Field(default_factory=dt.now)
    updated_at: dt = Field(default_factory=dt.now)

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    company_email: Optional[str] = Field(None, max_length=255)
    validate_email('company_email')
    company_phone: Optional[str] = Field(None, max_length=20)
    default_gas_price: Optional[float] = Field(None, gt=0)
    default_labor_per_hour: Optional[float] = Field(None, gt=0)
    default_maintenance_cost_per_mile: Optional[float] = Field(None, ge=0)

class CompanyList(BaseModel):
    companies: List[CompanyRead]

class CompanyDelete(BaseModel):
    id: UUID = Field(...)
    class Config:
        orm_mode = True

class CompanyStats(BaseModel):
    id: UUID
    total_locations: int
    total_vehicles: int
    total_routes: int
    total_revenue: float
    total_expenses: float
    net_profit: float
    average_route_profit: float
    busiest_day: Optional[dt] = None
    least_busy_day: Optional[dt] = None

class CompanySettingsUpdate(BaseModel):
    default_gas_price: Optional[float] = Field(None, gt=0)
    default_labor_per_hour: Optional[float] = Field(None, gt=0)
    default_maintenance_cost_per_mile: Optional[float] = Field(None, ge=0)
class CompanySettingsRead(BaseModel):
    default_gas_price: float
    default_labor_per_hour: float
    default_maintenance_cost_per_mile: float

class CompanyRevenueReport(BaseModel):
    start_date: dt
    end_date: dt
    total_revenue: float
    revenue_by_source: Dict[str, float]  # e.g., {'service': 1000.0, 'product_sale': 500.0}
class CompanyExpenseReport(BaseModel):
    start_date: dt
    end_date: dt
    total_expenses: float
    expenses_by_type: Dict[str, float]  # e.g., {'fuel': 300.0, 'maintenance': 200.0}
class CompanyProfitLossReport(BaseModel):
    start_date: dt
    end_date: dt
    total_revenue: float
    total_expenses: float
    net_profit: float
class CompanyRevenueByMonth(BaseModel):
    month: str  # e.g., '2024-01'
    total_revenue: float
class CompanyExpenseByMonth(BaseModel):
    month: str  # e.g., '2024-01'
    total_expenses: float

class CompanyProfitByMonth(BaseModel):
    month: str  # e.g., '2024-01'
    net_profit: float

class CompanyVehicleStats(BaseModel):
    vehicle_id: UUID
    total_routes: int
    total_miles: float
    total_revenue: float
    total_expenses: float
    net_profit: float

class CompanyCrewStats(BaseModel):
    crew_id: UUID
    total_routes: int
    total_miles: float
    total_revenue: float
    total_expenses: float
    net_profit: float

class CompanyLocationStats(BaseModel):
    location_id: UUID
    total_visits: int
    total_revenue: float
    total_expenses: float
    net_profit: float

class CompanyDepotStats(BaseModel):
    depot_id: UUID
    total_routes: int
    total_miles: float
    total_revenue: float
    total_expenses: float
    net_profit: float

    id: UUID = Field(default_factory=uuid4)
    name: str
    company_email: str | None = None
    company_phone: str | None = None
    default_gas_price: float = Field(3.0, gt=0)
    default_labor_per_hour: float = Field(20.0, gt=0)
    default_maintenance_cost_per_mile: float = Field(0.0, ge=0)
    created_at: dt = Field(default_factory=dt.utcnow)
    updated_at: dt = Field(default_factory=dt.utcnow)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

