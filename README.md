# Campus Procurement and Vendor Management System

Flask-based system for purchase requests, multi-stage approvals, vendor onboarding, quotation management, tracking, and exports.

## Features
- Role-based login (`Department`, `Officer`, `Admin`)
- End-to-end request lifecycle: `Accounts -> Audit -> Purchase -> CAO -> Registrar`
- Request tracking with action logs
- Vendor onboarding and status control (`Active`, `Pending`, `Blacklisted`)
- Vendor quotation management with shortlist/selection flow
- Automatic Purchase Order generation after Registrar approval
- Purchase Order PDF with PO Number, Vendor Address, GST, Unit Rate, Tax, Total
- Department budget allocation, payment transactions, and vendor performance modules
- Notification system for workflow events
- Director priority/comment updates
- Admin CSV and PDF export with full transaction details
- Auto-bootstrap for database and demo users on first run

## Database Coverage
- Total tables: `12` (`users`, `departments`, `user_departments`, `purchase_requests`, `request_logs`, `vendors`, `vendor_quotes`, `purchase_orders`, `budget_allocations`, `payment_transactions`, `vendor_performance`, `notifications`)
- Faculty SQL pack: `database/DBMS_15_PLUS_COMMANDS.sql`
- DBMS categories covered: DDL, DML, DQL, TCL, DCL, View, Trigger, Procedure, Function, Index

## Tech Stack
- Python + Flask
- Flask-SQLAlchemy
- SQLite (default) or MySQL
- FPDF (PDF export)

## Quick Setup (SQLite)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

## Proper MySQL Setup (SQL Execution)
1. Create the database and tables using the SQL script:
```bash
mysql -u root -p < database/schema.sql
```
2. Configure Flask to use MySQL:
```bash
export DATABASE_URL='mysql+pymysql://root:YOUR_PASSWORD@localhost/campus_procurement'
```
3. Start the app:
```bash
python app.py
```
4. Run faculty DBMS command showcase:
```bash
mysql -u root -p < database/DBMS_15_PLUS_COMMANDS.sql
```

If your MySQL username is not `root`, replace it in the `DATABASE_URL`.

## Demo Credentials
All demo accounts use password `123`.

| Username | Role | Designation |
|---|---|---|
| `dept` | Department | Professor |
| `hod` | Department | HoD |
| `accounts` | Officer | Accounts Officer |
| `audit` | Officer | Audit Officer |
| `purchase` | Officer | Purchase Officer |
| `cao` | Officer | Chief Accounts Officer |
| `registrar` | Officer | Registrar |
| `director` | Admin | Director |
| `admin` | Admin | Admin |

## Submission Checklist
- Install dependencies from `requirements.txt`
- Run app and validate login with `admin / 123`
- Create one request via `dept / 123`
- Approve through officer stages (`accounts -> audit -> purchase -> cao -> registrar`)
- Add vendors from `Vendors` page
- Add and mark quotations from `Vendor Quotes` page
- While approving as `registrar`, PO PDF auto-downloads for approved request
- Review `DBMS Reports` dashboard for budgets/payments/performance
- Execute `database/DBMS_15_PLUS_COMMANDS.sql` (15+ SQL commands demo)
- Verify tracking timeline and action log
- Download full details CSV/PDF from admin dashboard

## Notes
- Default database path: `sqlite:///campus.db`
- You can override with `DATABASE_URL` environment variable.
- You can override session key with `SECRET_KEY` environment variable.
- Detailed SQL instructions: `database/SQL_EXECUTION_GUIDE.md`
- Faculty command script: `database/DBMS_15_PLUS_COMMANDS.sql`
- If you already had an older DB schema, recreate DB using `database/schema.sql`.
