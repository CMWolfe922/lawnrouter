from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_db
from ..auth import get_current_user
from ..models import Crew, Employee, CrewEmployee
from ..schemas import (
    CrewCreate, CrewRead, CrewUpdate, CrewEmployeeAdd,
    EmployeeCreate, EmployeeRead, EmployeeUpdate,
)

router = APIRouter(tags=["Crews & Employees"])


# -----------------
# EMPLOYEE ENDPOINTS
# -----------------

@router.post("/employees", response_model=EmployeeRead)
async def create_employee(
    data: EmployeeCreate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new employee."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    employee = Employee(
        company_id=company_id,
        name=data.name,
        labor_cost_per_hour=data.labor_cost_per_hour,
    )
    session.add(employee)
    await session.commit()
    await session.refresh(employee)
    return employee


@router.get("/employees", response_model=list[EmployeeRead])
async def list_employees(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all employees for the company."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Employee).where(Employee.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a specific employee."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == company_id,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.patch("/employees/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update an employee."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == company_id,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    await session.commit()
    await session.refresh(employee)
    return employee


@router.delete("/employees/{employee_id}")
async def delete_employee(
    employee_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete an employee (sets inactive)."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == company_id,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.is_active = False
    await session.commit()
    return {"detail": "Employee deactivated"}


# -----------------
# CREW ENDPOINTS
# -----------------

@router.post("/crews", response_model=CrewRead)
async def create_crew(
    data: CrewCreate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new crew, optionally with initial employees."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    crew = Crew(
        company_id=company_id,
        name=data.name,
        labor_cost_per_hour=data.labor_cost_per_hour,
    )
    session.add(crew)
    await session.flush()

    # Add employees to crew if provided
    for emp_id in data.employee_ids:
        # Verify employee belongs to company
        result = await session.execute(
            select(Employee).where(
                Employee.id == emp_id,
                Employee.company_id == company_id,
            )
        )
        employee = result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=404, detail=f"Employee {emp_id} not found")

        crew_employee = CrewEmployee(crew_id=crew.id, employee_id=emp_id)
        session.add(crew_employee)

    await session.commit()
    await session.refresh(crew)
    return crew


@router.get("/crews", response_model=list[CrewRead])
async def list_crews(
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all crews for the company."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Crew).where(Crew.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/crews/{crew_id}", response_model=CrewRead)
async def get_crew(
    crew_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a specific crew."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Crew).where(
            Crew.id == crew_id,
            Crew.company_id == company_id,
        )
    )
    crew = result.scalar_one_or_none()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")
    return crew


@router.patch("/crews/{crew_id}", response_model=CrewRead)
async def update_crew(
    crew_id: UUID,
    data: CrewUpdate,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update a crew."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Crew).where(
            Crew.id == crew_id,
            Crew.company_id == company_id,
        )
    )
    crew = result.scalar_one_or_none()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(crew, field, value)

    await session.commit()
    await session.refresh(crew)
    return crew


@router.delete("/crews/{crew_id}")
async def delete_crew(
    crew_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete a crew (sets inactive)."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    result = await session.execute(
        select(Crew).where(
            Crew.id == crew_id,
            Crew.company_id == company_id,
        )
    )
    crew = result.scalar_one_or_none()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")

    crew.is_active = False
    await session.commit()
    return {"detail": "Crew deactivated"}


# -----------------
# CREW EMPLOYEE MANAGEMENT
# -----------------

@router.get("/crews/{crew_id}/employees", response_model=list[EmployeeRead])
async def list_crew_employees(
    crew_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all employees in a crew."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Verify crew belongs to company
    result = await session.execute(
        select(Crew).where(
            Crew.id == crew_id,
            Crew.company_id == company_id,
        )
    )
    crew = result.scalar_one_or_none()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")

    # Get employees via join
    result = await session.execute(
        select(Employee)
        .join(CrewEmployee, CrewEmployee.employee_id == Employee.id)
        .where(CrewEmployee.crew_id == crew_id)
    )
    return result.scalars().all()


@router.post("/crews/{crew_id}/employees", response_model=EmployeeRead)
async def add_employee_to_crew(
    crew_id: UUID,
    data: CrewEmployeeAdd,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Add an employee to a crew."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Verify crew belongs to company
    result = await session.execute(
        select(Crew).where(
            Crew.id == crew_id,
            Crew.company_id == company_id,
        )
    )
    crew = result.scalar_one_or_none()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")

    # Verify employee belongs to company
    result = await session.execute(
        select(Employee).where(
            Employee.id == data.employee_id,
            Employee.company_id == company_id,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Check if already in crew
    result = await session.execute(
        select(CrewEmployee).where(
            CrewEmployee.crew_id == crew_id,
            CrewEmployee.employee_id == data.employee_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Employee already in crew")

    crew_employee = CrewEmployee(crew_id=crew_id, employee_id=data.employee_id)
    session.add(crew_employee)
    await session.commit()
    return employee


@router.delete("/crews/{crew_id}/employees/{employee_id}")
async def remove_employee_from_crew(
    crew_id: UUID,
    employee_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Remove an employee from a crew."""
    company_id = user.get("custom:company_id") or user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id not found in token")

    # Verify crew belongs to company
    result = await session.execute(
        select(Crew).where(
            Crew.id == crew_id,
            Crew.company_id == company_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Crew not found")

    # Find and delete the association
    result = await session.execute(
        select(CrewEmployee).where(
            CrewEmployee.crew_id == crew_id,
            CrewEmployee.employee_id == employee_id,
        )
    )
    crew_employee = result.scalar_one_or_none()
    if not crew_employee:
        raise HTTPException(status_code=404, detail="Employee not in crew")

    await session.delete(crew_employee)
    await session.commit()
    return {"detail": "Employee removed from crew"}
