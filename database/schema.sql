CREATE DATABASE IF NOT EXISTS campus_procurement;
USE campus_procurement;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(50) NOT NULL,
    role ENUM('Department', 'Officer', 'Admin') NOT NULL,
    designation VARCHAR(50) NOT NULL
);



CREATE TABLE user_departments (
    user_id INT NOT NULL,
    department_id INT NOT NULL,
    assigned_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, department_id),
    CONSTRAINT fk_user_dept_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_dept_department FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE CASCADE
);

CREATE TABLE purchase_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    quantity INT NOT NULL,
    created_by INT NOT NULL,
    department_id INT NOT NULL,
    request_date DATE NOT NULL,
    accounts_status ENUM('Pending', 'Approved', 'Rejected') NOT NULL DEFAULT 'Pending',
    audit_status ENUM('Pending', 'Approved', 'Rejected') NOT NULL DEFAULT 'Pending',
    purchase_status ENUM('Pending', 'Approved', 'Rejected', 'Negotiation') NOT NULL DEFAULT 'Pending',
    cao_status ENUM('Pending', 'Approved', 'Rejected', 'Discuss') NOT NULL DEFAULT 'Pending',
    registrar_status ENUM('Pending', 'Approved', 'Rejected', 'Discuss') NOT NULL DEFAULT 'Pending',
    priority ENUM('Low', 'Medium', 'High') NOT NULL DEFAULT 'Low',
    comments TEXT NULL,
    current_stage ENUM('Accounts', 'Audit', 'Purchase', 'CAO', 'Registrar', 'Approved', 'Rejected') NOT NULL DEFAULT 'Accounts',
    CONSTRAINT fk_request_user FOREIGN KEY (created_by) REFERENCES users(user_id),
    CONSTRAINT fk_request_department FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE request_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    user_id INT NOT NULL,
    stage VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    comments TEXT NULL,
    CONSTRAINT fk_logs_request FOREIGN KEY (request_id) REFERENCES purchase_requests(request_id) ON DELETE CASCADE,
    CONSTRAINT fk_logs_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE vendors (
    vendor_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) UNIQUE NOT NULL,
    contact_person VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    gst_no VARCHAR(30) NOT NULL,
    category VARCHAR(80) NOT NULL,
    status ENUM('Active', 'Pending', 'Blacklisted') NOT NULL DEFAULT 'Active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vendor_quotes (
    quote_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    vendor_id INT NOT NULL,
    quoted_amount DECIMAL(12,2) NOT NULL,
    tax_percent DECIMAL(5,2) NOT NULL DEFAULT 18.00,
    delivery_days INT NOT NULL,
    notes TEXT NULL,
    quote_status ENUM('Submitted', 'Shortlisted', 'Selected', 'Rejected') NOT NULL DEFAULT 'Submitted',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_request_vendor_quote UNIQUE (request_id, vendor_id),
    CONSTRAINT fk_quotes_request FOREIGN KEY (request_id) REFERENCES purchase_requests(request_id) ON DELETE CASCADE,
    CONSTRAINT fk_quotes_vendor FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id) ON DELETE CASCADE
);

CREATE TABLE purchase_orders (
    po_id INT AUTO_INCREMENT PRIMARY KEY,
    po_number VARCHAR(60) UNIQUE NOT NULL,
    request_id INT NOT NULL UNIQUE,
    vendor_id INT NOT NULL,
    quote_id INT NOT NULL UNIQUE,
    po_date DATE NOT NULL,
    item_name VARCHAR(150) NOT NULL,
    item_description TEXT NOT NULL,
    quantity INT NOT NULL,
    unit_rate DECIMAL(12,2) NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL,
    tax_percent DECIMAL(5,2) NOT NULL,
    tax_amount DECIMAL(12,2) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    created_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_po_request FOREIGN KEY (request_id) REFERENCES purchase_requests(request_id) ON DELETE CASCADE,
    CONSTRAINT fk_po_vendor FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
    CONSTRAINT fk_po_quote FOREIGN KEY (quote_id) REFERENCES vendor_quotes(quote_id),
    CONSTRAINT fk_po_user FOREIGN KEY (created_by) REFERENCES users(user_id)
);

CREATE TABLE budget_allocations (
    budget_id INT AUTO_INCREMENT PRIMARY KEY,
    department_id INT NOT NULL,
    financial_year VARCHAR(9) NOT NULL,
    allocated_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    utilized_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    reserved_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    notes TEXT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_budget_department_year UNIQUE (department_id, financial_year),
    CONSTRAINT fk_budget_department FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE CASCADE
);

CREATE TABLE payment_transactions (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    po_id INT NOT NULL UNIQUE,
    transaction_ref VARCHAR(60) UNIQUE NOT NULL,
    payment_mode ENUM('NEFT', 'RTGS', 'UPI', 'CHEQUE', 'CASH') NOT NULL DEFAULT 'NEFT',
    payment_status ENUM('Pending', 'Processing', 'Paid', 'Failed') NOT NULL DEFAULT 'Pending',
    paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    payment_date DATE NULL,
    remarks TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_po FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id) ON DELETE CASCADE
);

CREATE TABLE vendor_performance (
    performance_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL UNIQUE,
    vendor_id INT NOT NULL,
    overall_rating INT NULL,
    quality_score INT NULL,
    delivery_score INT NULL,
    support_score INT NULL,
    review_comments TEXT NULL,
    reviewed_by INT NULL,
    reviewed_on DATE NULL,
    CONSTRAINT fk_performance_request FOREIGN KEY (request_id) REFERENCES purchase_requests(request_id) ON DELETE CASCADE,
    CONSTRAINT fk_performance_vendor FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
    CONSTRAINT fk_performance_user FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
);

CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    request_id INT NULL,
    title VARCHAR(120) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_notification_request FOREIGN KEY (request_id) REFERENCES purchase_requests(request_id) ON DELETE SET NULL
);

INSERT IGNORE INTO departments (department_code, department_name) VALUES
('CSE', 'Computer Science and Engineering'),
('ECE', 'Electronics and Communication Engineering'),
('ME', 'Mechanical Engineering'),
('CIVIL', 'Civil Engineering');

INSERT IGNORE INTO users (username, password, role, designation) VALUES
('dept', '123', 'Department', 'Professor'),
('hod', '123', 'Department', 'HoD'),
('accounts', '123', 'Officer', 'Accounts Officer'),
('audit', '123', 'Officer', 'Audit Officer'),
('purchase', '123', 'Officer', 'Purchase Officer'),
('cao', '123', 'Officer', 'Chief Accounts Officer'),
('registrar', '123', 'Officer', 'Registrar'),
('director', '123', 'Admin', 'Director'),
('admin', '123', 'Admin', 'Admin');

INSERT IGNORE INTO user_departments (user_id, department_id)
SELECT users.user_id, departments.department_id
FROM users
JOIN departments ON departments.department_code = 'CSE';

INSERT IGNORE INTO budget_allocations (
    department_id,
    financial_year,
    allocated_amount,
    utilized_amount,
    reserved_amount,
    notes
)
SELECT
    departments.department_id,
    '2025-26',
    5000000.00,
    0.00,
    5000000.00,
    'Initial annual budget'
FROM departments
WHERE departments.department_code = 'CSE';

INSERT IGNORE INTO vendors (name, contact_person, email, phone, address, gst_no, category, status) VALUES
('TechNova Solutions', 'Ravi Mehta', 'contact@technova.in', '9988776655', 'Office 201, Prime Tech Park, Ahmedabad - 380015', '24AABCT1234K1Z7', 'IT Equipment', 'Active'),
('Campus Office Mart', 'Neha Sharma', 'sales@campusofficemart.in', '9876543210', '12 Stationery Market, Navrangpura, Ahmedabad - 380009', '24AACCO5678M1Z2', 'Office Supplies', 'Active'),
('LabBridge Instruments', 'Arjun Nair', 'quotes@labbridge.in', '9123456789', '42 Science Plaza, Vastrapur, Ahmedabad - 380054', '24AABCL9012R1Z5', 'Laboratory', 'Active');

CREATE INDEX idx_purchase_requests_stage ON purchase_requests(current_stage);
CREATE INDEX idx_notifications_user_read ON notifications(user_id, is_read);
CREATE INDEX idx_payment_status ON payment_transactions(payment_status);
