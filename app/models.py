from __future__ import annotations
import uuid
import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Boolean, Integer, Date, DateTime, Numeric, Float
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


# -----------------
# CORE ENTITIES
# -----------------

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    company_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Company defaults
    default_gas_price: Mapped[float] = mapped_column(Numeric(10, 3), default=3.0)
    default_labor_per_hour: Mapped[float] = mapped_column(Numeric(10, 2), default=20)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"), index=True)

    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None]
    phone: Mapped[str | None]


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = mapped_column(ForeignKey("customers.id"), index=True)
    customer = relationship("Customer", backref="locations")
    address: Mapped[str]
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

    avg_service_minutes: Mapped[int] = mapped_column(Integer, default=45)


class ServicePlan(Base):
    __tablename__ = "service_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"), index=True)
    location_id = mapped_column(ForeignKey("locations.id"), index=True)
    location = relationship("Location", backref="service_plans")
    frequency: Mapped[str]  # weekly, biweekly, etc
    revenue_per_visit: Mapped[float]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    modified_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    company = relationship("Company", backref="service_plans")


# -----------------
# OPERATIONS
# -----------------

class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(255))
    mpg: Mapped[float]
    maintenance_cost_per_mile: Mapped[float]

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(255))  
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    labor_cost_per_hour: Mapped[float] = mapped_column(Numeric(10, 2), default=20.0)

    # Relationships
    companies = relationship("Company", backref="employees")


class Crew(Base):
    __tablename__ = "crews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    labor_cost_per_hour: Mapped[float] = mapped_column(Numeric(10, 2), default=20.0)

    # Relationships
    company = relationship("Company", backref="crews")
    employees = relationship("Employee", secondary="crew_employees", backref="crews_assigned")

class CrewEmployee(Base):
    __tablename__ = "crew_employees"
    crew_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crews.id"), primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    clocked_in: Mapped[bool] = mapped_column(Boolean, default=False)
    clocked_out: Mapped[bool] = mapped_column(Boolean, default=True)
    clock_in_time: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    clock_out_time: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    employee = relationship("Employee", backref="crew_associations")
    crew = relationship("Crew", backref="employee_associations")




# -----------------
# ROUTING
# -----------------
class Route(Base):
    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = mapped_column(ForeignKey("route_plans.id"))

    vehicle_id = mapped_column(ForeignKey("vehicles.id"))
    crew_id = mapped_column(ForeignKey("crews.id"))

    total_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_profit: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_miles: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_drive_minutes: Mapped[int] = mapped_column(Integer, default=0)
    total_service_minutes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    day: Mapped[int] = mapped_column(Integer)  # Day number within the plan (0-based)
    name: Mapped[str] = mapped_column(String(255))
    depot_id = mapped_column(ForeignKey("depots.id"))
    gas_price_per_gallon: Mapped[Float | None] = mapped_column(Numeric(10, 3), nullable=True)
    labor_cost_per_hour: Mapped[Float | None] = mapped_column(Numeric(10, 2), nullable=True)
    mpg: Mapped[Float | None] = mapped_column(Numeric(10, 2), nullable=True)
    maintenance_cost_per_mile: Mapped[Float | None] = mapped_column(Numeric(10, 2), nullable=True)


class RoutePlan(Base):
    __tablename__ = "route_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))

    start_date: Mapped[datetime.date]
    days: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default="pending")


class RouteDay(Base):
    __tablename__ = "route_days"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = mapped_column(ForeignKey("route_plans.id"))
    date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)
    vehicle_id = mapped_column(ForeignKey("vehicles.id"))
    crew_id = mapped_column(ForeignKey("crews.id"))
    total_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    total_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    total_profit: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_day_id = mapped_column(ForeignKey("route_days.id"))
    location_id = mapped_column(ForeignKey("locations.id"))
    route_id = mapped_column(ForeignKey("routes.id"), nullable=True)
    order: Mapped[int]
    revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    segment_miles: Mapped[float] = mapped_column(Numeric(12, 3), default=0.0)
    segment_drive_minutes: Mapped[int] = mapped_column(Integer, default=0)
    route_stop_time_started: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    route_stop_time_ended: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    total_route_stop_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    location = relationship("Location", backref="route_stops")
    route = relationship("Route", backref="stops")

class RouteStopServiceRecord(Base):
    __tablename__ = "route_stop_service_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_stop_id = mapped_column(ForeignKey("route_stops.id"))
    location_id = mapped_column(ForeignKey("locations.id"))
    employee_id = mapped_column(ForeignKey("employees.id"))
    crew_id = mapped_column(ForeignKey("crews.id"))
    date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)
    service_start_time: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    service_end_time: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    service_minutes: Mapped[int] = mapped_column(Integer, default=0)
    before_photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    after_photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)
    description: Mapped[str] = mapped_column(String(255))
    expense_type: Mapped[str] = mapped_column(String(50))  
    type: Mapped[str] # e.g., 'fuel', 'maintenance', etc.
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)

class Income(Base):
    __tablename__ = "incomes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)
    description: Mapped[str] = mapped_column(String(255))
    income_type: Mapped[str] = mapped_column(String(50))  
    type: Mapped[str]  # e.g., 'service', 'product_sale', etc.
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)


class Depot(Base):
    __tablename__ = "depots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    lng: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    modified_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))

    # relationships
    company = relationship("Company", backref="depots")
    routes = relationship("Route", backref="depot")


class RevenueRecord(Base):
    __tablename__ = "revenue_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)
    source: Mapped[str] = mapped_column(String(50))  # e.g., 'service', 'product_sale', 'Landscaping', etc..
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)

    # relationships
    company = relationship("Company", backref="revenue_records")


class ExpenseRecord(Base):
    __tablename__ = "cost_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)
    source: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)

    # relationships
    company = relationship("Company", backref="cost_records")
    
