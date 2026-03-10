from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.Enum("Department", "Officer", "Admin"), nullable=False)
    designation = db.Column(db.String(50), nullable=False)


class Department(db.Model):
    __tablename__ = "departments"

    department_id = db.Column(db.Integer, primary_key=True)
    department_code = db.Column(db.String(20), unique=True, nullable=False)
    department_name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class UserDepartment(db.Model):
    __tablename__ = "user_departments"

    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.department_id"), primary_key=True)
    assigned_on = db.Column(db.DateTime, default=db.func.current_timestamp())


class PurchaseRequest(db.Model):
    __tablename__ = "purchase_requests"

    request_id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.department_id"),
        nullable=False
    )

    request_date = db.Column(db.Date, nullable=False)

    accounts_status = db.Column(
        db.Enum("Pending", "Approved", "Rejected"),
        nullable=False,
        default="Pending"
    )

    audit_status = db.Column(
        db.Enum("Pending", "Approved", "Rejected"),
        nullable=False,
        default="Pending"
    )

    purchase_status = db.Column(
        db.Enum("Pending", "Approved", "Rejected", "Negotiation"),
        nullable=False,
        default="Pending"
    )

    cao_status = db.Column(
        db.Enum("Pending", "Approved", "Rejected", "Discuss"),
        nullable=False,
        default="Pending"
    )

    registrar_status = db.Column(
        db.Enum("Pending", "Approved", "Rejected", "Discuss"),
        nullable=False,
        default="Pending"
    )

    priority = db.Column(
        db.Enum("Low", "Medium", "High"),
        nullable=False,
        default="Low"
    )

    comments = db.Column(db.Text)

    current_stage = db.Column(
        db.Enum("Accounts", "Audit", "Purchase", "CAO", "Registrar", "Approved", "Rejected"),
        nullable=False,
        default="Accounts"
    )

    vendor_quotes = db.relationship(
        "VendorQuote",
        backref="request",
        lazy=True,
        cascade="all, delete-orphan"
    )

    purchase_order = db.relationship(
        "PurchaseOrder",
        backref="request",
        uselist=False,
        cascade="all, delete-orphan"
    )

    department = db.relationship(
        "Department",
        backref="purchase_requests",
        lazy=True
    )

class RequestLog(db.Model):
    __tablename__ = "request_logs"

    log_id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("purchase_requests.request_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    stage = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    comments = db.Column(db.Text)


class Vendor(db.Model):
    __tablename__ = "vendors"

    vendor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    gst_no = db.Column(db.String(30), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    status = db.Column(
        db.Enum("Active", "Pending", "Blacklisted"),
        nullable=False,
        default="Active"
    )
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    quotes = db.relationship(
        "VendorQuote",
        backref="vendor",
        lazy=True,
        cascade="all, delete-orphan"
    )


class VendorQuote(db.Model):
    __tablename__ = "vendor_quotes"

    quote_id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_requests.request_id"),
        nullable=False
    )
    vendor_id = db.Column(
        db.Integer,
        db.ForeignKey("vendors.vendor_id"),
        nullable=False
    )
    quoted_amount = db.Column(db.Numeric(12, 2), nullable=False)
    tax_percent = db.Column(db.Numeric(5, 2), nullable=False, default=18.00)
    delivery_days = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)
    quote_status = db.Column(
        db.Enum("Submitted", "Shortlisted", "Selected", "Rejected"),
        nullable=False,
        default="Submitted"
    )
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    __table_args__ = (
        db.UniqueConstraint(
            "request_id",
            "vendor_id",
            name="uq_request_vendor_quote"
        ),
    )


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"

    po_id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(60), unique=True, nullable=False)
    request_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_requests.request_id"),
        nullable=False,
        unique=True
    )
    vendor_id = db.Column(
        db.Integer,
        db.ForeignKey("vendors.vendor_id"),
        nullable=False
    )
    quote_id = db.Column(
        db.Integer,
        db.ForeignKey("vendor_quotes.quote_id"),
        nullable=False,
        unique=True
    )
    po_date = db.Column(db.Date, nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    item_description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_rate = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    tax_percent = db.Column(db.Numeric(5, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(12, 2), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    vendor = db.relationship("Vendor", backref="purchase_orders", lazy=True)
    quote = db.relationship("VendorQuote", backref="purchase_order", lazy=True)


class BudgetAllocation(db.Model):
    __tablename__ = "budget_allocations"

    budget_id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.department_id"),
        nullable=False
    )
    financial_year = db.Column(db.String(9), nullable=False)
    allocated_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    utilized_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    reserved_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    notes = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    __table_args__ = (
        db.UniqueConstraint(
            "department_id",
            "financial_year",
            name="uq_budget_department_year"
        ),
    )


class PaymentTransaction(db.Model):
    __tablename__ = "payment_transactions"

    payment_id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_orders.po_id"),
        nullable=False,
        unique=True
    )
    transaction_ref = db.Column(db.String(60), unique=True, nullable=False)
    payment_mode = db.Column(
        db.Enum("NEFT", "RTGS", "UPI", "CHEQUE", "CASH"),
        nullable=False,
        default="NEFT"
    )
    payment_status = db.Column(
        db.Enum("Pending", "Processing", "Paid", "Failed"),
        nullable=False,
        default="Pending"
    )
    paid_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    payment_date = db.Column(db.Date)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    purchase_order = db.relationship(
        "PurchaseOrder",
        backref=db.backref("payment_transaction", uselist=False),
        lazy=True
    )


class VendorPerformance(db.Model):
    __tablename__ = "vendor_performance"

    performance_id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_requests.request_id"),
        nullable=False,
        unique=True
    )
    vendor_id = db.Column(
        db.Integer,
        db.ForeignKey("vendors.vendor_id"),
        nullable=False
    )
    overall_rating = db.Column(db.Integer)
    quality_score = db.Column(db.Integer)
    delivery_score = db.Column(db.Integer)
    support_score = db.Column(db.Integer)
    review_comments = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    reviewed_on = db.Column(db.Date)

    request = db.relationship("PurchaseRequest", backref="vendor_performance", lazy=True)
    vendor = db.relationship("Vendor", backref="performance_entries", lazy=True)


class Notification(db.Model):
    __tablename__ = "notifications"

    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey("purchase_requests.request_id"))
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
