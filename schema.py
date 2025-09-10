from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from uuid import UUID
from datetime import date,datetime
from enum import Enum

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[str] = "employee"

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    roles: List[str]

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class RoleEnum(str, Enum):
    admin = "admin"
    manager = "manager"
    hr = "hr"
    employee = "employee"

class EmployeeBase(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str = Field(pattern=r"^\d{10}$")
    department_id: int
    role: RoleEnum
    date_of_joining: date
    salary: int
    is_active: bool = True

class EmployeeCreate(EmployeeBase):
    employee_code: Optional[str] = None
    created_at: Optional[date] = None

class EmployeeResponse(EmployeeBase):
    employee_code: str
    created_at: date

    class Config:
        from_attributes = True


class AttendanceCreate(BaseModel):
    user_id: int

class AttendanceOut(BaseModel):
    user_id: int
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class HolidayCreate(BaseModel):
    date: date
    name: str

class HolidayDelete(BaseModel):
    date: date
    name: str

class AttendanceSummary(BaseModel):
    total_days: int
    present_days: int
    absent_days: int
    holidays: int

class PayrollCreate(BaseModel):
    employee_id: int
    period_start: date
    period_end: date
    basic_salary: float
    allowances_percent: Optional[float] = 20.0
    deductions_percent: Optional[float] = 10.0
    absent_days: Optional[int] = 0

class PayrollOut(BaseModel):
    id: int
    employee_id: int
    period_start: date
    period_end: date
    basic_salary: float
    allowances: float
    deductions: float
    absent_deduction: float
    total_deductions: float
    absent_days: int
    net_salary: float
    generated_at: datetime

    class Config:
        from_attributes = True

class PayrollResponse(BaseModel):
    id: int
    employee_id: int
    period_start: date
    period_end: date
    basic_salary: float
    allowances: float
    total_deductions: float
    absent_days: int
    net_salary: float
    generated_at: datetime
    
    class Config:
        from_attributes = True


class LocationCreate(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    source: str

class LocationOut(BaseModel):
    id: int
    latitude: float
    longitude: float
    accuracy: Optional[float]
    source: str
    timestamp: datetime

    class Config:
        from_attributes = True       
