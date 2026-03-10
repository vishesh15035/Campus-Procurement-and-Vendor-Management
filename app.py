from flask import (
    Flask, render_template, request,
    redirect, session, Response, flash, url_for
)
from models import (
    db, User, PurchaseRequest, RequestLog,
    Vendor, VendorQuote, PurchaseOrder,
    Department, UserDepartment, BudgetAllocation,
    PaymentTransaction, VendorPerformance, Notification
)
from os import environ
from csv import writer
from io import StringIO
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import wraps
from fpdf import FPDF

# find . -name "__pycache__" -type d -exec rm -rf {} +

# -------------------------------------------------
# APP CONFIG
# -------------------------------------------------
app = Flask(__name__)
app.secret_key = environ.get("SECRET_KEY", "secure_key")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    environ.get("DATABASE_URL", "sqlite:///campus.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

DEFAULT_USERS = [
    ("dept", "123", "Department", "Professor"),
    ("hod", "123", "Department", "HoD"),
    ("accounts", "123", "Officer", "Accounts Officer"),
    ("audit", "123", "Officer", "Audit Officer"),
    ("purchase", "123", "Officer", "Purchase Officer"),
    ("cao", "123", "Officer", "Chief Accounts Officer"),
    ("registrar", "123", "Officer", "Registrar"),
    ("director", "123", "Admin", "Director"),
    ("admin", "123", "Admin", "Admin"),
]

DEFAULT_VENDORS = [
    (
        "TechNova Solutions",
        "Ravi Mehta",
        "contact@technova.in",
        "9988776655",
        "Office 201, Prime Tech Park, Ahmedabad - 380015",
        "24AABCT1234K1Z7",
        "IT Equipment"
    ),
    (
        "Campus Office Mart",
        "Neha Sharma",
        "sales@campusofficemart.in",
        "9876543210",
        "12 Stationery Market, Navrangpura, Ahmedabad - 380009",
        "24AACCO5678M1Z2",
        "Office Supplies"
    ),
    (
        "LabBridge Instruments",
        "Arjun Nair",
        "quotes@labbridge.in",
        "9123456789",
        "42 Science Plaza, Vastrapur, Ahmedabad - 380054",
        "24AABCL9012R1Z5",
        "Laboratory"
    ),
]

DEFAULT_DEPARTMENTS = [
    ("CSE", "Computer Science and Engineering"),
    ("ECE", "Electronics and Communication Engineering"),
    ("ME", "Mechanical Engineering"),
    ("CIVIL", "Civil Engineering"),
]


def bootstrap_data():
    db.create_all()
    existing_usernames = {
        username for (username,) in db.session.query(User.username).all()
    }
    new_users_added = False
    for username, password, role, designation in DEFAULT_USERS:
        if username not in existing_usernames:
            db.session.add(
                User(
                    username=username,
                    password=password,
                    role=role,
                    designation=designation
                )
            )
            new_users_added = True

    if new_users_added:
        db.session.commit()

    existing_department_codes = {
        code for (code,) in db.session.query(Department.department_code).all()
    }
    new_departments_added = False
    for department_code, department_name in DEFAULT_DEPARTMENTS:
        if department_code not in existing_department_codes:
            db.session.add(
                Department(
                    department_code=department_code,
                    department_name=department_name
                )
            )
            new_departments_added = True

    if new_departments_added:
        db.session.commit()

    department_by_code = {
        department.department_code: department
        for department in Department.query.all()
    }
    default_department = department_by_code.get("CSE")
    if default_department:
        existing_user_department_ids = {
            user_id for (user_id,) in db.session.query(UserDepartment.user_id).all()
        }
        all_users = User.query.all()
        new_user_department_added = False
        for user in all_users:
            if user.user_id not in existing_user_department_ids:
                db.session.add(
                    UserDepartment(
                        user_id=user.user_id,
                        department_id=default_department.department_id
                    )
                )
                new_user_department_added = True

        if new_user_department_added:
            db.session.commit()

    current_financial_year = get_financial_year(date.today())
    if default_department:
        existing_budget_entry = BudgetAllocation.query.filter_by(
            department_id=default_department.department_id,
            financial_year=current_financial_year
        ).first()
        if not existing_budget_entry:
            db.session.add(
                BudgetAllocation(
                    department_id=default_department.department_id,
                    financial_year=current_financial_year,
                    allocated_amount=Decimal("5000000.00"),
                    utilized_amount=Decimal("0.00"),
                    reserved_amount=Decimal("0.00"),
                    notes="Initial annual allocation"
                )
            )
            db.session.commit()

    existing_vendor_names = {
        name for (name,) in db.session.query(Vendor.name).all()
    }
    new_vendors_added = False
    for (
        name,
        contact_person,
        email,
        phone,
        address,
        gst_no,
        category
    ) in DEFAULT_VENDORS:
        if name not in existing_vendor_names:
            db.session.add(
                Vendor(
                    name=name,
                    contact_person=contact_person,
                    email=email,
                    phone=phone,
                    address=address,
                    gst_no=gst_no,
                    category=category,
                    status="Active"
                )
            )
            new_vendors_added = True

    if new_vendors_added:
        db.session.commit()


@app.before_request
def ensure_bootstrap():
    if not app.config.get("_BOOTSTRAPPED"):
        bootstrap_data()
        app.config["_BOOTSTRAPPED"] = True


@app.context_processor
def inject_notification_count():
    user_id = session.get("user_id")
    if not user_id:
        return {"unread_notification_count": 0}

    unread_count = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).count()
    return {"unread_notification_count": unread_count}


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper


def has_designation(name):
    return session.get("designation") == name


def can_manage_vendors():
    return (
        session.get("role") == "Admin" or
        session.get("designation") in {
            "Purchase Officer", "Director", "Admin"
        }
    )


def can_access_request_data(purchase_request):
    if session.get("role") == "Admin":
        return True

    designation = session.get("designation")
    if designation in {
        "HoD", "Registrar", "Director",
        "Chief Accounts Officer", "Purchase Officer"
    }:
        return True

    return purchase_request.created_by == session.get("user_id")


def get_default_department_id():
    department = Department.query.order_by(Department.department_id.asc()).first()
    return department.department_id if department else None


def get_user_department_id(user_id):
    mapping = UserDepartment.query.filter_by(user_id=user_id).first()
    if mapping:
        return mapping.department_id
    return get_default_department_id()


def create_notification_for_user(user_id, title, message, request_id=None):
    db.session.add(
        Notification(
            user_id=user_id,
            request_id=request_id,
            title=title,
            message=message
        )
    )


def notify_users_by_designation(designation, title, message, request_id=None):
    users = User.query.filter_by(designation=designation).all()
    for user in users:
        create_notification_for_user(user.user_id, title, message, request_id)


def get_financial_year(target_date):
    start_year = target_date.year if target_date.month >= 4 else target_date.year - 1
    end_year = str(start_year + 1)[-2:]
    return f"{start_year}-{end_year}"


def get_financial_year_date_range(financial_year):
    start_year = int(financial_year.split("-")[0])
    start_date = date(start_year, 4, 1)
    end_date = date(start_year + 1, 3, 31)
    return start_date, end_date


def refresh_department_budget_utilization(department_id, financial_year):
    start_date, end_date = get_financial_year_date_range(financial_year)
    total_utilized = db.session.query(
        db.func.coalesce(db.func.sum(PurchaseOrder.total_amount), 0)
    ).join(
        PurchaseRequest, PurchaseRequest.request_id == PurchaseOrder.request_id
    ).filter(
        PurchaseRequest.department_id == department_id,
        PurchaseOrder.po_date >= start_date,
        PurchaseOrder.po_date <= end_date
    ).scalar()

    budget = BudgetAllocation.query.filter_by(
        department_id=department_id,
        financial_year=financial_year
    ).first()
    if not budget:
        budget = BudgetAllocation(
            department_id=department_id,
            financial_year=financial_year,
            allocated_amount=Decimal("0.00"),
            utilized_amount=Decimal("0.00"),
            reserved_amount=Decimal("0.00"),
            notes="Auto-created from PO transactions"
        )
        db.session.add(budget)

    budget.utilized_amount = Decimal(total_utilized).quantize(Decimal("0.01"))
    if budget.allocated_amount > budget.utilized_amount:
        budget.reserved_amount = (
            budget.allocated_amount - budget.utilized_amount
        ).quantize(Decimal("0.01"))
    else:
        budget.reserved_amount = Decimal("0.00")


def ensure_payment_transaction_for_po(purchase_order):
    payment_transaction = PaymentTransaction.query.filter_by(
        po_id=purchase_order.po_id
    ).first()
    transaction_ref = f"PAY-{purchase_order.po_number.replace('/', '-')}"

    if not payment_transaction:
        payment_transaction = PaymentTransaction(
            po_id=purchase_order.po_id,
            transaction_ref=transaction_ref,
            payment_mode="NEFT",
            payment_status="Pending",
            paid_amount=Decimal(purchase_order.total_amount),
            remarks="Auto-created after PO generation"
        )
        db.session.add(payment_transaction)
    else:
        payment_transaction.paid_amount = Decimal(purchase_order.total_amount)


def ordinal_suffix(day):
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def format_date_ordinal(d):
    suffix = ordinal_suffix(d.day)
    return f"{d.day}{suffix} {d.strftime('%B, %Y')}"


def generate_po_number(po_date, department_code="IT"):
    financial_year = get_financial_year(po_date)
    prefix = f"NU/IT/PO/{department_code}/"
    latest_po = (
        PurchaseOrder.query.filter(PurchaseOrder.po_number.like(f"{prefix}%"))
        .order_by(PurchaseOrder.po_id.desc())
        .first()
    )
    if latest_po:
        try:
            # po_number: NU/IT/PO/{dept}/{serial}/{year}/
            parts = latest_po.po_number.rstrip("/").rsplit("/", 2)
            latest_serial = int(parts[-2]) if len(parts) >= 2 else latest_po.po_id
        except (ValueError, IndexError):
            latest_serial = latest_po.po_id
    else:
        latest_serial = 0

    serial = f"{latest_serial + 1:04d}"
    return f"{prefix}{serial}/{financial_year}/"


def calculate_po_totals(quantity, unit_rate, tax_percent):
    subtotal = (unit_rate * Decimal(quantity)).quantize(Decimal("0.01"))
    tax_amount = ((subtotal * tax_percent) / Decimal("100")).quantize(Decimal("0.01"))
    total_amount = (subtotal + tax_amount).quantize(Decimal("0.01"))
    return subtotal, tax_amount, total_amount


def create_or_update_purchase_order(purchase_request, selected_quote, created_by_user_id):
    po_date = date.today()
    unit_rate = Decimal(selected_quote.quoted_amount)
    tax_percent = Decimal(selected_quote.tax_percent)
    subtotal, tax_amount, total_amount = calculate_po_totals(
        purchase_request.quantity,
        unit_rate,
        tax_percent
    )

    # Resolve department code for PO number
    dept_obj = Department.query.get(purchase_request.department_id)
    dept_code = dept_obj.department_code if dept_obj else "NU"

    purchase_order = PurchaseOrder.query.filter_by(
        request_id=purchase_request.request_id
    ).first()
    if not purchase_order:
        purchase_order = PurchaseOrder(
            po_number=generate_po_number(po_date, dept_code),
            request_id=purchase_request.request_id,
            vendor_id=selected_quote.vendor_id,
            quote_id=selected_quote.quote_id,
            po_date=po_date,
            item_name=purchase_request.item_name,
            item_description=selected_quote.notes or purchase_request.item_name,
            quantity=purchase_request.quantity,
            unit_rate=unit_rate,
            subtotal=subtotal,
            tax_percent=tax_percent,
            tax_amount=tax_amount,
            total_amount=total_amount,
            created_by=created_by_user_id
        )
        db.session.add(purchase_order)
        db.session.flush()
    else:
        purchase_order.vendor_id = selected_quote.vendor_id
        purchase_order.quote_id = selected_quote.quote_id
        purchase_order.po_date = po_date
        purchase_order.item_name = purchase_request.item_name
        purchase_order.item_description = selected_quote.notes or purchase_request.item_name
        purchase_order.quantity = purchase_request.quantity
        purchase_order.unit_rate = unit_rate
        purchase_order.subtotal = subtotal
        purchase_order.tax_percent = tax_percent
        purchase_order.tax_amount = tax_amount
        purchase_order.total_amount = total_amount

    ensure_payment_transaction_for_po(purchase_order)
    financial_year = get_financial_year(po_date)
    if purchase_request.department_id:
        refresh_department_budget_utilization(
            purchase_request.department_id,
            financial_year
        )

    return purchase_order


def build_purchase_order_pdf_response(purchase_order):
    vendor = purchase_order.vendor
    request_obj = purchase_order.request

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)

    # Convenience: content width and a helper to safely use multi_cell
    CW = pdf.w - pdf.l_margin - pdf.r_margin   # 170 mm

    def row(text, font_style="", font_size=12, h=7):
        """Single line — always resets X so it starts at left margin."""
        pdf.set_font("Times", font_style, font_size)
        pdf.set_x(pdf.l_margin)
        pdf.cell(CW, h, text, new_x="LMARGIN", new_y="NEXT")

    def multirow(text, font_style="", font_size=12, h=7):
        """Multi-line cell — always resets X before calling multi_cell."""
        pdf.set_font("Times", font_style, font_size)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(CW, h, text)

    # ── PO Number & Date ──────────────────────────────────────────────────────
    row(purchase_order.po_number)
    row(f"Date: {format_date_ordinal(purchase_order.po_date)}")
    pdf.ln(5)

    # ── Vendor "To" Block ─────────────────────────────────────────────────────
    row("To")
    row(vendor.name, font_style="B")
    multirow(vendor.address)                      # address wraps naturally
    row(f"GSTIN: {vendor.gst_no}")
    pdf.ln(5)

    # ── Subject ───────────────────────────────────────────────────────────────
    multirow(f"Subject: Purchase order for {purchase_order.item_name}", font_style="B")
    pdf.ln(3)

    # ── Salutation & intro ────────────────────────────────────────────────────
    row("Dear Sir,")
    row("We are pleased to place an order of the following items")
    pdf.ln(2)

    # ── Item Table ────────────────────────────────────────────────────────────
    col_widths = [15, 65, 37, 22, 37]  # Sr No | Item Desc | Unit Rate | Qty | Total
    headers = [
        "Sr\nNo",
        "Item description",
        "Unit Rate\n(Including GST)",
        "Qty",
        "Total\n(Including GST)",
    ]
    row_h = 8
    header_h = 10

    pdf.set_font("Times", "B", 11)
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        pdf.multi_cell(
            w, header_h, h, border=1, align="C",
            new_x="RIGHT" if i < len(headers) - 1 else "LMARGIN",
            new_y="TOP" if i < len(headers) - 1 else "NEXT"
        )

    pdf.set_font("Times", "", 12)
    unit_rate = Decimal(purchase_order.unit_rate)
    qty = purchase_order.quantity
    row_total = (unit_rate * qty).quantize(Decimal("0.01"))

    cells = [
        ("1", col_widths[0], "C"),
        (purchase_order.item_name, col_widths[1], "L"),
        (f"{unit_rate:.2f}", col_widths[2], "R"),
        (str(qty), col_widths[3], "C"),
        (f"{row_total:.2f}", col_widths[4], "R"),
    ]
    for i, (txt, w, align) in enumerate(cells):
        pdf.cell(
            w, row_h, txt, border=1, align=align,
            new_x="RIGHT" if i < len(cells) - 1 else "LMARGIN",
            new_y="TOP" if i < len(cells) - 1 else "NEXT"
        )

    # ── Totals rows ───────────────────────────────────────────────────────────
    subtotal = Decimal(purchase_order.subtotal)
    tax_pct = Decimal(purchase_order.tax_percent)
    tax_amt = Decimal(purchase_order.tax_amount)
    total = Decimal(purchase_order.total_amount)
    rounded_total = int(total.quantize(Decimal("1"), rounding="ROUND_HALF_UP"))
    round_off = Decimal(rounded_total) - total

    label_w = sum(col_widths[:4])   # span first 4 columns
    val_w = col_widths[4]

    def total_row(label, value, bold=False):
        pdf.set_font("Times", "B" if bold else "", 12)
        pdf.set_x(pdf.l_margin)
        pdf.cell(label_w, row_h, label, border=1, align="R")
        pdf.cell(val_w, row_h, value, border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    total_row("Subtotal", f"{subtotal:.1f}")
    total_row(f"GST ({tax_pct:.0f}%)", f"{tax_amt:.2f}")
    total_row("Total", f"{total:.2f}")
    round_sign = "+" if round_off >= 0 else ""
    total_row("Round-Off", f"{round_sign}{round_off:.2f}")
    total_row("Grand Total", str(rounded_total), bold=True)

    pdf.ln(6)

    # ── Terms & Conditions ────────────────────────────────────────────────────
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    row("Other terms and conditions:")
    delivery_days = 14
    selected_quote_for_delivery = VendorQuote.query.filter_by(
        request_id=purchase_order.request_id,
        quote_status="Selected"
    ).first()
    if selected_quote_for_delivery:
        delivery_days = selected_quote_for_delivery.delivery_days
    terms = [
        "The above prices are inclusive of all taxes and tariffs.",
        "Payment: To be made by the department and later to be reimbursed.",
        f"Delivery: {delivery_days} days after payment.",
        "Warranty: As per manufacturer.",
        "Nirma University GST no. 24AAATT6829N1ZY. Mention HSN code in the bill.",
        (
            "Submit e-invoice with tax invoice if your annual turnover is more than five crores. "
            "In case your turnover is less than 5 crores, submit the declaration for the same."
        ),
    ]
    for idx, term in enumerate(terms, 1):
        multirow(f"{idx}. {term}")

    pdf.ln(5)
    row("Thanking You")
    pdf.ln(15)

    # ── Authorized Signatory ──────────────────────────────────────────────────
    row("Authorized Signatory")
    row("Institute of Technology, Nirma University, S G Highway, Ahmedabad")

    pdf_data = bytes(pdf.output())

    safe_name = purchase_order.po_number.replace("/", "_").strip("_")
    response = Response(pdf_data)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'
    return response


def build_vendor_offer_pdf_response(purchase_request, selected_quote):
    vendor = selected_quote.vendor
    unit_rate = Decimal(selected_quote.quoted_amount)
    tax_percent = Decimal(selected_quote.tax_percent)
    subtotal, tax_amount, total_amount = calculate_po_totals(
        purchase_request.quantity,
        unit_rate,
        tax_percent
    )

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "VENDOR OFFER DETAILS", ln=True, align="C")
    pdf.ln(3)

    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, f"Request ID: {purchase_request.request_id}", ln=True)
    pdf.cell(0, 7, f"Date: {date.today().strftime('%d-%m-%Y')}", ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "Vendor Details", ln=True)
    pdf.set_font("Arial", "", 10)
    cw = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(cw, 6, f"Name: {vendor.name}")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(cw, 6, f"Address: {vendor.address}")
    pdf.cell(0, 6, f"GST No: {vendor.gst_no}", ln=True)
    pdf.cell(0, 6, f"Email: {vendor.email} | Phone: {vendor.phone}", ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "Item & Rate Details", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Item Name: {purchase_request.item_name}", ln=True)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(cw, 6, f"Description: {selected_quote.notes or purchase_request.item_name}")
    pdf.cell(0, 6, f"Quantity: {purchase_request.quantity}", ln=True)
    pdf.cell(0, 6, f"Unit Rate: {unit_rate:.2f}", ln=True)
    pdf.cell(0, 6, f"Subtotal: {subtotal:.2f}", ln=True)
    pdf.cell(0, 6, f"Tax (%): {tax_percent:.2f}", ln=True)
    pdf.cell(0, 6, f"Tax Amount: {tax_amount:.2f}", ln=True)
    pdf.cell(0, 6, f"Total Price: {total_amount:.2f}", ln=True)
    pdf.cell(0, 6, f"Quote Status: {selected_quote.quote_status}", ln=True)

    pdf_data = bytes(pdf.output())

    response = Response(pdf_data)
    response.headers["Content-Type"] = "application/pdf"
    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename=Vendor_Offer_Request_{purchase_request.request_id}.pdf"
    return response


@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session.clear()
            session["user_id"] = user.user_id
            session["role"] = user.role
            session["designation"] = user.designation
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")

    return render_template("login.html", default_users=DEFAULT_USERS)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You are logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    uid = session.get("user_id")
    designation = session.get("designation")

    if not role or not uid or not designation:
        session.clear()
        flash("Session expired. Please login again.", "error")
        return redirect(url_for("login"))

    if role == "Department":
        if designation == "Professor":
            reqs = PurchaseRequest.query.filter_by(created_by=uid).order_by(PurchaseRequest.request_id.desc()).all()
            return render_template("dash_department.html", requests=reqs)

        if designation == "HoD":
            reqs = PurchaseRequest.query.order_by(PurchaseRequest.request_id.desc()).all()
            return render_template("dash_department.html", requests=reqs)
        return "Unauthorized", 403


    if role == "Officer":
        # Show ALL requests so officers can see the full pipeline;
        # action forms in the template gate actions to the correct stage/role.
        reqs = PurchaseRequest.query.order_by(PurchaseRequest.request_id.desc()).all()
        return render_template("dash_officer.html", requests=reqs)

    if role == "Admin":
        reqs = PurchaseRequest.query.order_by(PurchaseRequest.request_id.desc()).all()
        return render_template("dash_admin.html", requests=reqs)

    return "Unauthorized", 403

def log_action(req_id, stage, action, decision, comments=""):
    user_id = session.get("user_id")
    if not user_id:
        return
    log = RequestLog(
        request_id=req_id,
        user_id=user_id,
        stage=stage,
        action=f"{action} - {decision}",
        comments=comments
    )
    db.session.add(log)

@app.route("/new_request", methods=["GET", "POST"])
@login_required
def new_request():
    if session.get("role") != "Department":
        return "Unauthorized", 403

    departments = Department.query.order_by(Department.department_name).all()

    if request.method == "POST":
        item_name = request.form.get("item", "").strip()
        qty_value = request.form.get("qty", "").strip()
        dept_id_str = request.form.get("department_id", "").strip()
        if not item_name:
            flash("Item name is required.", "error")
            return render_template("new_request.html", departments=departments)

        try:
            quantity = int(qty_value)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a positive number.", "error")
            return render_template("new_request.html", departments=departments)

        try:
            dept_id = int(dept_id_str) if dept_id_str else None
        except ValueError:
            dept_id = None

        if not dept_id:
            dept_id = get_user_department_id(session["user_id"])

        r = PurchaseRequest(
            item_name=item_name,
            quantity=quantity,
            created_by=session["user_id"],
            department_id=dept_id,
            request_date=date.today(),
            current_stage="Accounts"
        )
        db.session.add(r)
        db.session.commit()

        log_action(r.request_id, "Creation", "Created", "Success")
        notify_users_by_designation(
            "Accounts Officer",
            "New Purchase Request",
            f"Request #{r.request_id} needs Accounts review.",
            r.request_id
        )
        create_notification_for_user(
            session["user_id"],
            "Request Submitted",
            f"Your request #{r.request_id} has been submitted.",
            r.request_id
        )
        db.session.commit()

        flash("Purchase request submitted.", "success")
        return redirect(url_for("dashboard"))

    return render_template("new_request.html", departments=departments)

def process_approval(rid, expected_stage, next_stage, role_check):
    if session.get("designation") != role_check:
        return "Unauthorized", 403

    r = PurchaseRequest.query.get_or_404(rid)

    if r.current_stage != expected_stage:
        return f"Invalid Stage: Expected {expected_stage}, got {r.current_stage}", 400

    decision = request.form.get("decision", "").strip()
    remark = request.form.get("remark", "").strip()

    allowed_decisions = {"Approved", "Rejected"}
    if expected_stage in {"CAO", "Registrar"}:
        allowed_decisions.add("Discuss")
    if decision not in allowed_decisions:
        return "Invalid decision", 400

    selected_quote = None
    # Purchase Officer must have a Selected quote before forwarding to CAO
    if expected_stage == "Purchase" and decision == "Approved":
        selected_quote = VendorQuote.query.filter_by(
            request_id=r.request_id,
            quote_status="Selected"
        ).first()
        if not selected_quote:
            flash("Please select a vendor quotation before forwarding to CAO.", "error")
            return redirect(url_for("dashboard"))

    # Registrar must also have a Selected quote
    if expected_stage == "Registrar" and decision == "Approved":
        selected_quote = VendorQuote.query.filter_by(
            request_id=r.request_id,
            quote_status="Selected"
        ).first()
        if not selected_quote:
            flash("Select one vendor quotation before Registrar approval.", "error")
            return redirect(url_for("dashboard"))

    status_field = {
        "Accounts": "accounts_status",
        "Audit": "audit_status",
        "Purchase": "purchase_status",
        "CAO": "cao_status",
        "Registrar": "registrar_status",
    }
    setattr(r, status_field[expected_stage], decision)

    if decision == "Approved":
        r.current_stage = next_stage
    elif decision == "Rejected":
        r.current_stage = "Rejected"
    else:
        r.current_stage = expected_stage

    log_action(rid, expected_stage, "Review", decision, remark)

    if decision == "Approved":
        stage_to_designation = {
            "Audit": "Audit Officer",
            "Purchase": "Purchase Officer",
            "CAO": "Chief Accounts Officer",
            "Registrar": "Registrar",
        }
        next_designation = stage_to_designation.get(next_stage)
        if next_designation:
            notify_users_by_designation(
                next_designation,
                "Approval Pending",
                f"Request #{r.request_id} is ready for your review at {next_stage} stage.",
                r.request_id
            )
        if next_stage == "Approved":
            create_notification_for_user(
                r.created_by,
                "Request Approved",
                f"Request #{r.request_id} is fully approved.",
                r.request_id
            )
    elif decision == "Rejected":
        create_notification_for_user(
            r.created_by,
            "Request Rejected",
            f"Request #{r.request_id} was rejected at {expected_stage} stage.",
            r.request_id
        )

    purchase_order = None
    if expected_stage == "Registrar" and decision == "Approved":
        purchase_order = create_or_update_purchase_order(
            purchase_request=r,
            selected_quote=selected_quote,
            created_by_user_id=session["user_id"]
        )
        vendor_performance = VendorPerformance.query.filter_by(
            request_id=r.request_id
        ).first()
        if not vendor_performance:
            db.session.add(
                VendorPerformance(
                    request_id=r.request_id,
                    vendor_id=selected_quote.vendor_id,
                    review_comments="Auto-created at PO stage"
                )
            )
        log_action(
            r.request_id,
            "Purchase Order",
            "Generated",
            purchase_order.po_number,
            f"Vendor: {selected_quote.vendor.name}"
        )

    db.session.commit()

    if purchase_order:
        flash(
            f"Request approved. Purchase Order {purchase_order.po_number} generated.",
            "success"
        )
        return build_purchase_order_pdf_response(purchase_order)

    flash(f"Request {decision.lower()} at {expected_stage} stage.", "success")
    return redirect(url_for("dashboard"))

@app.post("/approve/accounts/<int:rid>")
@login_required
def approve_accounts(rid):
    return process_approval(rid, "Accounts", "Audit", "Accounts Officer")

@app.post("/approve/audit/<int:rid>")
@login_required
def approve_audit(rid):
    return process_approval(rid, "Audit", "Purchase", "Audit Officer")

@app.post("/approve/purchase/<int:rid>")
@login_required
def approve_purchase(rid):
    return process_approval(rid, "Purchase", "CAO", "Purchase Officer")


@app.post("/purchase/select-quote/<int:rid>")
@login_required
def purchase_select_quote(rid):
    """Allow Purchase Officer to select a vendor quotation from the dashboard."""
    if session.get("designation") != "Purchase Officer":
        return "Unauthorized", 403

    r = PurchaseRequest.query.get_or_404(rid)
    if r.current_stage != "Purchase":
        flash("Request is not at Purchase stage.", "error")
        return redirect(url_for("dashboard"))

    quote_id_str = request.form.get("quote_id", "").strip()
    try:
        quote_id = int(quote_id_str)
    except ValueError:
        flash("Invalid quotation selected.", "error")
        return redirect(url_for("dashboard"))

    quote = VendorQuote.query.filter_by(
        quote_id=quote_id,
        request_id=rid
    ).first()
    if not quote:
        flash("Quotation not found for this request.", "error")
        return redirect(url_for("dashboard"))

    # Deselect any previously selected quote for this request
    VendorQuote.query.filter(
        VendorQuote.request_id == rid,
        VendorQuote.quote_status == "Selected"
    ).update({"quote_status": "Submitted"})

    quote.quote_status = "Selected"
    r.purchase_status = "Negotiation"

    log_action(
        rid,
        "Purchase",
        "Quote Selected",
        "Selected",
        f"Vendor: {quote.vendor.name} | Quote #: {quote.quote_id}"
    )
    db.session.commit()
    flash(f"Quotation #{quote.quote_id} from {quote.vendor.name} selected.", "success")
    return redirect(url_for("dashboard"))

@app.post("/approve/cao/<int:rid>")
@login_required
def approve_cao(rid):
    return process_approval(rid, "CAO", "Registrar", "Chief Accounts Officer")

@app.post("/approve/registrar/<int:rid>")
@login_required
def approve_registrar(rid):
    return process_approval(rid, "Registrar", "Approved", "Registrar")


@app.post("/director/update/<int:rid>")
@login_required
def director_update(rid):
    if session.get("designation") != "Director":
        return "Unauthorized", 403

    priority = request.form.get("priority", "")
    if priority not in {"Low", "Medium", "High"}:
        return "Invalid priority", 400

    r = PurchaseRequest.query.get_or_404(rid)
    comments = request.form.get("comments", "").strip()
    r.priority = priority
    r.comments = comments or None

    log_action(rid, "Director", "Priority Update", priority, comments)
    db.session.commit()
    flash("Request priority updated.", "success")
    return redirect(url_for("dashboard"))


# -------------------------------------------------
# VENDOR MANAGEMENT
# -------------------------------------------------
@app.route("/vendors")
@login_required
def list_vendors():
    if not can_manage_vendors():
        return "Unauthorized", 403

    vendors = Vendor.query.order_by(Vendor.name.asc()).all()
    return render_template("vendors.html", vendors=vendors)


@app.route("/vendors/add", methods=["GET", "POST"])
@login_required
def add_vendor():
    if not can_manage_vendors():
        return "Unauthorized", 403

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        contact_person = request.form.get("contact_person", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        gst_no = request.form.get("gst_no", "").strip().upper()
        category = request.form.get("category", "").strip()

        if not all([name, contact_person, email, phone, address, gst_no, category]):
            flash("All vendor fields are required.", "error")
            return render_template("add_vendor.html")

        existing_vendor = Vendor.query.filter_by(name=name).first()
        if existing_vendor:
            flash("Vendor with this name already exists.", "error")
            return render_template("add_vendor.html")

        db.session.add(
            Vendor(
                name=name,
                contact_person=contact_person,
                email=email,
                phone=phone,
                address=address,
                gst_no=gst_no,
                category=category,
                status="Active"
            )
        )
        db.session.commit()
        flash("Vendor added successfully.", "success")
        return redirect(url_for("list_vendors"))

    return render_template("add_vendor.html")


@app.route("/add_vendor")
@login_required
def add_vendor_legacy():
    return redirect(url_for("add_vendor"))


@app.post("/vendors/<int:vendor_id>/status")
@login_required
def update_vendor_status(vendor_id):
    if not can_manage_vendors():
        return "Unauthorized", 403

    status = request.form.get("status", "")
    if status not in {"Active", "Pending", "Blacklisted"}:
        return "Invalid status", 400

    vendor = Vendor.query.get_or_404(vendor_id)
    vendor.status = status
    db.session.commit()
    flash(f"Vendor status updated to {status}.", "success")
    return redirect(url_for("list_vendors"))


@app.route("/vendors/quotes", methods=["GET", "POST"])
@login_required
def manage_vendor_quotes():
    if not can_manage_vendors():
        return "Unauthorized", 403

    if request.method == "POST":
        request_id_value = request.form.get("request_id", "").strip()
        vendor_id_value = request.form.get("vendor_id", "").strip()
        amount_value = request.form.get("quoted_amount", "").strip()
        tax_percent_value = request.form.get("tax_percent", "").strip()
        delivery_days_value = request.form.get("delivery_days", "").strip()
        notes = request.form.get("notes", "").strip()

        try:
            request_id = int(request_id_value)
            vendor_id = int(vendor_id_value)
            delivery_days = int(delivery_days_value)
            if delivery_days <= 0:
                raise ValueError
        except ValueError:
            flash("Request, vendor, and delivery days must be valid values.", "error")
            return redirect(url_for("manage_vendor_quotes"))

        try:
            quoted_amount = Decimal(amount_value)
            if quoted_amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash("Quoted amount must be a positive number.", "error")
            return redirect(url_for("manage_vendor_quotes"))

        try:
            tax_percent = Decimal(tax_percent_value)
            if tax_percent < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash("Tax percent must be zero or positive.", "error")
            return redirect(url_for("manage_vendor_quotes"))

        purchase_request = PurchaseRequest.query.get_or_404(request_id)
        vendor = Vendor.query.get_or_404(vendor_id)

        if purchase_request.current_stage == "Rejected":
            flash("Cannot add quotation for rejected request.", "error")
            return redirect(url_for("manage_vendor_quotes"))

        if vendor.status == "Blacklisted":
            flash("Blacklisted vendor cannot submit quotation.", "error")
            return redirect(url_for("manage_vendor_quotes"))

        quote = VendorQuote.query.filter_by(
            request_id=request_id,
            vendor_id=vendor_id
        ).first()

        if quote:
            quote.quoted_amount = quoted_amount
            quote.tax_percent = tax_percent
            quote.delivery_days = delivery_days
            quote.notes = notes or None
            decision = "Updated"
        else:
            quote = VendorQuote(
                request_id=request_id,
                vendor_id=vendor_id,
                quoted_amount=quoted_amount,
                tax_percent=tax_percent,
                delivery_days=delivery_days,
                notes=notes or None,
                quote_status="Submitted"
            )
            db.session.add(quote)
            decision = "Added"

        if (
            purchase_request.current_stage == "Purchase" and
            purchase_request.purchase_status == "Pending"
        ):
            purchase_request.purchase_status = "Negotiation"

        log_action(
            request_id,
            "Purchase",
            "Vendor Quote",
            decision,
            f"{vendor.name} | Amount: {quoted_amount}"
        )
        db.session.commit()
        flash(f"Vendor quotation {decision.lower()} successfully.", "success")
        return redirect(url_for("manage_vendor_quotes"))

    active_requests = PurchaseRequest.query.filter(
        PurchaseRequest.current_stage != "Rejected"
    ).order_by(PurchaseRequest.request_id.desc()).all()
    vendors = Vendor.query.order_by(Vendor.name.asc()).all()
    quotes = VendorQuote.query.order_by(VendorQuote.created_at.desc()).all()
    return render_template(
        "vendor_quotes.html",
        purchase_requests=active_requests,
        vendors=vendors,
        quotes=quotes
    )


@app.post("/vendors/quotes/<int:quote_id>/status")
@login_required
def update_quote_status(quote_id):
    if not can_manage_vendors():
        return "Unauthorized", 403

    status = request.form.get("quote_status", "")
    if status not in {"Submitted", "Shortlisted", "Selected", "Rejected"}:
        return "Invalid status", 400

    quote = VendorQuote.query.get_or_404(quote_id)
    quote.quote_status = status

    if status == "Selected":
        other_selected_quotes = VendorQuote.query.filter(
            VendorQuote.request_id == quote.request_id,
            VendorQuote.quote_id != quote.quote_id,
            VendorQuote.quote_status == "Selected"
        ).all()
        for other_quote in other_selected_quotes:
            other_quote.quote_status = "Rejected"

        if quote.request.current_stage == "Purchase":
            quote.request.purchase_status = "Negotiation"
        # NOTE: PO is only generated when Registrar approves — not here.

    log_action(
        quote.request_id,
        "Purchase",
        "Quote Decision",
        status,
        f"Vendor: {quote.vendor.name}"
    )
    db.session.commit()
    flash(f"Quotation marked as {status}.", "success")
    return redirect(url_for("manage_vendor_quotes"))


@app.route("/admin/reports")
@login_required
def admin_reports():
    if session.get("role") != "Admin":
        return "Unauthorized", 403

    budgets = db.session.query(
        BudgetAllocation,
        Department.department_code,
        Department.department_name
    ).join(
        Department,
        Department.department_id == BudgetAllocation.department_id
    ).order_by(
        Department.department_code.asc()
    ).all()

    payments = db.session.query(
        PaymentTransaction,
        PurchaseOrder.po_number,
        Vendor.name
    ).join(
        PurchaseOrder, PurchaseOrder.po_id == PaymentTransaction.po_id
    ).join(
        Vendor, Vendor.vendor_id == PurchaseOrder.vendor_id
    ).order_by(
        PaymentTransaction.created_at.desc()
    ).all()

    performance_rows = db.session.query(
        VendorPerformance,
        PurchaseRequest.item_name,
        Vendor.name
    ).join(
        PurchaseRequest,
        PurchaseRequest.request_id == VendorPerformance.request_id
    ).join(
        Vendor,
        Vendor.vendor_id == VendorPerformance.vendor_id
    ).order_by(
        VendorPerformance.performance_id.desc()
    ).all()

    unread_notifications = Notification.query.filter_by(is_read=False).count()
    total_notifications = Notification.query.count()

    return render_template(
        "admin_reports.html",
        budgets=budgets,
        payments=payments,
        performance_rows=performance_rows,
        unread_notifications=unread_notifications,
        total_notifications=total_notifications
    )


@app.post("/payments/<int:payment_id>/status")
@login_required
def update_payment_status(payment_id):
    if session.get("role") != "Admin":
        return "Unauthorized", 403

    payment = PaymentTransaction.query.get_or_404(payment_id)
    payment_status = request.form.get("payment_status", "")
    payment_mode = request.form.get("payment_mode", "")
    remarks = request.form.get("remarks", "").strip()

    if payment_status not in {"Pending", "Processing", "Paid", "Failed"}:
        return "Invalid payment status", 400
    if payment_mode not in {"NEFT", "RTGS", "UPI", "CHEQUE", "CASH"}:
        return "Invalid payment mode", 400

    payment.payment_status = payment_status
    payment.payment_mode = payment_mode
    payment.remarks = remarks or payment.remarks
    if payment_status == "Paid":
        payment.payment_date = date.today()

    db.session.commit()
    flash("Payment transaction updated.", "success")
    return redirect(url_for("admin_reports"))


@app.post("/performance/<int:performance_id>/update")
@login_required
def update_vendor_performance(performance_id):
    if session.get("designation") not in {"Director", "Admin"} and session.get("role") != "Admin":
        return "Unauthorized", 403

    performance = VendorPerformance.query.get_or_404(performance_id)

    def parse_score(field_name):
        value = request.form.get(field_name, "").strip()
        try:
            score = int(value)
        except ValueError:
            raise ValueError(f"Invalid {field_name}")
        if score < 1 or score > 10:
            raise ValueError(f"{field_name} should be between 1 and 10")
        return score

    try:
        quality_score = parse_score("quality_score")
        delivery_score = parse_score("delivery_score")
        support_score = parse_score("support_score")
    except ValueError as err:
        flash(str(err), "error")
        return redirect(url_for("admin_reports"))

    performance.quality_score = quality_score
    performance.delivery_score = delivery_score
    performance.support_score = support_score
    performance.overall_rating = int(round(
        (quality_score + delivery_score + support_score) / 3
    ))
    performance.review_comments = request.form.get("review_comments", "").strip() or None
    performance.reviewed_by = session.get("user_id")
    performance.reviewed_on = date.today()

    db.session.commit()
    flash("Vendor performance updated.", "success")
    return redirect(url_for("admin_reports"))


@app.route("/notifications/mark-all-read")
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=session.get("user_id"), is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("dashboard"))


@app.route("/po/<int:rid>/download")
@login_required
def download_purchase_order(rid):
    allowed_designations = {"Registrar", "Director", "HoD"}
    if (
        session.get("role") != "Admin" and
        session.get("designation") not in allowed_designations
    ):
        return "Unauthorized: Only Registrar, Director, or HoD may download Purchase Orders.", 403

    purchase_order = PurchaseOrder.query.filter_by(request_id=rid).first()
    if not purchase_order:
        flash("Purchase Order not generated yet for this request.", "error")
        return redirect(url_for("dashboard"))

    return build_purchase_order_pdf_response(purchase_order)


@app.route("/vendor-offer/<int:rid>/download")
@login_required
def download_vendor_offer_pdf(rid):
    purchase_request = PurchaseRequest.query.get_or_404(rid)
    if not can_access_request_data(purchase_request):
        return "Unauthorized", 403

    selected_quote = VendorQuote.query.filter_by(
        request_id=rid,
        quote_status="Selected"
    ).first()
    if not selected_quote:
        flash("Selected vendor quotation not available yet.", "error")
        return redirect(url_for("dashboard"))

    return build_vendor_offer_pdf_response(purchase_request, selected_quote)


def get_request_log_summary(request_id):
    logs = (
        RequestLog.query.filter_by(request_id=request_id)
        .order_by(RequestLog.timestamp.asc())
        .all()
    )
    if not logs:
        return ""

    summary_items = []
    for log in logs:
        timestamp_text = (
            log.timestamp.strftime("%Y-%m-%d %H:%M")
            if log.timestamp else ""
        )
        comments_text = (log.comments or "").strip()
        message = f"{timestamp_text} | {log.stage} | {log.action}"
        if comments_text:
            message += f" | {comments_text}"
        summary_items.append(message)
    return " || ".join(summary_items)



@app.route("/track/<int:rid>")
@login_required
def track_request(rid):
    r = PurchaseRequest.query.get_or_404(rid)
    if not can_access_request_data(r):
        return "Unauthorized", 403

    logs = RequestLog.query.filter_by(request_id=rid).order_by(RequestLog.timestamp.desc()).all()
    purchase_order = PurchaseOrder.query.filter_by(request_id=rid).first()
    selected_quote = VendorQuote.query.filter_by(
        request_id=rid,
        quote_status="Selected"
    ).first()
    return render_template(
        "track.html",
        r=r,
        logs=logs,
        po=purchase_order,
        selected_quote=selected_quote
    )

# -------------------------------------------------
# EXPORTS
# -------------------------------------------------
@app.route("/export/csv")
@login_required
def export_csv():
    if session.get("role") != "Admin":
        return "Unauthorized", 403

    # Pre-fetch ALL data inside the request/app context so the generator
    # doesn't need to make DB calls after Flask closes the context.
    reqs = PurchaseRequest.query.order_by(PurchaseRequest.request_id.asc()).all()
    rows = []
    for r in reqs:
        created_by_user = db.session.get(User, r.created_by)
        department = db.session.get(Department, r.department_id)
        selected_quote = VendorQuote.query.filter_by(
            request_id=r.request_id,
            quote_status="Selected"
        ).first()
        purchase_order = PurchaseOrder.query.filter_by(
            request_id=r.request_id
        ).first()
        payment = PaymentTransaction.query.filter_by(
            po_id=purchase_order.po_id
        ).first() if purchase_order else None
        performance = VendorPerformance.query.filter_by(
            request_id=r.request_id
        ).first()
        log_summary = get_request_log_summary(r.request_id)

        rows.append([
            r.request_id,
            r.request_date,
            created_by_user.username if created_by_user else "",
            department.department_name if department else "",
            r.item_name,
            selected_quote.notes if selected_quote and selected_quote.notes else r.item_name,
            r.quantity,
            r.current_stage,
            r.accounts_status,
            r.audit_status,
            r.purchase_status,
            r.cao_status,
            r.registrar_status,
            r.priority,
            selected_quote.vendor.name if selected_quote else "",
            selected_quote.vendor.address if selected_quote else "",
            selected_quote.vendor.gst_no if selected_quote else "",
            f"{selected_quote.quoted_amount:.2f}" if selected_quote else "",
            f"{selected_quote.tax_percent:.2f}" if selected_quote else "",
            selected_quote.quote_status if selected_quote else "",
            purchase_order.po_number if purchase_order else "",
            purchase_order.po_date if purchase_order else "",
            f"{purchase_order.subtotal:.2f}" if purchase_order else "",
            f"{purchase_order.tax_amount:.2f}" if purchase_order else "",
            f"{purchase_order.total_amount:.2f}" if purchase_order else "",
            payment.payment_status if payment else "",
            payment.payment_mode if payment else "",
            performance.overall_rating if performance and performance.overall_rating else "",
            r.comments or "",
            log_summary,
        ])

    def generate():
        stream = StringIO()
        csv_writer = writer(stream)
        csv_writer.writerow([
            "Request ID", "Request Date", "Created By", "Department",
            "Item Name", "Description", "Quantity", "Current Stage",
            "Accounts", "Audit", "Purchase", "CAO", "Registrar", "Priority",
            "Vendor Name", "Vendor Address", "Vendor GST No",
            "Quote Unit Rate", "Quote Tax %", "Quote Status",
            "PO Number", "PO Date", "PO Subtotal", "PO Tax Amount", "PO Total Amount",
            "Payment Status", "Payment Mode", "Vendor Rating",
            "Director Comments", "Transaction Logs",
        ])
        yield stream.getvalue().encode('utf-8')
        for row in rows:
            stream.seek(0)
            stream.truncate(0)
            csv_writer.writerow(row)
            yield stream.getvalue().encode('utf-8')

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            'attachment; filename="purchase_requests.csv"'
        }
    )


@app.route("/export/pdf")
@login_required
def export_pdf():
    if session.get("role") != "Admin":
        return "Unauthorized", 403

    reqs = PurchaseRequest.query.order_by(PurchaseRequest.request_id.asc()).all()

    pdf = FPDF(orientation="landscape")
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "DBMS Report - Purchase Requests (Authority Statuses)", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    # Define table columns and headers
    col_widths = [15, 25, 45, 12, 25, 23, 23, 23, 23, 23]
    headers = [
        "Req ID",
        "Date",
        "Item Name",
        "Qty",
        "Stage",
        "Accounts",
        "Audit",
        "Purchase",
        "CAO",
        "Registrar"
    ]
    
    row_h = 8
    
    # Table header
    pdf.set_font("Helvetica", "B", 10)
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        pdf.cell(
            w, row_h, h, border=1, align="C",
            new_x="RIGHT" if i < len(headers) - 1 else "LMARGIN",
            new_y="TOP" if i < len(headers) - 1 else "NEXT"
        )
        
    # Table body
    pdf.set_font("Helvetica", "", 9)
    for r in reqs:
        date_str = r.request_date.strftime("%Y-%m-%d") if r.request_date else "-"
        # Truncate item name if too long to avoid line breaks ruining the strict cell height (or use multi_cell, but cell is easier for tight rows)
        item_name = (r.item_name[:25] + '...') if len(r.item_name) > 28 else r.item_name
        
        cells = [
            (f"#{r.request_id}", col_widths[0], "C"),
            (date_str, col_widths[1], "C"),
            (item_name, col_widths[2], "L"),
            (str(r.quantity), col_widths[3], "C"),
            (r.current_stage, col_widths[4], "C"),
            (r.accounts_status, col_widths[5], "C"),
            (r.audit_status, col_widths[6], "C"),
            (r.purchase_status, col_widths[7], "C"),
            (r.cao_status, col_widths[8], "C"),
            (r.registrar_status, col_widths[9], "C"),
        ]
        
        # Draw a row
        max_h = row_h # If we want to support multiline we query string width, but keeping it fixed is cleaner for large tables.
        for i, (txt, w, align) in enumerate(cells):
            pdf.cell(
                w, max_h, txt, border=1, align=align,
                new_x="RIGHT" if i < len(cells) - 1 else "LMARGIN",
                new_y="TOP" if i < len(cells) - 1 else "NEXT"
            )

    pdf_data = bytes(pdf.output())


    response = Response(pdf_data)
    response.headers["Content-Type"] = "application/pdf"
    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=purchase_requests.pdf"
    return response


if __name__ == "__main__":
    with app.app_context():
        bootstrap_data()
    app.run(debug=True)
