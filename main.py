from fastapi import FastAPI, Depends, HTTPException, Header, Query, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from jose import jwt, JWTError
from uuid import uuid4, UUID
from datetime import date, datetime  
import os


import auth
import crud
import database
import models
import schema
import utils



from database import Base, engine, get_db
from models import User, Role, EmployeeDB,LocationLog
from schema import (
    UserCreate, UserOut, TokenResponse, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest,LocationOut,LocationCreate,
    EmployeeCreate, EmployeeResponse
)
from auth import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token, create_reset_token,
    get_current_user, require_roles, blacklisted_refresh_tokens,
    SECRET_KEY, ALGORITHM, authorize, get_user_roles
)



Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth System with Roles")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password)
    )
    role = db.query(Role).filter(Role.name == user.role.lower()).first()
    if not role:
        role = Role(name=user.role.lower())
        db.add(role)
        db.commit()
        db.refresh(role)
    new_user.roles.append(role)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserOut(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        roles=[r.name for r in new_user.roles]
    )


@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token({"sub": user.username, "roles": [r.name for r in user.roles]})
    refresh_token = create_refresh_token({"sub": user.username})

    return {"access_token": access_token, "refresh_token": refresh_token, "expires_in": 300}


@app.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshRequest):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        if request.refresh_token in blacklisted_refresh_tokens:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    new_access_token = create_access_token({"sub": username, "roles": payload.get("roles", [])})
    return {"access_token": new_access_token, "refresh_token": request.refresh_token, "expires_in": 300}


@app.post("/logout")
def logout(request: RefreshRequest):
    blacklisted_refresh_tokens.add(request.refresh_token)
    return {"msg": "Successfully logged out"}


@app.get("/profile", response_model=UserOut)
def profile(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=[r.name for r in user.roles]
    )


@app.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    reset_token = create_reset_token({"sub": user.username})
    return {"msg": "Password reset token generated", "reset_token": reset_token}


@app.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(request.token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    return {"msg": "Password reset successful"}



@app.get("/admin-only")
def admin_only(user: User = Depends(require_roles(["admin"]))):
    return {"msg": f"Welcome Admin {user.username}!"}


@app.get("/manager")
def manager_or_admin(user: User = Depends(require_roles(["manager", "admin"]))):
    return {"msg": f"Hello {user.username}, you have manager/admin access"}


@app.get("/hr")
def hr_route(user: User = Depends(require_roles(["hr", "manager", "admin"]))):
    return {"msg": f"Hello {user.username}, HR access granted"}


@app.get("/employee")
def employee_route(user: User = Depends(require_roles(["employee"]))):
    return {"msg": f"Employee dashboard for {user.username}"}


@app.get("/")
def root():
    return {"msg": "User Auth API running"}



@app.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    req: EmployeeCreate,
    username: str = Header(...),
    db: Session = Depends(get_db)
):
    authorize(username, "employee", "create", db)

    creator = db.query(User).filter(User.username == username).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Header username not found")

    target_user = db.query(User).filter(User.id == req.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="user_id does not exist in Users table")

    exists = db.query(EmployeeDB).filter(
        (EmployeeDB.user_id == req.user_id) | (EmployeeDB.email == req.email)
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="User with this ID or Email already exists")

    
    employee_code_obj = str(uuid4())
    created_at = req.created_at or date.today()

    db_employee = EmployeeDB(
        user_id=req.user_id,
        employee_code=employee_code_obj,
        first_name=req.first_name,
        last_name=req.last_name,
        email=req.email,
        phone_number=req.phone_number,
        department_id=req.department_id,
        role=req.role,
        date_of_joining=req.date_of_joining,
        salary=req.salary,
        is_active=req.is_active,
        created_at=created_at
    )
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)

    try:
        db.add(models.AuditLog(action="EMPLOYEE_CREATED", user_id=creator.id))
        db.commit()
    except Exception:
        db.rollback()

    return EmployeeResponse(
        user_id=db_employee.user_id,
        employee_code=db_employee.employee_code,  
        first_name=db_employee.first_name,
        last_name=db_employee.last_name,
        email=db_employee.email,
        phone_number=db_employee.phone_number,
        department_id=db_employee.department_id,
        role=db_employee.role,
        date_of_joining=db_employee.date_of_joining,
        salary=db_employee.salary,
        is_active=db_employee.is_active,
        created_at=db_employee.created_at
    )


@app.get("/employees", response_model=List[EmployeeResponse])
def list_employees(
    username: str = Header(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    authorize(username, "employee", "view", db)

    query = db.query(EmployeeDB)
    if is_active is not None:
        query = query.filter(EmployeeDB.is_active == is_active)
    employees = query.offset(skip).limit(limit).all()
    return employees


@app.get("/employees/{user_id}", response_model=EmployeeResponse)
def get_employee_detail(user_id: int, username: str = Header(...), db: Session = Depends(get_db)):
    employee = db.query(EmployeeDB).filter(EmployeeDB.user_id == user_id).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    roles = get_user_roles(username, db)
    if "admin" not in roles:
        current = db.query(User).filter(User.username == username).first()
        if not current or current.id != employee.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    authorize(username, "employee", "view", db)
    return employee



@app.post("/attendance/checkin", response_model=schema.AttendanceOut, status_code=status.HTTP_201_CREATED)
def checkin(data: schema.AttendanceCreate, db: Session = Depends(get_db)):
    return crud.check_in(db, data.user_id)


@app.post("/attendance/checkout", response_model=schema.AttendanceOut)
def checkout(data: schema.AttendanceCreate, db: Session = Depends(get_db)):
    return crud.check_out(db, data.user_id)


@app.post("/attendance/manual", response_model=schema.AttendanceOut)
def manual_update(
    user_id: int,
    day: date,
    check_in: datetime,
    check_out: datetime,
    db: Session = Depends(get_db)
):
    return crud.manual_update(db, user_id, day, check_in, check_out)


@app.get("/attendance/report", response_model=Union[List[schema.AttendanceOut], schema.HolidayCreate])
def report(day: date = Query(default=date.today()), db: Session = Depends(get_db)):
    return crud.daily_report(db, day)


@app.post("/attendance/holidays", response_model=schema.HolidayCreate, status_code=status.HTTP_201_CREATED)
def add_holiday(data: schema.HolidayCreate, db: Session = Depends(get_db)):
    return crud.create_holiday(db, data)


@app.post("/attendance/holidays/delete", response_model=schema.HolidayDelete)
def erase_holiday(data: schema.HolidayDelete, db: Session = Depends(get_db)):
    return crud.delete_holiday(db, data)


@app.get("/attendance/summary/{user_id}/{year}/{month}", response_model=schema.AttendanceSummary)
def attendance_summary(user_id: int, year: int, month: int, db: Session = Depends(get_db)):
    return crud.get_monthly_summary(db, user_id, year, month)



@app.post("/payroll/generate", response_model=schema.PayrollOut, status_code=status.HTTP_201_CREATED)
def create_payroll(
    payload: schema.PayrollCreate,
    current_user: models.User = Depends(auth.require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    This endpoint creates a new payroll record.
    It requires the user to have the 'admin' role.
    """
    emp = db.query(models.EmployeeDB).filter(models.EmployeeDB.id == payload.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing = crud.get_payroll_for_employee(db, payload.employee_id, payload.period_start, payload.period_end)
    if existing:
        raise HTTPException(status_code=409, detail="Payroll already exists for this period")

    payroll_record = crud.create_payroll(db, payload)
    return payroll_record



@app.get("/payroll/{employee_id}/payslip")
def get_payslip(employee_id: int, period_start: date = None, period_end: date = None, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    emp = db.query(models.EmployeeDB).filter(models.EmployeeDB.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    user_roles = [r.name for r in current_user.roles]

    if "admin" not in user_roles:
        
        current_emp = db.query(models.EmployeeDB).filter(models.EmployeeDB.user_id == current_user.id).first()
        if not current_emp or current_emp.id != employee_id:
            raise HTTPException(status_code=403, detail="Not allowed to view others' payslips")

    if period_start and period_end:
        row = crud.get_payroll_for_employee(db, employee_id, period_start, period_end)
    else:
        row = crud.get_latest_payroll(db, employee_id)

    if not row:
        raise HTTPException(status_code=404, detail="Payroll not found")

    pdf_path = utils.save_payslip_pdf(emp, row)
    filename = os.path.basename(pdf_path)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return FileResponse(path=pdf_path, media_type="application/pdf", headers=headers)


@app.get("/payroll/summary")
def payroll_summary(period_start: date, period_end: date, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    results = crud.list_payrolls_for_period(db, period_start, period_end)
    user_roles = [r.name for r in current_user.roles]

    if "admin" not in user_roles:
        current_emp = db.query(models.EmployeeDB).filter(models.EmployeeDB.user_id == current_user.id).first()
        if current_emp:
            results = [r for r in results if r.employee_id == current_emp.id]
        else:
            results = []

    return [{
        "id": r.id,
        "employee_id": r.employee_id,
        "period_start": r.period_start,
        "period_end": r.period_end,
        "basic_salary": r.basic_salary,
        "allowances": r.allowances,
        "total_deductions": r.total_deductions,
        "absent_days": r.absent_days,
        "net_salary": r.net_salary,
        "generated_at": r.generated_at
    } for r in results]



@app.post("/location/employee/{employee_id}", response_model=LocationOut)
def save_location(employee_id: int, location: LocationCreate, db: Session = Depends(get_db)):
    
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    db_location = LocationLog(
        employee_id=employee_id,
        latitude=location.latitude,
        longitude=location.longitude,
        accuracy=location.accuracy,
        source=location.source
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


@app.get("/location/history/{employee_id}", response_model=List[LocationOut])
def get_location_history(employee_id: int, start: Optional[datetime] = Query(None), end: Optional[datetime] = Query(None), db: Session = Depends(get_db)):
    query = db.query(LocationLog).filter(LocationLog.employee_id == employee_id)
    if start:
        query = query.filter(LocationLog.timestamp >= start)
    if end:
        query = query.filter(LocationLog.timestamp <= end)
    return query.order_by(LocationLog.timestamp.desc()).all()


@app.get("/location/all", response_model=List[LocationOut])
def get_all_locations(db: Session = Depends(get_db)):
    return db.query(LocationLog).all()


@app.get("/location/latest/{employee_id}", response_model=LocationOut)
def get_latest_location(employee_id: int, db: Session = Depends(get_db)):
    location = (
        db.query(LocationLog)
        .filter(LocationLog.employee_id == employee_id)
        .order_by(LocationLog.timestamp.desc())
        .first()
    )
    if not location:
        raise HTTPException(status_code=404, detail="No location found for this employee")
    return location

