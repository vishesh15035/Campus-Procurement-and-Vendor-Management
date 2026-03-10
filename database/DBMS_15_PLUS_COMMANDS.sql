-- Campus Procurement and Vendor Management System
-- Faculty DBMS Demonstration Script (15+ commands)
-- Run on MySQL 8+/9+

-- 01) Switch DB
USE campus_procurement;

-- 02) List all tables
SHOW TABLES;

-- 03) Describe a core table
DESCRIBE purchase_orders;

-- 04) Basic SELECT with filter
SELECT request_id, item_name, quantity, current_stage
FROM purchase_requests
WHERE current_stage IN ('Purchase', 'Registrar', 'Approved');

-- 05) INSERT sample notification (DML)
INSERT INTO notifications (user_id, request_id, title, message, is_read)
SELECT user_id, NULL, 'DBMS Demo', 'Demo notification for command showcase', FALSE
FROM users
WHERE username = 'admin'
LIMIT 1;

-- 06) UPDATE sample data (DML)
UPDATE vendors
SET status = 'Pending'
WHERE status = 'Active'
  AND vendor_id IN (SELECT vendor_id FROM vendor_quotes);

-- 07) DELETE sample demo notification (DML)
DELETE FROM notifications
WHERE title = 'DBMS Demo'
  AND request_id IS NULL;

-- 08) JOIN query across 4 tables
SELECT
    pr.request_id,
    pr.item_name,
    v.name AS vendor_name,
    po.po_number,
    pt.payment_status
FROM purchase_requests pr
LEFT JOIN purchase_orders po ON po.request_id = pr.request_id
LEFT JOIN vendors v ON v.vendor_id = po.vendor_id
LEFT JOIN payment_transactions pt ON pt.po_id = po.po_id
ORDER BY pr.request_id DESC;

-- 09) Aggregate query with GROUP BY + HAVING
SELECT
    d.department_code,
    d.department_name,
    COUNT(pr.request_id) AS total_requests,
    COALESCE(SUM(po.total_amount), 0) AS total_po_value
FROM departments d
LEFT JOIN purchase_requests pr ON pr.department_id = d.department_id
LEFT JOIN purchase_orders po ON po.request_id = pr.request_id
GROUP BY d.department_id, d.department_code, d.department_name
HAVING total_requests >= 0
ORDER BY total_po_value DESC;

-- 10) Subquery example
SELECT name, category, status
FROM vendors
WHERE vendor_id IN (
    SELECT vendor_id
    FROM vendor_quotes
    WHERE quote_status = 'Selected'
);

-- 11) Create VIEW for approved requests
CREATE OR REPLACE VIEW vw_approved_requests AS
SELECT
    pr.request_id,
    pr.item_name,
    pr.quantity,
    d.department_code,
    po.po_number,
    po.total_amount
FROM purchase_requests pr
JOIN departments d ON d.department_id = pr.department_id
LEFT JOIN purchase_orders po ON po.request_id = pr.request_id
WHERE pr.current_stage = 'Approved';

-- 12) Query from VIEW
SELECT * FROM vw_approved_requests ORDER BY request_id DESC;

-- 13) Transaction control (TCL)
START TRANSACTION;
UPDATE budget_allocations
SET utilized_amount = utilized_amount
WHERE budget_id = 1;
SAVEPOINT budget_check;
UPDATE budget_allocations
SET reserved_amount = reserved_amount
WHERE budget_id = 1;
ROLLBACK TO budget_check;
COMMIT;

-- 14) Create INDEX (DDL optimization, idempotent)
SET @index_exists := (
    SELECT COUNT(1)
    FROM information_schema.statistics
    WHERE table_schema = 'campus_procurement'
      AND table_name = 'vendor_quotes'
      AND index_name = 'idx_vendor_quotes_status_amount'
);
SET @create_index_sql := IF(
    @index_exists = 0,
    'CREATE INDEX idx_vendor_quotes_status_amount ON vendor_quotes (quote_status, quoted_amount)',
    'SELECT "Index already exists"'
);
PREPARE stmt_index FROM @create_index_sql;
EXECUTE stmt_index;
DEALLOCATE PREPARE stmt_index;

-- 15) Trigger for automatic notification on payment marked paid
DROP TRIGGER IF EXISTS trg_payment_paid_notification;
DELIMITER $$
CREATE TRIGGER trg_payment_paid_notification
AFTER UPDATE ON payment_transactions
FOR EACH ROW
BEGIN
    IF NEW.payment_status = 'Paid' AND OLD.payment_status <> 'Paid' THEN
        INSERT INTO notifications (user_id, request_id, title, message, is_read)
        SELECT
            pr.created_by,
            pr.request_id,
            'Payment Completed',
            CONCAT('Payment completed for PO ', po.po_number),
            FALSE
        FROM purchase_orders po
        JOIN purchase_requests pr ON pr.request_id = po.request_id
        WHERE po.po_id = NEW.po_id
        LIMIT 1;
    END IF;
END$$
DELIMITER ;

-- 16) Stored Procedure for payment update
DROP PROCEDURE IF EXISTS sp_mark_payment_paid;
DELIMITER $$
CREATE PROCEDURE sp_mark_payment_paid(IN p_payment_id INT, IN p_mode VARCHAR(10))
BEGIN
    UPDATE payment_transactions
    SET payment_status = 'Paid',
        payment_mode = p_mode,
        payment_date = CURDATE()
    WHERE payment_id = p_payment_id;
END$$
DELIMITER ;

-- 17) Call procedure
-- CALL sp_mark_payment_paid(1, 'NEFT');

-- 18) User-defined function for vendor average score
DROP FUNCTION IF EXISTS fn_vendor_average_rating;
DELIMITER $$
CREATE FUNCTION fn_vendor_average_rating(p_vendor_id INT)
RETURNS DECIMAL(5,2)
DETERMINISTIC
BEGIN
    DECLARE avg_rating DECIMAL(5,2);
    SELECT COALESCE(AVG(overall_rating), 0)
    INTO avg_rating
    FROM vendor_performance
    WHERE vendor_id = p_vendor_id;
    RETURN avg_rating;
END$$
DELIMITER ;

-- 19) Function usage
SELECT
    v.vendor_id,
    v.name,
    fn_vendor_average_rating(v.vendor_id) AS avg_rating
FROM vendors v;

-- 20) DCL examples (run as privileged user)
-- CREATE USER IF NOT EXISTS 'campus_auditor'@'localhost' IDENTIFIED BY 'Audit123';
-- GRANT SELECT ON campus_procurement.* TO 'campus_auditor'@'localhost';
-- REVOKE INSERT, UPDATE, DELETE ON campus_procurement.* FROM 'campus_auditor'@'localhost';
-- FLUSH PRIVILEGES;
