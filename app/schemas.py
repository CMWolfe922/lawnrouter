from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime as dt
from uuid import uuid4, UUID


# -----------------
# CUSTOMER SCHEMAS
# -----------------

class CustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerRead(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True


# -----------------
# LOCATION (PROPERTY) SCHEMAS
# -----------------

class LocationCreate(BaseModel):
    customer_id: UUID
    address: str
    avg_service_minutes: int = 45


class LocationRead(BaseModel):
    id: UUID
    customer_id: UUID
    address: str
    lat: float
    lng: float
    is_active: bool
    avg_service_minutes: int
    created_at: dt

    class Config:
        from_attributes = True


class CompanyCreate(BaseModel):
    name: str
    company_email: str = Field(..., max_length=255)
    company_phone: str | None = Field(None, max_length=20)
    default_gas_price: float = Field(3.0, gt=0)
    default_labor_per_hour: float = Field(20.0, gt=0)
    default_maintenance_cost_per_mile: float = Field(0.0, ge=0)

    class Config:
        from_attributes = True

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
    company_phone: Optional[str] = Field(None, max_length=20)
    default_gas_price: Optional[float] = Field(None, gt=0)
    default_labor_per_hour: Optional[float] = Field(None, gt=0)
    default_maintenance_cost_per_mile: Optional[float] = Field(None, ge=0)

class CompanyList(BaseModel):
    companies: List[CompanyRead]

class CompanyDelete(BaseModel):
    id: UUID = Field(...)

    class Config:
        from_attributes = True

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


# -----------------
# VEHICLE SCHEMAS
# -----------------

class VehicleCreate(BaseModel):
    name: str
    mpg: float = Field(..., gt=0)
    maintenance_cost_per_mile: float = Field(0.0, ge=0)


class VehicleRead(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    mpg: float
    maintenance_cost_per_mile: float

    class Config:
        from_attributes = True


class VehicleUpdate(BaseModel):
    name: Optional[str] = None
    mpg: Optional[float] = Field(None, gt=0)
    maintenance_cost_per_mile: Optional[float] = Field(None, ge=0)


# -----------------
# EMPLOYEE SCHEMAS
# -----------------

class EmployeeCreate(BaseModel):
    name: str
    labor_cost_per_hour: float = Field(20.0, gt=0)


class EmployeeRead(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    is_active: bool
    labor_cost_per_hour: float

    class Config:
        from_attributes = True


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    labor_cost_per_hour: Optional[float] = Field(None, gt=0)


# -----------------
# CREW SCHEMAS
# -----------------

class CrewCreate(BaseModel):
    name: str
    labor_cost_per_hour: float = Field(20.0, gt=0)
    employee_ids: List[UUID] = []


class CrewRead(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    is_active: bool
    labor_cost_per_hour: float

    class Config:
        from_attributes = True


class CrewUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    labor_cost_per_hour: Optional[float] = Field(None, gt=0)


class CrewEmployeeAdd(BaseModel):
    employee_id: UUID


# -----------------
# DEPOT SCHEMAS
# -----------------

class DepotCreate(BaseModel):
    name: str
    address: str


class DepotRead(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    address: str
    lat: float
    lng: float
    is_active: bool
    created_at: dt

    class Config:
        from_attributes = True


class DepotUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


# -----------------
# SERVICE PLAN SCHEMAS
# -----------------

class ServicePlanCreate(BaseModel):
    location_id: UUID
    frequency: str  # weekly, biweekly, monthly
    revenue_per_visit: float = Field(..., gt=0)


class ServicePlanRead(BaseModel):
    id: UUID
    company_id: UUID
    location_id: UUID
    frequency: str
    revenue_per_visit: float
    is_active: bool
    created_at: dt

    class Config:
        from_attributes = True


class ServicePlanUpdate(BaseModel):
    frequency: Optional[str] = None
    revenue_per_visit: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None


# -----------------
# ROUTE PLAN SCHEMAS
# -----------------

class RoutePlanCreate(BaseModel):
    start_date: dt
    days: int = Field(..., gt=0)


class RoutePlanRead(BaseModel):
    id: UUID
    company_id: UUID
    start_date: dt
    days: int
    status: str

    class Config:
        from_attributes = True


class RoutePlanUpdate(BaseModel):
    start_date: Optional[dt] = None
    days: Optional[int] = Field(None, gt=0)
    status: Optional[str] = None


# -----------------
# ROUTE SCHEMAS
# -----------------

class RouteRead(BaseModel):
    id: UUID
    plan_id: UUID
    vehicle_id: UUID
    crew_id: UUID
    depot_id: UUID
    day: int
    name: str
    total_revenue: float
    total_cost: float
    total_profit: float
    total_miles: float
    total_drive_minutes: int
    total_service_minutes: int

    class Config:
        from_attributes = True


# -----------------
# ROUTE STOP SCHEMAS
# -----------------

class RouteStopRead(BaseModel):
    id: UUID
    route_id: Optional[UUID]
    location_id: UUID
    order: int
    revenue: float
    segment_miles: float
    segment_drive_minutes: int

    class Config:
        from_attributes = True

