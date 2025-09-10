from sqlalchemy.orm import Session
from sqlalchemy import extract
from datetime import date, datetime
from fastapi import HTTPException, status
from calendar import monthrange 
import models, schema



# Check-In
def check_in(db: Session, user_id: int):
    today = date.today()
    record = db.query(models.Attendance).filter(
        models.Attendance.user_id == user_id, 
        models.Attendance.date == today
    ).first()
    
    if record:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already checked in today."
        )

    new_att = models.Attendance(user_id=user_id, date=today, check_in=datetime.now())
    db.add(new_att)
    db.commit()
    db.refresh(new_att)
    return new_att


# Check-Out
def check_out(db: Session, user_id: int):
    today = date.today()
    record = db.query(models.Attendance).filter(
        models.Attendance.user_id == user_id, 
        models.Attendance.date == today
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No check-in record found for today."
        )

    if record.check_out:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already checked out today."
        )

    record.check_out = datetime.now()
    db.commit()
    db.refresh(record)
    return record


# Manual Correction (Admin)
def manual_update(db: Session, user_id: int, day: date, check_in_dt: datetime, check_out_dt: datetime):
    existing_record = db.query(models.Attendance).filter(
        models.Attendance.user_id == user_id,
        models.Attendance.date == day
    ).first()

    if existing_record:
        existing_record.check_in = check_in_dt
        existing_record.check_out = check_out_dt
        db.commit()
        db.refresh(existing_record)
        return existing_record
    else:
        new_record = models.Attendance(
            user_id=user_id, 
            date=day, 
            check_in=check_in_dt, 
            check_out=check_out_dt
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record


# Daily Report
def daily_report(db: Session, day: date):
    holiday = db.query(models.Holiday).filter(models.Holiday.date == day).first()
    if holiday:
        return schema.HolidayCreate(date=holiday.date, name=holiday.name)
    
    rows = db.query(models.Attendance).filter(models.Attendance.date == day).all()
    return rows



def create_holiday(db: Session, holiday: schema.HolidayCreate):
    db_holiday = db.query(models.Holiday).filter(models.Holiday.date == holiday.date).first()
    if db_holiday:
        raise HTTPException(status_code=409, detail="Holiday for this date already exists.")
    
    db_holiday = models.Holiday(date=holiday.date, name=holiday.name)
    db.add(db_holiday)
    db.commit()
    db.refresh(db_holiday)
    return db_holiday


def delete_holiday(db: Session, holiday: schema.HolidayDelete):
    db_holiday = db.query(models.Holiday).filter(
        models.Holiday.date == holiday.date
    ).first()

    if not db_holiday:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Holiday not found"
        )

    db.delete(db_holiday)
    db.commit()
    return db_holiday



def get_monthly_summary(db: Session, user_id: int, year: int, month: int):
    present_dates = db.query(models.Attendance.date).filter(
        models.Attendance.user_id == user_id,
        extract('year', models.Attendance.date) == year,
        extract('month', models.Attendance.date) == month
    ).all()

    holiday_dates = db.query(models.Holiday.date).filter(
        extract('year', models.Holiday.date) == year,
        extract('month', models.Holiday.date) == month
    ).all()
    
    present_dates_set = {d[0] for d in present_dates}
    holiday_dates_set = {h[0] for h in holiday_dates}
    
    _, total_days = monthrange(year, month)
    
    present_days_count = len(present_dates_set)
    holidays_count = len(holiday_dates_set)

    total_days_in_month_set = {date(year, month, day) for day in range(1, total_days + 1)}
    
    absent_days_count = len(total_days_in_month_set - present_dates_set - holiday_dates_set)
    
    return schema.AttendanceSummary(
        total_days=total_days,
        present_days=present_days_count,
        absent_days=absent_days_count,
        holidays=holidays_count
    )


def create_payroll(db: Session, payload: schema.PayrollCreate):
    allowances_value = payload.basic_salary * (payload.allowances_percent / 100)
    deductions_value = payload.basic_salary * (payload.deductions_percent / 100)
    
   
    daily_salary = payload.basic_salary / 30
    absent_deduction = payload.absent_days * daily_salary
    
    total_deductions = deductions_value + absent_deduction
    net_salary = payload.basic_salary + allowances_value - total_deductions

    new_payroll = models.Payroll(
        employee_id=payload.employee_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        basic_salary=payload.basic_salary,
        allowances=allowances_value, 
        deductions=deductions_value,  
        absent_deduction=absent_deduction, 
        total_deductions=total_deductions,
        absent_days=payload.absent_days,
        net_salary=net_salary,
        generated_at=datetime.utcnow()
    )
    
    db.add(new_payroll)
    db.commit()
    db.refresh(new_payroll)
    
    return new_payroll


def get_payroll_for_employee(db: Session, employee_id: int, start: date, end: date):
    return db.query(models.Payroll).filter(
        models.Payroll.employee_id == employee_id,
        models.Payroll.period_start == start,
        models.Payroll.period_end == end
    ).first()

def get_latest_payroll(db: Session, employee_id: int):
    return db.query(models.Payroll).filter(
        models.Payroll.employee_id == employee_id
    ).order_by(models.Payroll.generated_at.desc()).first()
    
def list_payrolls_for_period(db: Session, start: date, end: date):
    return db.query(models.Payroll).filter(
        models.Payroll.period_start >= start,
        models.Payroll.period_end <= end
    ).all()