from __future__ import annotations
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Boolean, Integer, Date, DateTime, Numeric
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

    default_gas_price: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=3.0)
    default_labor_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=20)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
    lat: Mapped[Decimal]
    lng: Mapped[Decimal]

    avg_service_minutes: Mapped[int] = mapped_column(Integer, default=45)


class ServicePlan(Base):
    __tablename__ = "service_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_id = mapped_column(ForeignKey("locations.id"), index=True)
    location = relationship("Location", backref="service_plans")
    frequency: Mapped[str]  # weekly, biweekly, etc
    revenue_per_visit: Mapped[Decimal]


# -----------------
# OPERATIONS
# -----------------

class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(255))
    mpg: Mapped[Decimal]
    maintenance_cost_per_mile: Mapped[Decimal]

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(255))  
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    labor_cost_per_hour: Mapped[Decimal]
    companies = relationship("Company", backref="employees")


class Crew(Base):
    __tablename__ = "crews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(255))  
    companies = relationship("Company", backref="crews")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    labor_cost_per_hour: Mapped[Decimal]
    company = relationship("Company", backref="crews")
    employee = relationship("Employee", secondary="crew_employees", backref="crews")
    

# -----------------
# ROUTING
# -----------------
class Route(Base):
    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = mapped_column(ForeignKey("route_plans.id"))

    vehicle_id = mapped_column(ForeignKey("vehicles.id"))
    crew_id = mapped_column(ForeignKey("crews.id"))

    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_miles: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_drive_minutes: Mapped[int] = mapped_column(Integer, default=0)
    total_service_minutes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    day: Mapped[int] = mapped_column(Integer)  # Day number within the plan (0-based)
    name: Mapped[str] = mapped_column(String(255))
    depot_id = mapped_column(ForeignKey("depots.id"))
    gas_price_per_gallon: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    labor_cost_per_hour: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    mpg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    maintenance_cost_per_mile: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)


class RoutePlan(Base):
    __tablename__ = "route_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))

    start_date: Mapped[Date]
    days: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default="pending")


class RouteDay(Base):
    __tablename__ = "route_days"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = mapped_column(ForeignKey("route_plans.id"))
    date: Mapped[Date]
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_day_id = mapped_column(ForeignKey("route_days.id"))
    location_id = mapped_column(ForeignKey("locations.id"))
    order: Mapped[int]
    revenue: Mapped[Decimal]


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    date: Mapped[Date]
    type: Mapped[str]
    amount: Mapped[Decimal]


class Depot(Base):
    __tablename__ = "depots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))

    address: Mapped[str]
    lat: Mapped[Decimal]
    lng: Mapped[Decimal]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    name: Mapped[str] = mapped_column(String(255))


class RevenueRecord(Base):
    __tablename__ = "revenue_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    date: Mapped[Date]
    source: Mapped[str]
    amount: Mapped[Decimal]

class CostRecord(Base):
    __tablename__ = "cost_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(ForeignKey("companies.id"))
    date: Mapped[Date]
    source: Mapped[str]
    amount: Mapped[Decimal]