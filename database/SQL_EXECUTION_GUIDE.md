# MySQL Execution Guide

Use these steps for proper SQL-based execution of the project.
The script uses `INSERT IGNORE`, so re-running is safe for seed data.

## 1) Create schema and seed base data
If you already executed an older schema version, reset first:
```sql
DROP DATABASE IF EXISTS campus_procurement;
```
Then run:
```bash
mysql -u root -p < database/schema.sql
```

## 2) Verify tables
```sql
USE campus_procurement;
SHOW TABLES;
```

Expected key tables:
- `users`
- `departments`
- `user_departments`
- `purchase_requests`
- `request_logs`
- `vendors`
- `vendor_quotes`
- `purchase_orders`
- `budget_allocations`
- `payment_transactions`
- `vendor_performance`
- `notifications`

## 3) Verify seed users and vendors
```sql
SELECT username, role, designation FROM users;
SELECT vendor_id, name, gst_no, category, status FROM vendors;
SELECT quote_id, request_id, vendor_id, quoted_amount, tax_percent, quote_status FROM vendor_quotes;
SELECT po_id, po_number, request_id, vendor_id, total_amount FROM purchase_orders;
SELECT budget_id, department_id, financial_year, allocated_amount, utilized_amount FROM budget_allocations;
SELECT payment_id, po_id, transaction_ref, payment_status, paid_amount FROM payment_transactions;
```

## 4) Configure app for MySQL
```bash
export DATABASE_URL='mysql+pymysql://root:YOUR_PASSWORD@localhost/campus_procurement'
python app.py
```

## 5) Run faculty DBMS command pack (15+ commands)
```bash
mysql -u root -p < database/DBMS_15_PLUS_COMMANDS.sql
```

## 6) Optional reset for clean demo
```sql
DROP DATABASE IF EXISTS campus_procurement;
```
Then re-run step 1.
