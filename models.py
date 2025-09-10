from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Date, Boolean, Numeric, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, date


user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("role_id", Integer, ForeignKey("roles.id"))
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

  
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    attendance = relationship("Attendance", back_populates="user")
    employee = relationship("EmployeeDB", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    users = relationship("User", secondary=user_roles, back_populates="roles")


class EmployeeDB(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    employee_code = Column(String, unique=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    email = Column(String, unique=True, nullable=False)
    phone_number = Column(String)
    department_id = Column(Integer)
    role = Column(String)
    date_of_joining = Column(Date)
    salary = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

   
    user = relationship("User", back_populates="employee")
    payrolls = relationship("Payroll", back_populates="employee")
    locations = relationship("LocationLog", back_populates="employee")  

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    date = Column(Date, default=date.today)
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="attendance")


class Holiday(Base):
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False)
    name = Column(String, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="audit_logs")


class Payroll(Base):
    __tablename__ = "payrolls"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    basic_salary = Column(Numeric(10, 2), nullable=False)
    allowances = Column(Numeric(10, 2), default=0.0)
    deductions = Column(Numeric(10, 2), default=0.0)
    absent_deduction = Column(Numeric(10, 2), default=0.0)
    total_deductions = Column(Numeric(10, 2), default=0.0)
    absent_days = Column(Integer, default=0)
    net_salary = Column(Numeric(10, 2), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    employee = relationship("EmployeeDB", back_populates="payrolls")


class LocationLog(Base):
    __tablename__ = "location_logs"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    source = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    employee = relationship("EmployeeDB", back_populates="locations")

