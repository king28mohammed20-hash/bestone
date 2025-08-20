import os
import uuid
import re
from datetime import datetime, date, time as dtime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required, logout_user, current_user
)
import warnings
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField, SelectField,
    DateField, DecimalField, IntegerField, BooleanField, FileField
)
from wtforms.validators import (
    DataRequired, Length, NumberRange, EqualTo, Optional, URL, ValidationError, Regexp
)
from werkzeug.security import generate_password_hash, check_password_hash

# =========================================
# App / Config
# =========================================
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
warnings.filterwarnings("ignore", message="Using the in-memory storage")

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# إعدادات قاعدة البيانات
if os.environ.get('DATABASE_URL'):
    # للإنتاج - PostgreSQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://')
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    # للتطوير - SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Uploads
UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
THUMB_FOLDER = os.path.join(UPLOAD_FOLDER, "thumbs")
os.makedirs(THUMB_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB

# Business hours
OPEN_HOUR = 13
CLOSE_HOUR = 22
STEP_MINUTES = int(os.environ.get("STEP_MINUTES", "30"))
CURRENCY_LABEL = os.environ.get("CURRENCY_LABEL", "ريال")

# Closed days (env): CLOSED_WEEKDAYS="5,6" / CLOSED_DATES="2025-08-15,2025-08-20"
# Closed days (env): CLOSED_WEEKDAYS="4" (4=الجمعة) / CLOSED_DATES="2025-08-15,2025-08-20"
CLOSED_WEEKDAYS = set(
    int(x) for x in os.environ.get("CLOSED_WEEKDAYS", "4").split(",") if x.strip().isdigit()
)  # الافتراضي: الجمعة
CLOSED_DATES = set(s.strip() for s in os.environ.get("CLOSED_DATES", "").split(",") if s.strip())

# Video helpers
ALLOWED_VIDEO_EXTS = {"mp4"}
VIDEO_FOLDER = os.path.join(app.static_folder, "uploads", "videos")
os.makedirs(VIDEO_FOLDER, exist_ok=True)

# DB / Login
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# =========================================
# Helper Functions
# =========================================
def clean_phone_number(phone_str):
    """تنظيف وتوحيد صيغة رقم الهاتف"""
    if not phone_str:
        return ""
    
    # إزالة كل شيء عدا الأرقام والعلامة +
    cleaned = ''.join(c for c in phone_str if c.isdigit() or c == '+')
    
    # إذا بدأ بـ 0، تحويل للرقم السعودي
    if cleaned.startswith('0'):
        cleaned = '+966' + cleaned[1:]
    # إذا لم يبدأ بـ +، إضافة رمز السعودية
    elif not cleaned.startswith('+') and len(cleaned) >= 9:
        cleaned = '+966' + cleaned
    
    return cleaned

def validate_saudi_phone(phone):
    """التحقق من صحة رقم الهاتف السعودي"""
    clean = clean_phone_number(phone)
    
    # يجب أن يبدأ بـ +966 ويكون طوله 13 رقم
    if not clean.startswith('+966'):
        return False, "رقم الهاتف يجب أن يبدأ بـ +966"
    
    if len(clean) != 13:
        return False, "رقم الهاتف السعودي يجب أن يكون 13 رقم (مع +966)"
    
    # التحقق من أن الرقم يبدأ بـ 5 (موبايل)
    if clean[4:5] == '5':
        return True, "رقم صحيح"
    
    return False, "أرقام الجوال السعودي تبدأ بـ 5"

# =========================================
# Jinja filters
# =========================================
def currency(value):
    try:
        return f"{float(value):.2f} {CURRENCY_LABEL}"
    except Exception:
        return f"{value} {CURRENCY_LABEL}"

app.jinja_env.filters["currency"] = currency

# =========================================
# Helpers
# =========================================
def time_slots(step_minutes: int | None = None):
    if step_minutes is None:
        step_minutes = STEP_MINUTES
    slots = []
    for h in range(OPEN_HOUR, CLOSE_HOUR):
        m = 0
        while m < 60:
            if h == CLOSE_HOUR - 1 and m > 30:
                break
            slots.append(f"{h:02d}:{m:02d}")
            m += step_minutes
    return slots

def compose_datetime(d: date, t_str: str) -> datetime:
    h, m = map(int, t_str.split(":"))
    return datetime.combine(d, dtime(hour=h, minute=m))

def within_business_hours(dt: datetime) -> bool:
    return (OPEN_HOUR <= dt.hour < CLOSE_HOUR) and not (
        dt.hour == CLOSE_HOUR - 1 and dt.minute > 30
    )

def is_closed_day(d: date) -> bool:
    """التحقق من أيام الإغلاق"""
    
    # 1. التحقق من التواريخ المحددة يدوياً
    if str(d) in CLOSED_DATES:
        return True
    
    # 2. التحقق من أيام الأسبوع المغلقة
    if d.weekday() in CLOSED_WEEKDAYS:
        return True
    
    # 3. منع الجمعة (weekday = 4 للجمعة)
    if d.weekday() == 4:  # الجمعة
        return True
    
    return False


def is_conflicting(service_id: int, when_dt: datetime) -> bool:
    q = db.select(Booking).where(
        Booking.service_id == service_id,
        Booking.appointment_at == when_dt,
        Booking.status.in_(["pending", "approved"]),
    )
    return db.session.scalar(q) is not None

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_video(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTS

def save_image(file_storage, prefix="img"):
    """Save image as letterboxed contain (1000x500) + thumb (400x200), keeping full image."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("صيغة الصورة غير مسموحة. المسموح: jpg, jpeg, png")

    unique = f"{prefix}-" + uuid.uuid4().hex[:10] + ".jpg"
    abs_path = os.path.join(UPLOAD_FOLDER, unique)
    file_storage.save(abs_path)

    from PIL import Image, ImageOps

    BOX_W, BOX_H = 1000, 500
    TH_W, TH_H = 400, 200

    with Image.open(abs_path) as im:
        im = im.convert("RGB")

        # Main
        im_fit = ImageOps.contain(im, (BOX_W, BOX_H), Image.LANCZOS)
        canvas = Image.new("RGB", (BOX_W, BOX_H), (255, 255, 255))
        x = (BOX_W - im_fit.width) // 2
        y = (BOX_H - im_fit.height) // 2
        canvas.paste(im_fit, (x, y))
        canvas.save(abs_path, format="JPEG", quality=85, optimize=True)

        # Thumb
        thumb_path = os.path.join(THUMB_FOLDER, unique)
        th_fit = ImageOps.contain(im, (TH_W, TH_H), Image.LANCZOS)
        th_canvas = Image.new("RGB", (TH_W, TH_H), (255, 255, 255))
        tx = (TH_W - th_fit.width) // 2
        ty = (TH_H - th_fit.height) // 2
        th_canvas.paste(th_fit, (tx, ty))
        th_canvas.save(thumb_path, format="JPEG", quality=80, optimize=True)

    return f"uploads/{unique}"

def save_video_file(file_storage, prefix="vid"):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_video(file_storage.filename):
        raise ValueError("صيغة الفيديو غير مسموحة. المسموح: mp4")
    unique = f"{prefix}-" + uuid.uuid4().hex[:10] + ".mp4"
    abs_path = os.path.join(VIDEO_FOLDER, unique)
    file_storage.save(abs_path)
    return f"uploads/videos/{unique}"

def delete_image(rel_path: str):
    if not rel_path:
        return
    abs_path = os.path.join(app.static_folder, rel_path.replace("/", os.sep))
    thumb_path = os.path.join(app.static_folder, "uploads", "thumbs", os.path.basename(rel_path))
    for p in (abs_path, thumb_path):
        try:
            if os.path.isfile(p):
                os.remove(p)
        except Exception:
            pass

def _service_choices():
    services = db.session.scalars(db.select(Service).order_by(Service.name)).all()
    return [(0, "بدون")] + [(s.id, s.name) for s in services]

def admin_required():
    if not (current_user.is_authenticated and current_user.is_admin):
        abort(403)

# =========================================
# YouTube helpers
# =========================================
_YT_PATTERNS = [
    r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:\?|&|$)",
    r"youtu\.be\/([0-9A-Za-z_-]{11})",
]

def parse_youtube_id(url: str) -> str | None:
    if not url: 
        return None
    for pattern in _YT_PATTERNS:
        m = re.search(pattern, url)
        if m: 
            return m.group(1)
    return None

# =========================================
# Models
# =========================================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    # حقول إدارة المستخدمين الجديدة
    is_active = db.Column(db.Boolean, default=True)  # نشط/محظور
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)  # ملاحظات إدارية
    
    def set_password(self, raw): 
        self.password_hash = generate_password_hash(raw)
    
    def check_password(self, raw): 
        return check_password_hash(self.password_hash, raw)
    
    def get_bookings_count(self):
        """عدد الحجوزات"""
        return db.session.scalar(
            db.select(db.func.count(Booking.id)).where(Booking.user_id == self.id)
        ) or 0
    
    def get_last_booking(self):
        """آخر حجز"""
        return db.session.scalar(
            db.select(Booking).where(Booking.user_id == self.id)
            .order_by(Booking.appointment_at.desc())
        )

# نموذج تعديل المستخدم
class UserEditForm(FlaskForm):
    full_name = StringField("الاسم الكامل", validators=[DataRequired(), Length(min=2, max=120)])
    phone = StringField("رقم الهاتف", validators=[DataRequired()])
    is_active = BooleanField("نشط", default=True)
    is_admin = BooleanField("مدير", default=False)
    notes = TextAreaField("ملاحظات إدارية", validators=[Optional(), Length(max=500)])
    submit = SubmitField("حفظ التعديلات")

# نموذج إضافة مستخدم جديد
class UserCreateForm(FlaskForm):
    full_name = StringField("الاسم الكامل", validators=[DataRequired(), Length(min=2, max=120)])
    phone = StringField("رقم الهاتف", validators=[DataRequired()])
    password = PasswordField("كلمة المرور", validators=[DataRequired(), Length(min=6)])
    is_admin = BooleanField("مدير", default=False)
    notes = TextAreaField("ملاحظات إدارية", validators=[Optional(), Length(max=500)])
    submit = SubmitField("إضافة المستخدم")
    
    def validate_phone(self, field):
        clean_phone = clean_phone_number(field.data)
        existing = db.session.scalar(db.select(User).where(User.phone == clean_phone))
        if existing:
            raise ValidationError("هذا الرقم مسجّل مسبقاً")


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False, default=0)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    active = db.Column(db.Boolean, default=True)
    image_path = db.Column(db.String(255), nullable=True)
    
    # حقل واحد للتقسيط
    installment_available = db.Column(db.Boolean, default=False)  # إمكانية التقسيط

class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10,2), nullable=True)
    active = db.Column(db.Boolean, default=True)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), nullable=True)
    service = db.relationship("Service")
    image_path = db.Column(db.String(255), nullable=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), nullable=False)
    appointment_at = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    notes = db.Column(db.Text, nullable=True)
    car_info_id = db.Column(db.Integer, db.ForeignKey("car_info.id"), nullable=True)
    user = db.relationship("User")
    service = db.relationship("Service")
    car_info = db.relationship("CarInfo")

class ContactInfo(db.Model):
    __tablename__ = "contact_info"
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50))
    whatsapp = db.Column(db.String(50))
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    location_url = db.Column(db.String(512))
    map_embed = db.Column(db.Text)
    
    # حقول جديدة للسوشيال ميديا
    snapchat = db.Column(db.String(100))
    instagram = db.Column(db.String(100))
    tiktok = db.Column(db.String(100))

    @staticmethod
    def get_single(create_if_missing=True):
        obj = ContactInfo.query.first()
        if not obj and create_if_missing:
            obj = ContactInfo()
            db.session.add(obj)
            db.session.commit()
        return obj

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(16), nullable=False, default="youtube")
    youtube_id = db.Column(db.String(16), nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    poster_path = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, default=True)
    featured = db.Column(db.Boolean, default=False)
    sort = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===== إضافة جدول معلومات السيارة =====
class CarInfo(db.Model):
    __tablename__ = "car_info"
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)  # نوع السيارة
    model = db.Column(db.String(100), nullable=False)  # الموديل
    year = db.Column(db.Integer, nullable=True)        # السنة (اختياري)
    color = db.Column(db.String(30), nullable=True)    # اللون (اختياري)
    plate_number = db.Column(db.String(20), nullable=True)  # رقم اللوحة (اختياري)
    notes = db.Column(db.Text, nullable=True)          # ملاحظات إضافية
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    user = db.relationship("User", backref="cars")

# ===== تحديث جدول الحجوزات =====
# أضف هذا العمود إلى جدول Booking (بعد العمود الموجود):
    car_info_id = db.Column(db.Integer, db.ForeignKey("car_info.id"), nullable=True)
    car_info = db.relationship("CarInfo")

# في الـ Booking class، أضف هذا السطر:
# car_info_id = db.Column(db.Integer, db.ForeignKey("car_info.id"), nullable=True)
# car_info = db.relationship("CarInfo")

# ===== قائمة السيارات الشائعة في السعودية =====
CAR_BRANDS = {
    "Toyota": [
        "كامري", "كورولا", "لاند كروزر", "برادو", "يارس", "RAV4", "هايلكس", 
        "فورتونر", "أفانزا", "هايلاندر", "سي إتش آر", "فينزا"
    ],
    "Hyundai": [
        "النترا", "سوناتا", "أكسنت", "توسان", "كريتا", "فيلوستر", 
        "سانتا في", "أيونيك", "كونا", "باليساد"
    ],
    "Nissan": [
        "ألتيما", "سنترا", "باترول", "إكس تريل", "كيكس", "ماكسيما", 
        "مورانو", "أرمادا", "نافارا", "جوك"
    ],
    "Honda": [
        "أكورد", "سيفيك", "سي آر في", "بايلوت", "أوديسي", "فيت", 
        "هايبرد", "باسبورت", "ريدج لاين"
    ],
    "Kia": [
        "أوبتيما", "ريو", "سيراتو", "سبورتاج", "سورنتو", "كادينزا", 
        "ستينجر", "سيلتوس", "كارنيفال", "إي في 6"
    ],
    "Mercedes": [
        "C-Class", "E-Class", "S-Class", "GLC", "GLE", "GLS", "A-Class", 
        "CLA", "G-Class", "GLB", "GLA"
    ],
    "BMW": [
        "الفئة الثالثة", "الفئة الخامسة", "الفئة السابعة", "X1", "X3", "X5", 
        "X6", "X7", "الفئة الأولى", "الفئة الثانية", "Z4"
    ],
    "Audi": [
        "A3", "A4", "A6", "A8", "Q3", "Q5", "Q7", "Q8", "TT", "A5", "e-tron"
    ],
    "Lexus": [
        "ES", "LS", "IS", "GS", "NX", "RX", "GX", "LX", "LC", "RC", "UX"
    ],
    "Chevrolet": [
        "كروز", "إمبالا", "ماليبو", "كابتيفا", "تاهو", "سوبربان", 
        "إكوينوكس", "ترافيرس", "كمارو", "كورفيت"
    ],
    "Ford": [
        "فيوجن", "فوكس", "مونديو", "إكسبلورر", "إكسبيديشن", "إيدج", 
        "إيكو سبورت", "موستانغ", "F-150", "رينجر"
    ],
    "Mitsubishi": [
        "لانسر", "أوت لاندر", "باجيرو", "إكليبس كروس", "ASX", "L200", 
        "أتراج", "إكسباندر"
    ],
    "Mazda": [
        "3", "6", "CX-3", "CX-5", "CX-9", "MX-5", "CX-30", "2"
    ],
    "Infiniti": [
        "Q50", "Q60", "Q70", "QX50", "QX60", "QX70", "QX80", "Q30"
    ],
    "GMC": [
        "سييرا", "يوكون", "أكاديا", "تيرين", "كانيون", "سافانا"
    ],
    "Cadillac": [
        "CTS", "ATS", "XT5", "XT6", "إسكاليد", "CT6", "XT4"
    ],
    "Jeep": [
        "رانجلر", "جراند شيروكي", "شيروكي", "كومباس", "رينيجيد", "جلادياتور"
    ],
    "Land Rover": [
        "ديسكفري", "رينج روفر", "ديفندر", "إيفوك", "فيلار", "سبورت"
    ],
    "Porsche": [
        "911", "كايان", "ماكان", "بانامرا", "تايكان", "718"
    ],
    "Volkswagen": [
        "جيتا", "باسات", "تيغوان", "أطلس", "جولف", "أرتيون", "بولو"
    ],
    "Subaru": [
        "إمبريزا", "ليغاسي", "فورستر", "أوت باك", "أسنت", "كروس تريك"
    ],
    "Suzuki": [
        "سويفت", "سيليريو", "فيتارا", "جيمني", "بالينو", "إرتيغا"
    ],
    "MINI": [
        "Cooper", "Countryman", "Clubman", "Convertible", "Hardtop"
    ],
    "جيلي": [
        "إمجراند", "كولراي", "أطلس", "توغيلا", "جي سي 6", "بين يو"
    ],
    "شيري": [
        "تيجو", "أريزو", "إكسيد", "تيجو 7", "تيجو 4"
    ],
    "هافال": [
        "H6", "H9", "جوليان", "دارجو", "F7", "H2"
    ],
    "BYD": [
        "تانغ", "سونغ", "هان", "دولفين", "سيل", "أتو 3"
    ]
}

# ===== ألوان السيارات الشائعة =====
CAR_COLORS = [
    "أبيض", "أسود", "فضي", "رمادي", "أحمر", "أزرق", "بني", "ذهبي",
    "أخضر", "بيج", "برتقالي", "وردي", "بنفسجي", "أصفر", "كحلي"
]

# ===== سنوات الصنع =====
def get_car_years():
    """إرجاع قائمة سنوات الصنع من 2000 إلى السنة الحالية + 1"""
    current_year = datetime.now().year
    return list(range(current_year + 1, 1999, -1))  # من السنة القادمة إلى 2000

# ===== تحديث نموذج الحجز =====
class CarBookingForm(FlaskForm):
    # معلومات الخدمة والموعد
    service_id = SelectField("الخدمة", coerce=int, validators=[DataRequired()])
    date = DateField("التاريخ", validators=[DataRequired()], format="%Y-%m-%d")
    time = SelectField("الوقت", choices=[], validators=[DataRequired()])
    
    # معلومات السيارة - مطلوبة
    # استبدل SelectField بـ StringField للموديل
    car_brand = SelectField("نوع السيارة", validators=[DataRequired()], 
                       choices=[('', 'اختر نوع السيارة')] + [(brand, brand) for brand in CAR_BRANDS.keys()])

    car_model = StringField("الموديل", validators=[DataRequired()], 
                       render_kw={
                           "list": "carModelsList", 
                           "placeholder": "اختر أو اكتب الموديل",
                           "autocomplete": "off"
                       })
    
    # معلومات السيارة - اختيارية
    car_year = SelectField("سنة الصنع (اختياري)", validators=[Optional()],
                      choices=[('', 'اختر السنة')] + [(str(year), str(year)) for year in get_car_years()])
    car_color = SelectField("لون السيارة (اختياري)", validators=[Optional()],
                           choices=[('', 'اختر اللون')] + [(color, color) for color in CAR_COLORS])
    plate_number = StringField("رقم اللوحة (اختياري)", validators=[Optional(), Length(max=20)])
    
    # ملاحظات
    notes = TextAreaField("ملاحظات إضافية (اختياري)")
    
    submit = SubmitField("تأكيد الحجز")

# ===== Route للحصول على موديلات السيارة =====
@app.route("/api/car-models/<brand>")
def get_car_models(brand):
    """إرجاع موديلات السيارة حسب النوع"""
    models = CAR_BRANDS.get(brand, [])
    return jsonify(models)

# ===== تحديث route الحجز =====
@app.route("/api/booked-slots/<date>")
@login_required
def get_booked_slots(date):
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        bookings = db.session.scalars(
            db.select(Booking).where(
                db.func.date(Booking.appointment_at) == target_date,
                Booking.status.in_(["pending", "approved"])
            )
        ).all()
        booked_slots = [b.appointment_at.strftime("%H:%M") for b in bookings]
        return jsonify(booked_slots)
    except:
        return jsonify([])

@app.route("/book", methods=["GET","POST"])
@limiter.limit("10 per hour")  # 10 حجوزات كل ساعة
@login_required
def book():
    form = CarBookingForm()
    services = db.session.scalars(
        db.select(Service).where(Service.active == True).order_by(Service.name)
    ).all()
    form.service_id.choices = [(s.id, f"{s.name} — {int(s.duration_minutes)}د") for s in services]
    form.time.choices = [(s, s) for s in time_slots()]

    # Preselect service by ?service_id=
    try:
        pre_id = request.args.get("service_id", type=int)
        if pre_id:
            _s = db.session.get(Service, pre_id)
            if _s and _s.active:
                form.service_id.data = pre_id
    except Exception:
        pass
    booked_slots = []
    selected_date = request.form.get('date') or request.args.get('date')
    if selected_date:
        try:
            target_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            bookings = db.session.scalars(
                db.select(Booking).where(
                    db.func.date(Booking.appointment_at) == target_date,
                    Booking.status.in_(["pending", "approved"])
                )
            ).all()
            booked_slots = [b.appointment_at.strftime("%H:%M") for b in bookings]
        except:
            pass
    if form.validate_on_submit():
        # التحقق من يوم الإغلاق
        if is_closed_day(form.date.data):
            day_name = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"][form.date.data.weekday()]
            if form.date.data.weekday() == 4:  # الجمعة
                flash(f"عذراً، نحن مغلقون يوم الجمعة. اختر يوماً آخر.", "warning")
            elif form.date.data.weekday() in CLOSED_WEEKDAYS:
                flash(f"عذراً، نحن مغلقون يوم {day_name}. اختر يوماً آخر.", "warning")
            else:
                flash("هذا التاريخ ضمن العطل الرسمية. الرجاء اختيار تاريخ آخر.", "warning")
            return render_template("booking_form.html", form=form, booked_slots=booked_slots)

        appt_dt = compose_datetime(form.date.data, form.time.data)
        if appt_dt < datetime.now():
            flash("لا يمكن اختيار وقت في الماضي.", "warning")
            return render_template("booking_form.html", form=form, booked_slots=booked_slots)

        if not within_business_hours(appt_dt):
            flash("الدوام من 1:00 ظهراً إلى 10:00 مساءً (آخر موعد يبدأ 9:30).", "warning")
            return render_template("booking_form.html", form=form, booked_slots=booked_slots)

        if is_conflicting(form.service_id.data, appt_dt):
            flash("هذا الموعد محجوز بالفعل لهذه الخدمة. اختر وقتاً آخر.", "warning")
            return render_template("booking_form.html", form=form, booked_slots=booked_slots)

        # حفظ معلومات السيارة
        car_info = CarInfo(
            brand=form.car_brand.data,
            model=form.car_model.data,
            year=form.car_year.data if form.car_year.data else None,
            color=form.car_color.data if form.car_color.data else None,
            plate_number=form.plate_number.data.strip() if form.plate_number.data else None,
            notes="",  # الملاحظات ستكون في الحجز
            user_id=current_user.id
        )
        db.session.add(car_info)
        db.session.flush()  # للحصول على ID

        # إنشاء الحجز
        b = Booking(
            user_id=current_user.id,
            service_id=form.service_id.data,
            appointment_at=appt_dt,
            notes=form.notes.data or "",
            car_info_id=car_info.id  # ربط معلومات السيارة
        )
        db.session.add(b)
        db.session.commit()
        
        flash("تم إرسال طلب الحجز بنجاح مع معلومات السيارة. بانتظار موافقة الإدارة.", "success")
        return redirect(url_for("my_bookings"))

    return render_template("booking_form.html", form=form, booked_slots=booked_slots)

# ===== إضافة command لتحديث قاعدة البيانات =====
@app.cli.command("add-car-table")
def add_car_table():
    """إضافة جدول معلومات السيارة"""
    # إنشاء الجدول الجديد
    db.create_all()
    
    # إضافة العمود الجديد لجدول الحجوزات
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE booking ADD COLUMN car_info_id INTEGER"))
            conn.commit()
        print("✅ تم إضافة عمود car_info_id إلى جدول booking")
    except Exception as e:
        print(f"⚠️ العمود موجود مسبقاً أو حدث خطأ: {e}")
    
    print("✅ تم إنشاء جدول معلومات السيارة بنجاح!")
    print("🚗 قائمة السيارات تحتوي على:", len(CAR_BRANDS), "نوع سيارة")
    print("🎨 قائمة الألوان تحتوي على:", len(CAR_COLORS), "لون")

# =========================================
# Forms
# =========================================
class RegisterForm(FlaskForm):
    full_name = StringField("الاسم الكامل", validators=[DataRequired(), Length(min=2, max=120)])
    phone = StringField("رقم الهاتف", validators=[DataRequired()])
    password = PasswordField("كلمة المرور", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField("تأكيد كلمة المرور", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("إنشاء حساب")
    
    def validate_phone(self, field):
        """التحقق المخصص من رقم الهاتف"""
        clean_phone = clean_phone_number(field.data)
        is_valid, message = validate_saudi_phone(clean_phone)
        
        if not is_valid:
            raise ValidationError(message)
        
        # التحقق من عدم وجود الرقم مسبقاً
        existing = db.session.scalar(db.select(User).where(User.phone == clean_phone))
        if existing:
            raise ValidationError("هذا الرقم مسجّل مسبقاً")

class LoginForm(FlaskForm):
    phone = StringField("رقم الهاتف", validators=[DataRequired()])
    password = PasswordField("كلمة المرور", validators=[DataRequired()])
    submit = SubmitField("دخول")

class BookingForm(FlaskForm):
    service_id = SelectField("الخدمة", coerce=int, validators=[DataRequired()])
    date = DateField("التاريخ", validators=[DataRequired()], format="%Y-%m-%d")
    time = SelectField("الوقت", choices=[], validators=[DataRequired()])
    notes = TextAreaField("ملاحظات (اختياري)")
    submit = SubmitField("احجز")

class ServiceForm(FlaskForm):
    name = StringField("اسم الخدمة", validators=[DataRequired(), Length(min=2, max=120)])
    price = DecimalField("السعر", validators=[DataRequired(), NumberRange(min=0)], places=2)
    duration_minutes = IntegerField("المدة (دقائق)", validators=[DataRequired(), NumberRange(min=15, max=600)])
    active = BooleanField("مُفَعَّل", default=True)
    image = FileField("صورة الخدمة (jpg/png)")
    
    # خيار التقسيط البسيط
    installment_available = BooleanField("إمكانية التقسيط", default=False)
    
    submit = SubmitField("حفظ")

class OfferForm(FlaskForm):
    title = StringField("عنوان الإعلان", validators=[DataRequired(), Length(min=2, max=160)])
    description = TextAreaField("الوصف")
    price = DecimalField("السعر (اختياري)", places=2)
    service_id = SelectField("يرتبط بخدمة (اختياري)", coerce=int, choices=[(0, "بدون")])
    active = BooleanField("مُفَعَّل", default=True)
    image = FileField("صورة الإعلان (jpg/png)")
    submit = SubmitField("حفظ")

class VideoForm(FlaskForm):
    title = StringField("العنوان", validators=[DataRequired(), Length(min=2, max=160)])
    description = TextAreaField("الوصف", validators=[Optional(), Length(max=2000)])
    source = SelectField("المصدر", choices=[("youtube","يوتيوب"), ("mp4","رفع ملف MP4")])
    youtube_url = StringField("رابط يوتيوب", validators=[Optional(), URL()])
    video_file = FileField("ملف الفيديو (MP4)")
    poster = FileField("صورة غلاف (اختياري)")
    active = BooleanField("فعّال", default=True)
    featured = BooleanField("مميّز", default=False)
    sort = IntegerField("الترتيب (أصغر يظهر أولاً)", validators=[Optional()], default=0)
    submit = SubmitField("حفظ")

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("كلمة المرور الحالية", validators=[DataRequired()])
    new_password = PasswordField("كلمة المرور الجديدة", validators=[DataRequired(), Length(min=8, message="8 أحرف على الأقل")])
    confirm = PasswordField("تأكيد كلمة المرور الجديدة", validators=[DataRequired(), EqualTo("new_password", message="غير متطابقة")])
    submit = SubmitField("تحديث كلمة المرور")

class ContactForm(FlaskForm):
    phone = StringField("الهاتف", validators=[Optional(), Length(max=50)])
    whatsapp = StringField("واتساب", validators=[Optional(), Length(max=50)])
    email = StringField("الإيميل", validators=[Optional(), Length(max=120)])
    address = StringField("العنوان", validators=[Optional(), Length(max=255)])
    location_url = StringField("رابط الموقع على الخريطة", validators=[Optional(), URL(), Length(max=512)])
    map_embed = TextAreaField("كود الخريطة (iframe اختياري)", validators=[Optional(), Length(max=5000)])
    
    # حقول السوشيال ميديا الجديدة
    snapchat = StringField("اسم المستخدم في سناب شات", validators=[Optional(), Length(max=100)])
    instagram = StringField("اسم المستخدم في انستغرام", validators=[Optional(), Length(max=100)])
    tiktok = StringField("اسم المستخدم في تيك توك", validators=[Optional(), Length(max=100)])
    
    submit = SubmitField("حفظ")

# =========================================
# Login manager
# =========================================
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def inject_contact():
    try:
        c = ContactInfo.get_single(create_if_missing=True)
    except Exception:
        c = None
    return dict(contact_global=c)

# =========================================
# Routes
# =========================================
@app.route("/")
def index():
    services = db.session.scalars(
        db.select(Service).where(Service.active == True).order_by(Service.name)
    ).all()
    offers = db.session.scalars(
        db.select(Offer).where(Offer.active == True).order_by(Offer.id.desc())
    ).all()
    return render_template("index.html", services=services, offers=offers)

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegisterForm()
    if form.validate_on_submit():
        # تنظيف رقم الهاتف
        clean_phone = clean_phone_number(form.phone.data)
        
        u = User(
            full_name=form.full_name.data.strip(), 
            phone=clean_phone
        )
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        login_user(u)
        flash("تم إنشاء الحساب بنجاح.", "success")
        return redirect(url_for("index"))
    return render_template("register.html", form=form)

@app.route("/booking/<int:booking_id>/delete", methods=["POST"])
@login_required
def delete_my_booking(booking_id):
    booking = db.session.get(Booking, booking_id) or abort(404)
    
    # التأكد أن الحجز يخص المستخدم الحالي
    if booking.user_id != current_user.id:
        abort(403)
    
    # السماح بالحذف فقط للحجوزات قيد المراجعة
    if booking.status != "pending":
        flash("لا يمكن حذف الحجوزات المؤكدة أو الملغاة. تواصل مع الإدارة.", "warning")
        return redirect(url_for("my_bookings"))
    
    # حذف معلومات السيارة المرتبطة
    if booking.car_info:
        db.session.delete(booking.car_info)
    
    # حذف الحجز
    db.session.delete(booking)
    db.session.commit()
    
    flash("تم حذف الحجز بنجاح.", "success")
    return redirect(url_for("my_bookings"))


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        clean_phone = clean_phone_number(form.phone.data)
        
        u = db.session.scalar(db.select(User).where(User.phone == clean_phone))
        if not u:
            flash("بيانات الدخول غير صحيحة.", "danger")
            return render_template("login.html", form=form)
        
        if not u.is_active:
            flash("حسابك محظور. تواصل مع الإدارة.", "danger")
            return render_template("login.html", form=form)
        
        if not u.check_password(form.password.data):
            flash("بيانات الدخول غير صحيحة.", "danger")
            return render_template("login.html", form=form)
        
        # حفظ وقت آخر تسجيل دخول
        u.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(u)
        flash("أهلاً بك.", "success")
        return redirect(url_for("index"))
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج.", "info")
    return redirect(url_for("index"))



# Routes إدارة المستخدمين
@app.route("/admin/users")
@login_required
def admin_users():
    admin_required()
    
    # فلترة المستخدمين حسب الحالة
    status = request.args.get('status', 'all')
    search = request.args.get('search', '')
    
    query = db.select(User).order_by(User.created_at.desc())
    
    if status == 'active':
        query = query.where(User.is_active == True)
    elif status == 'blocked':
        query = query.where(User.is_active == False)
    elif status == 'admin':
        query = query.where(User.is_admin == True)
    
    if search:
        query = query.where(
            db.or_(
                User.full_name.contains(search),
                User.phone.contains(search)
            )
        )
    
    users = db.session.scalars(query).all()
    
    # إحصائيات
    stats = {
        'total': db.session.scalar(db.select(db.func.count(User.id))),
        'active': db.session.scalar(db.select(db.func.count(User.id)).where(User.is_active == True)),
        'blocked': db.session.scalar(db.select(db.func.count(User.id)).where(User.is_active == False)),
        'admins': db.session.scalar(db.select(db.func.count(User.id)).where(User.is_admin == True))
    }
    
    return render_template("admin_users.html", users=users, stats=stats, 
                         current_status=status, search=search)

@app.route("/admin/users/new", methods=["GET", "POST"])
@login_required
def admin_user_new():
    admin_required()
    form = UserCreateForm()
    
    if form.validate_on_submit():
        clean_phone = clean_phone_number(form.phone.data)
        
        user = User(
            full_name=form.full_name.data.strip(),
            phone=clean_phone,
            is_admin=form.is_admin.data,
            notes=form.notes.data or ""
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f"تم إضافة المستخدم {user.full_name} بنجاح.", "success")
        return redirect(url_for("admin_users"))
    
    return render_template("admin_user_form.html", form=form, is_edit=False)

@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def admin_user_edit(user_id):
    admin_required()
    user = db.session.get(User, user_id) or abort(404)
    
    # منع تعديل المدير الرئيسي لنفسه
    if user.id == current_user.id:
        flash("لا يمكنك تعديل حسابك الخاص من هنا.", "warning")
        return redirect(url_for("admin_users"))
    
    form = UserEditForm(obj=user)
    
    if form.validate_on_submit():
        # التحقق من رقم الهاتف
        clean_phone = clean_phone_number(form.phone.data)
        existing = db.session.scalar(
            db.select(User).where(
                db.and_(User.phone == clean_phone, User.id != user.id)
            )
        )
        if existing:
            flash("رقم الهاتف مستخدم من قبل مستخدم آخر.", "danger")
            return render_template("admin_user_form.html", form=form, is_edit=True, user=user)
        
        user.full_name = form.full_name.data.strip()
        user.phone = clean_phone
        user.is_active = form.is_active.data
        user.is_admin = form.is_admin.data
        user.notes = form.notes.data or ""
        
        db.session.commit()
        flash(f"تم تحديث بيانات {user.full_name}.", "success")
        return redirect(url_for("admin_users"))
    
    return render_template("admin_user_form.html", form=form, is_edit=True, user=user)

@app.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
@login_required
def admin_user_toggle_status(user_id):
    admin_required()
    user = db.session.get(User, user_id) or abort(404)
    
    if user.id == current_user.id:
        flash("لا يمكنك حظر نفسك!", "danger")
        return redirect(url_for("admin_users"))
    
    user.is_active = not user.is_active
    status = "تم تفعيل" if user.is_active else "تم حظر"
    
    db.session.commit()
    flash(f"{status} المستخدم {user.full_name}.", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
def admin_user_delete(user_id):
    admin_required()
    user = db.session.get(User, user_id) or abort(404)
    
    if user.id == current_user.id:
        flash("لا يمكنك حذف حسابك الخاص!", "danger")
        return redirect(url_for("admin_users"))
    
    # حذف حجوزات المستخدم أولاً
    db.session.execute(db.delete(Booking).where(Booking.user_id == user.id))
    
    user_name = user.full_name
    db.session.delete(user)
    db.session.commit()
    
    flash(f"تم حذف المستخدم {user_name} وجميع حجوزاته.", "warning")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
def admin_user_reset_password(user_id):
    admin_required()
    user = db.session.get(User, user_id) or abort(404)
    
    # كلمة مرور افتراضية
    new_password = "123456"
    user.set_password(new_password)
    
    db.session.commit()
    flash(f"تم إعادة تعيين كلمة مرور {user.full_name} إلى: {new_password}", "info")
    return redirect(url_for("admin_users"))

@app.route("/my-bookings")
@login_required
def my_bookings():
    items = db.session.scalars(
        db.select(Booking).where(Booking.user_id == current_user.id).order_by(Booking.appointment_at.desc())
    ).all()
    return render_template("bookings.html", items=items)

# ---------- Admin Routes ----------
@app.route("/admin")
@login_required
def admin_home():
    admin_required()
    pending = db.session.scalars(
        db.select(Booking).where(Booking.status == "pending").order_by(Booking.appointment_at.asc())
    ).all()
    approved = db.session.scalars(
        db.select(Booking).where(Booking.status == "approved").order_by(Booking.appointment_at.asc())
    ).all()
    cancelled = db.session.scalars(
        db.select(Booking).where(Booking.status == "cancelled").order_by(Booking.appointment_at.asc())
    ).all()
    return render_template("admin_home.html", pending=pending, approved=approved, cancelled=cancelled)

@app.route("/admin/approve/<int:booking_id>", methods=["POST"])
@login_required
def admin_approve(booking_id):
    admin_required()
    b = db.session.get(Booking, booking_id) or abort(404)
    b.status = "approved"
    db.session.commit()
    flash("تمت الموافقة على الحجز.", "success")
    return redirect(url_for("admin_home"))

@app.route("/admin/cancel/<int:booking_id>", methods=["POST"])
@login_required
def admin_cancel(booking_id):
    admin_required()
    b = db.session.get(Booking, booking_id) or abort(404)
    b.status = "cancelled"
    db.session.commit()
    flash("تم إلغاء الحجز.", "info")
    return redirect(url_for("admin_home"))

@app.route("/admin/reset/<int:booking_id>", methods=["POST"])
@login_required
def admin_reset(booking_id):
    admin_required()
    b = db.session.get(Booking, booking_id) or abort(404)
    b.status = "pending"
    db.session.commit()
    flash("تمت إعادة الحالة إلى قيد المراجعة.", "info")
    return redirect(url_for("admin_home"))

@app.route("/admin/delete/<int:booking_id>", methods=["POST"])
@login_required
def admin_delete(booking_id):
    admin_required()
    b = db.session.get(Booking, booking_id) or abort(404)
    db.session.delete(b)
    db.session.commit()
    flash("تم حذف الحجز نهائياً.", "warning")
    return redirect(url_for("admin_home"))

# ---------- Admin Services ----------
@app.route("/admin/services")
@login_required
def admin_services():
    admin_required()
    items = db.session.scalars(db.select(Service).order_by(Service.name)).all()
    return render_template("admin_services.html", items=items)

@app.route("/admin/services/new", methods=["GET","POST"])
@login_required
def admin_service_new():
    admin_required()
    form = ServiceForm()
    if form.validate_on_submit():
        s = Service(
            name=form.name.data.strip(),
            price=form.price.data,
            duration_minutes=form.duration_minutes.data,
            active=form.active.data,
            installment_available=form.installment_available.data  # حفظ خيار التقسيط
        )
        
        if "image" in request.files and request.files["image"].filename:
            try:
                rel = save_image(request.files["image"], prefix="service")
                s.image_path = rel
            except Exception as e:
                flash(str(e), "danger")
                return render_template("admin_service_form.html", form=form, is_edit=False)
        
        db.session.add(s)
        db.session.commit()
        flash("تمت إضافة الخدمة.", "success")
        return redirect(url_for("admin_services"))
    return render_template("admin_service_form.html", form=form, is_edit=False)

@app.route("/admin/services/<int:service_id>/edit", methods=["GET","POST"])
@login_required
def admin_service_edit(service_id):
    admin_required()
    s = db.session.get(Service, service_id) or abort(404)
    form = ServiceForm(obj=s)
    
    if form.validate_on_submit():
        s.name = form.name.data.strip()
        s.price = form.price.data
        s.duration_minutes = form.duration_minutes.data
        s.active = form.active.data
        s.installment_available = form.installment_available.data  # تحديث خيار التقسيط
        
        if "image" in request.files and request.files["image"].filename:
            try:
                if s.image_path:
                    delete_image(s.image_path)
                rel = save_image(request.files["image"], prefix="service")
                s.image_path = rel
            except Exception as e:
                flash(str(e), "danger")
                return render_template("admin_service_form.html", form=form, is_edit=True)
        
        db.session.commit()
        flash("تم تعديل الخدمة.", "success")
        return redirect(url_for("admin_services"))
    return render_template("admin_service_form.html", form=form, is_edit=True)

@app.route("/admin/services/<int:service_id>/delete", methods=["POST"])
@login_required
def admin_service_delete(service_id):
    admin_required()
    s = db.session.get(Service, service_id) or abort(404)
    if s.image_path:
        delete_image(s.image_path)
    db.session.delete(s)
    db.session.commit()
    flash("تم حذف الخدمة.", "info")
    return redirect(url_for("admin_services"))

# ---------- Admin Offers ----------
@app.route("/admin/offers")
@login_required
def admin_offers():
    admin_required()
    items = db.session.scalars(db.select(Offer).order_by(Offer.id.desc())).all()
    return render_template("admin_offers.html", items=items)

# استبدل دالة admin_offer_new في app.py بهذا الكود:

@app.route("/admin/offers/new", methods=["GET","POST"])
@login_required
def admin_offer_new():
    admin_required()
    form = OfferForm()
    form.service_id.choices = _service_choices()
    
    if form.validate_on_submit():
        service_id = form.service_id.data or 0
        
        # إنشاء العرض الجديد
        o = Offer(
            title=form.title.data.strip(),
            description=form.description.data or "",
            price=form.price.data if form.price.data is not None else None,
            active=True,  # اجبار التفعيل دائماً للعرض الجديد
            service_id=(service_id if service_id != 0 else None)
        )
        
        # معالجة الصورة (اختياري ومحمي من الأخطاء)
        try:
            if "image" in request.files and request.files["image"].filename:
                file_storage = request.files["image"]
                if file_storage and allowed_file(file_storage.filename):
                    # حفظ الصورة بحجم مناسب
                    unique = f"offer-" + uuid.uuid4().hex[:10] + ".jpg"
                    abs_path = os.path.join(UPLOAD_FOLDER, unique)
                    file_storage.save(abs_path)
                    
                    # معالجة بسيطة للحجم
                    from PIL import Image
                    with Image.open(abs_path) as img:
                        img = img.convert("RGB")
                        # تحديد حجم ثابت للعروض: 800x400
                        img = img.resize((800, 400), Image.LANCZOS)
                        img.save(abs_path, format="JPEG", quality=85)
                    
                    o.image_path = f"uploads/{unique}"
                else:
                    flash("صيغة الصورة غير مدعومة", "warning")
        except Exception as e:
            # في حالة خطأ الصورة، احفظ العرض بدون صورة
            print(f"خطأ في معالجة الصورة: {e}")
            flash("تم حفظ العرض، لكن حدث خطأ في الصورة", "warning")
        
        # حفظ في قاعدة البيانات
        try:
            db.session.add(o)
            db.session.commit()
            flash("تمت إضافة الإعلان بنجاح.", "success")
            return redirect(url_for("admin_offers"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ في الحفظ: {e}", "danger")
    
    return render_template("admin_offer_form.html", form=form, is_edit=False)

# استبدل دالة admin_offer_edit في app.py بهذا الكود:

@app.route("/admin/offers/<int:offer_id>/edit", methods=["GET","POST"])
@login_required
def admin_offer_edit(offer_id):
    admin_required()
    o = db.session.get(Offer, offer_id) or abort(404)
    form = OfferForm(obj=o)
    form.service_id.choices = _service_choices()
    form.service_id.data = o.service_id or 0
    
    if form.validate_on_submit():
        # حفظ البيانات الأساسية أولاً
        o.title = form.title.data.strip()
        o.description = form.description.data or ""
        o.price = form.price.data if form.price.data is not None else None
        o.active = True  # اجبار التفعيل
        o.service_id = (form.service_id.data if form.service_id.data != 0 else None)
        
        # معالجة الصورة (اختياري ومحمي من الأخطاء)
        try:
            if "image" in request.files and request.files["image"].filename:
                # حذف الصورة القديمة
                if o.image_path:
                    delete_image(o.image_path)
                
                # حفظ الصورة الجديدة بحجم مناسب
                file_storage = request.files["image"]
                if file_storage and allowed_file(file_storage.filename):
                    # حفظ بدون معالجة معقدة
                    unique = f"offer-" + uuid.uuid4().hex[:10] + ".jpg"
                    abs_path = os.path.join(UPLOAD_FOLDER, unique)
                    file_storage.save(abs_path)
                    
                    # معالجة بسيطة للحجم
                    from PIL import Image
                    with Image.open(abs_path) as img:
                        img = img.convert("RGB")
                        # تحديد حجم ثابت للعروض: 800x400
                        img = img.resize((800, 400), Image.LANCZOS)
                        img.save(abs_path, format="JPEG", quality=85)
                    
                    o.image_path = f"uploads/{unique}"
                else:
                    flash("صيغة الصورة غير مدعومة", "warning")
        except Exception as e:
            # في حالة خطأ الصورة، احفظ العرض بدون صورة
            print(f"خطأ في معالجة الصورة: {e}")
            flash("تم حفظ العرض، لكن حدث خطأ في الصورة", "warning")
        
        # حفظ في قاعدة البيانات
        try:
            db.session.commit()
            flash("تم تعديل الإعلان بنجاح.", "success")
            return redirect(url_for("admin_offers"))
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ في الحفظ: {e}", "danger")
    
    return render_template("admin_offer_form.html", form=form, is_edit=True)
@app.route("/admin/offers/<int:offer_id>/delete", methods=["POST"])
@login_required
def admin_offer_delete(offer_id):
    admin_required()
    o = db.session.get(Offer, offer_id) or abort(404)
    if o.image_path:
        delete_image(o.image_path)
    db.session.delete(o)
    db.session.commit()
    flash("تم حذف الإعلان.", "info")
    return redirect(url_for("admin_offers"))

# ---------- Admin Videos ----------
@app.route("/admin/videos")
@login_required
def admin_videos():
    admin_required()
    items = db.session.scalars(
        db.select(Video).order_by(Video.sort.asc(), Video.created_at.desc())
    ).all()
    return render_template("admin_videos.html", items=items)

@app.route("/admin/videos/new", methods=["GET","POST"])
@login_required
def admin_video_new():
    admin_required()
    form = VideoForm()
    if form.validate_on_submit():
        v = Video(
            title=form.title.data.strip(),
            description=form.description.data or "",
            source=form.source.data,
            active=form.active.data,
            featured=form.featured.data,
            sort=form.sort.data or 0
        )
        try:
            if form.source.data == "youtube":
                vid = parse_youtube_id(form.youtube_url.data or "")
                if not vid:
                    flash("رابط يوتيوب غير صالح.", "danger")
                    return render_template("admin_video_form.html", form=form, is_edit=False)
                v.youtube_id = vid
            else:
                fs = request.files.get("video_file")
                if not fs or fs.filename == "":
                    flash("الرجاء اختيار ملف MP4.", "danger")
                    return render_template("admin_video_form.html", form=form, is_edit=False)
                v.file_path = save_video_file(fs, prefix="video")

            if "poster" in request.files and request.files["poster"].filename:
                try:
                    v.poster_path = save_image(request.files["poster"], prefix="video_poster")
                except Exception as e:
                    flash(str(e), "danger")
                    return render_template("admin_video_form.html", form=form, is_edit=False)

            db.session.add(v)
            db.session.commit()
            flash("تمت إضافة الفيديو.", "success")
            return redirect(url_for("admin_videos"))
        except Exception as e:
            flash(str(e), "danger")
    return render_template("admin_video_form.html", form=form, is_edit=False)

@app.route("/admin/videos/<int:video_id>/edit", methods=["GET","POST"])
@login_required
def admin_video_edit(video_id):
    admin_required()
    v = db.session.get(Video, video_id) or abort(404)
    form = VideoForm(obj=v)
    if v.source == "youtube" and v.youtube_id:
        form.youtube_url.data = f"https://youtu.be/{v.youtube_id}"
    if form.validate_on_submit():
        v.title = form.title.data.strip()
        v.description = form.description.data or ""
        v.source = form.source.data
        v.active = form.active.data
        v.featured = form.featured.data
        v.sort = form.sort.data or 0
        try:
            if form.source.data == "youtube":
                vid = parse_youtube_id(form.youtube_url.data or "")
                if not vid:
                    flash("رابط يوتيوب غير صالح.", "danger")
                    return render_template("admin_video_form.html", form=form, is_edit=True)
                v.youtube_id = vid
                v.file_path = None
            else:
                fs = request.files.get("video_file")
                if fs and fs.filename:
                    if v.file_path:
                        try:
                            os.remove(os.path.join(app.static_folder, v.file_path.replace("/", os.sep)))
                        except Exception: 
                            pass
                    v.file_path = save_video_file(fs, prefix="video")

            if "poster" in request.files and request.files["poster"].filename:
                if v.poster_path:
                    delete_image(v.poster_path)
                v.poster_path = save_image(request.files["poster"], prefix="video_poster")

            db.session.commit()
            flash("تم تعديل الفيديو.", "success")
            return redirect(url_for("admin_videos"))
        except Exception as e:
            flash(str(e), "danger")
    return render_template("admin_video_form.html", form=form, is_edit=True)

@app.route("/admin/videos/<int:video_id>/delete", methods=["POST"])
@login_required
def admin_video_delete(video_id):
    admin_required()
    v = db.session.get(Video, video_id) or abort(404)
    for p in (v.file_path, v.poster_path):
        if p:
            try:
                if p.startswith('uploads/'):
                    os.remove(os.path.join(app.static_folder, p.replace("/", os.sep)))
                else:
                    delete_image(p)
            except Exception: 
                pass
    db.session.delete(v)
    db.session.commit()
    flash("تم حذف الفيديو.", "info")
    return redirect(url_for("admin_videos"))

# ---------- Public Videos ----------
@app.route("/videos")
def videos_page():
    page = request.args.get("page", 1, type=int)
    per_page = 9

    base_q = (
        db.select(Video)
          .where(Video.active == True)
          .order_by(Video.sort.asc(), Video.created_at.desc())
    )
    items = db.session.scalars(
        base_q.limit(per_page).offset((page - 1) * per_page)
    ).all()

    total = db.session.scalar(
        db.select(db.func.count()).select_from(Video).where(Video.active == True)
    )
    pages = (total + per_page - 1) // per_page if total else 1

    return render_template("videos.html", items=items, page=page, pages=pages)

# ---------- Account ----------
@app.route("/account/password", methods=["GET","POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("كلمة المرور الحالية غير صحيحة.", "danger")
            return render_template("change_password.html", form=form)
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("تم تحديث كلمة المرور بنجاح.", "success")
        return redirect(url_for("index"))
    return render_template("change_password.html", form=form)

# ---------- Contact ----------
@app.route("/contact")
def contact_page():
    contact = ContactInfo.get_single(create_if_missing=True)
    return render_template("contact.html", contact=contact)

@app.route("/admin/contact", methods=["GET", "POST"])
@login_required
def admin_contact():
    admin_required()
    contact = ContactInfo.get_single()
    form = ContactForm(obj=contact)
    if form.validate_on_submit():
        form.populate_obj(contact)
        db.session.commit()
        flash("تم حفظ بيانات التواصل.", "success")
        return redirect(url_for("contact_page"))
    return render_template("admin_contact.html", form=form)

# =========================================
# CLI Commands
# =========================================
@app.cli.command("init-db")
def init_db():
    """Initialize the database and seed default data."""
    db.drop_all()
    db.create_all()

    admin_phone = os.environ.get("ADMIN_PHONE", "+966501234567")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    admin_name = os.environ.get("ADMIN_NAME", "المدير")

    admin = User(full_name=admin_name, phone=admin_phone, is_admin=True)
    admin.set_password(admin_password)
    db.session.add(admin)

    services = [
        Service(name="تظليل", price=35, duration_minutes=60, active=True),
        Service(name="نانو سيراميك", price=120, duration_minutes=180, active=True),
        Service(name="تلميع داخلي", price=50, duration_minutes=90, active=True),
        Service(name="حماية واجهة", price=40, duration_minutes=60, active=True),
    ]
    db.session.add_all(services)

    demo_offer = Offer(
        title="عرض تظليل خاص", 
        description="خصم على التظليل لهذا الأسبوع.", 
        price=30, 
        active=True, 
        service_id=None
    )
    db.session.add(demo_offer)

    db.session.commit()
    print("✅ Database initialized. Admin phone:", admin_phone)

@app.cli.command("upgrade-db")
def upgrade_db():
    """Create any missing tables without dropping existing data."""
    db.create_all()
    print("✅ DB upgraded (created missing tables).")

# =========================================
# Main
# =========================================

# أضف هذا الكود في نهاية app.py قبل if __name__ == "__main__":

@app.cli.command("fix-offers")
def fix_offers():
    """تفعيل جميع الإعلانات"""
    try:
        # تفعيل جميع الإعلانات
        offers = db.session.scalars(db.select(Offer)).all()
        count = 0
        for offer in offers:
            offer.active = True
            count += 1
        
        db.session.commit()
        print(f"✅ تم تفعيل {count} إعلان!")
        
        # عرض الإعلانات
        active_offers = db.session.scalars(db.select(Offer).where(Offer.active == True)).all()
        print(f"📋 الإعلانات المفعلة:")
        for offer in active_offers:
            print(f"   - {offer.title} (ID: {offer.id})")
            
    except Exception as e:
        print(f"❌ خطأ: {e}")
@app.cli.command("fix-db")
def fix_db():
    """إصلاح قاعدة البيانات"""
    # إنشاء الجداول المفقودة
    db.create_all()
    
    # إضافة العمود المفقود
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE booking ADD COLUMN car_info_id INTEGER"))
            conn.commit()
            print("✅ تم إضافة عمود car_info_id")
    except Exception as e:
        print(f"⚠️ العمود موجود أو خطأ: {e}")

@app.cli.command("show-offers")
def show_offers():
    """عرض جميع الإعلانات"""
    try:
        offers = db.session.scalars(db.select(Offer)).all()
        print(f"📋 إجمالي الإعلانات: {len(offers)}")
        for offer in offers:
            status = "مفعل" if offer.active else "موقوف"
            print(f"   - {offer.title} ({status}) - ID: {offer.id}")
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    app.run(debug=True)