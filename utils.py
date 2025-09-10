from fastapi import HTTPException
import os,re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(ROOT, "outputs", "payslips")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_payslip_pdf(employee, payroll_row):
    emp_code = getattr(employee, "employee_code", f"EMP{employee.id:03d}")
    fname = f"payslip_{emp_code}_{payroll_row.period_start.isoformat()}_{payroll_row.period_end.isoformat()}.pdf"
    path = os.path.join(OUTPUT_DIR, fname)

    
    if os.path.exists(path):
        return path

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 60, "Company Name Pvt Ltd")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 80, "Address line 1, City - PIN")

    c.setFont("Helvetica-Bold", 12)
    full_name = f"{employee.first_name} {employee.last_name}"
    c.drawString(50, height - 120, f"Payslip for: {full_name} ({emp_code})")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 140, f"Period: {payroll_row.period_start.isoformat()} to {payroll_row.period_end.isoformat()}")

    start_y = height - 180
    lh = 18

    c.setFont("Helvetica", 11)
    c.drawString(50, start_y, "Basic Salary:")
    c.drawRightString(500, start_y, f"{payroll_row.basic_salary:,.2f}")

    c.drawString(50, start_y - lh, "Allowances:")
    c.drawRightString(500, start_y - lh, f"{payroll_row.allowances:,.2f}")

    c.drawString(50, start_y - 2*lh, "Deductions (base):")
    c.drawRightString(500, start_y - 2*lh, f"{payroll_row.deductions:,.2f}")

    c.drawString(50, start_y - 3*lh, "Absent days:")
    c.drawRightString(500, start_y - 3*lh, f"{payroll_row.absent_days}")

    c.drawString(50, start_y - 4*lh, "Absent deduction:")
    c.drawRightString(500, start_y - 4*lh, f"{payroll_row.absent_deduction:,.2f}")

    c.drawString(50, start_y - 5*lh, "Total deductions:")
    c.drawRightString(500, start_y - 5*lh, f"{payroll_row.total_deductions:,.2f}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, start_y - 7*lh, "Net Salary:")
    c.drawRightString(500, start_y - 7*lh, f"{payroll_row.net_salary:,.2f}")

    c.setFont("Helvetica", 9)
    c.drawString(50, 80, "This is a system generated payslip.")
    c.drawString(50, 60, f"Generated on: {datetime.utcnow().isoformat()} UTC")

    c.showPage()
    c.save()
    try:
        with open(os.path.join(os.path.dirname(__file__), "audit.log"), "a") as f:
            f.write(f"{datetime.now().isoformat()} - saved payslip - {path}\n")
    except Exception:
        pass

    return path

def validate_password(password: str):
    pattern = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,15}$"
    )

    if not pattern.match(password):
        raise HTTPException(
            status_code=400,
            detail="Password must be 8–15 characters long and include at least one uppercase, one lowercase, one digit, and one special character (@$!%*?&)."
        )
    return True
    
   
