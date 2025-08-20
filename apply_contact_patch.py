#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto patcher: adds ContactInfo model, routes (/contact, /admin/contact),
and navbar links into an existing Flask project using SQLAlchemy "db".
It ensures code is inserted *after* db is defined to avoid NameError.
Usage:
    python apply_contact_patch.py "C:\\path\\to\\your\\project"
If no argument is passed, it uses the current working directory.
"""
import sys, os, io, re, shutil

CONTACT_BLOCK = r'''
from flask import render_template, redirect, url_for, abort, flash
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import Optional, Length, Email, URL
from flask_login import login_required, current_user

class ContactInfo(db.Model):
    __tablename__ = "contact_info"
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50))
    whatsapp = db.Column(db.String(50))
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    location_url = db.Column(db.String(512))
    map_embed = db.Column(db.Text)

    @staticmethod
    def get_single(create_if_missing=True):
        obj = ContactInfo.query.first()
        if not obj and create_if_missing:
            obj = ContactInfo()
            db.session.add(obj)
            db.session.commit()
        return obj

class ContactForm(FlaskForm):
    phone = StringField("الهاتف", validators=[Optional(), Length(max=50)])
    whatsapp = StringField("واتساب", validators=[Optional(), Length(max=50)])
    email = StringField("الإيميل", validators=[Optional(), Email(), Length(max=120)])
    address = StringField("العنوان", validators=[Optional(), Length(max=255)])
    location_url = StringField("رابط الموقع على الخريطة", validators=[Optional(), URL(), Length(max=512)])
    map_embed = TextAreaField("كود الخريطة (iframe اختياري)", validators=[Optional(), Length(max=5000)])

def _ensure_admin():
    if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
        abort(403)

@app.route("/contact")
def contact_page():
    contact = ContactInfo.get_single(create_if_missing=True)
    return render_template("contact.html", contact=contact)

@app.route("/admin/contact", methods=["GET", "POST"])
@login_required
def admin_contact():
    _ensure_admin()
    contact = ContactInfo.get_single()
    form = ContactForm(obj=contact)
    if form.validate_on_submit():
        form.populate_obj(contact)
        db.session.commit()
        flash("تم حفظ بيانات التواصل.", "success")
        return redirect(url_for("contact_page"))
    return render_template("admin_contact.html", form=form)
'''

NAV_CONTACT = r'''
<li class="nav-item">
  <a class="nav-link" href="{{ url_for('contact_page') }}">تواصل وموقعنا</a>
</li>
{% if current_user.is_authenticated and current_user.is_admin %}
<li class="nav-item">
  <a class="nav-link" href="{{ url_for('admin_contact') }}">تعديل بيانات التواصل</a>
</li>
{% endif %}
'''

def patch_app_py(app_path):
    with open(app_path, "r", encoding="utf-8") as f:
        src = f.read()

    # sanity: prevent double insertion
    if "class ContactInfo(db.Model):" in src and "def contact_page()" in src:
        print("[i] Contact block already exists in app.py, skipping insert.")
        return

    # find where db is defined
    m = re.search(r'^\s*db\s*=\s*SQLAlchemy\([^\n]*\)\s*$', src, flags=re.M)
    insert_pos = None
    if m:
        insert_pos = m.end()
    else:
        # fallback: db = SQLAlchemy()
        m2 = re.search(r'^\s*db\s*=\s*SQLAlchemy\(\s*\)\s*$', src, flags=re.M)
        if m2:
            insert_pos = m2.end()
        else:
            # after import of SQLAlchemy
            m3 = re.search(r'from\s+flask_sqlalchemy\s+import\s+SQLAlchemy.*?\n', src, flags=re.S)
            if m3:
                insert_pos = m3.end()
            else:
                insert_pos = 0

    # backup
    bak_path = app_path + ".bak_contact"
    import shutil
    shutil.copyfile(app_path, bak_path)

    # insert with two newlines
    patched = src[:insert_pos] + "\n\n" + CONTACT_BLOCK.strip() + "\n\n" + src[insert_pos:]

    with open(app_path, "w", encoding="utf-8") as f:
        f.write(patched)
    print("[+] Patched app.py (ContactInfo block inserted). Backup:", bak_path)

def ensure_templates(project_root):
    tpl_dir = os.path.join(project_root, "templates")
    os.makedirs(tpl_dir, exist_ok=True)

    def write_if_missing(name, content):
        path = os.path.join(tpl_dir, name)
        if os.path.exists(path):
            print(f"[i] {name} exists, leaving it unchanged.")
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Created templates/{name}]")

    contact_html = """{% extends "base.html" %}
{% block title %}تواصل وموقعنا{% endblock %}
{% block content %}
<div class="container my-4">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3 class="m-0">تواصل وموقعنا</h3>
    {% if current_user.is_authenticated and current_user.is_admin %}
      <a class="btn btn-sm btn-primary" href="{{ url_for('admin_contact') }}">تعديل بيانات التواصل</a>
    {% endif %}
  </div>
  <div class="row g-3">
    <div class="col-12 col-lg-6">
      <div class="card shadow-sm h-100">
        <div class="card-body">
          <h5 class="card-title mb-3">معلومات التواصل</h5>
          <ul class="list-unstyled small">
            <li class="mb-2"><strong>الهاتف:</strong> {{ contact.phone or "—" }}</li>
            <li class="mb-2"><strong>واتساب:</strong> {{ contact.whatsapp or "—" }}</li>
            <li class="mb-2"><strong>الإيميل:</strong> {{ contact.email or "—" }}</li>
            <li class="mb-2"><strong>العنوان:</strong> {{ contact.address or "—" }}</li>
            {% if contact.location_url %}
            <li class="mt-2">
              <a class="btn btn-outline-primary btn-sm" href="{{ contact.location_url }}" target="_blank" rel="noopener">فتح الموقع على الخريطة</a>
            </li>
            {% endif %}
          </ul>
          <div class="text-muted small">يُمكن للمدير تعديل البيانات.</div>
        </div>
      </div>
    </div>
    <div class="col-12 col-lg-6">
      <div class="card shadow-sm h-100">
        <div class="card-body">
          <h5 class="card-title mb-3">الخريطة</h5>
          {% if contact.map_embed %}
            <div class="ratio ratio-16x9">
              {{ contact.map_embed | safe }}
            </div>
          {% else %}
            <div class="alert alert-info mb-0">
              لم يتم إدخال كود الخريطة بعد. أضفه من صفحة الإدارة (<code>/admin/contact</code>) لعرض الخريطة هنا.
            </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
"""

    admin_contact_html = """{% extends "base.html" %}
{% block title %}بيانات التواصل{% endblock %}
{% block content %}
<div class="container my-4">
  <h3 class="mb-3">تعديل بيانات التواصل وموقعنا</h3>
  <form method="post" novalidate>
    {{ form.csrf_token }}
    <div class="mb-3">
      <label class="form-label">الهاتف</label>
      {{ form.phone(class="form-control", placeholder="05xxxxxxxx") }}
    </div>
    <div class="mb-3">
      <label class="form-label">واتساب</label>
      {{ form.whatsapp(class="form-control", placeholder="05xxxxxxxx") }}
    </div>
    <div class="mb-3">
      <label class="form-label">الإيميل</label>
      {{ form.email(class="form-control", placeholder="name@example.com") }}
    </div>
    <div class="mb-3">
      <label class="form-label">العنوان</label>
      {{ form.address(class="form-control", placeholder="الحي - الشارع - الوصف المختصر") }}
    </div>
    <div class="mb-3">
      <label class="form-label">رابط الموقع على الخريطة (Google Maps)</label>
      {{ form.location_url(class="form-control", placeholder="https://maps.google.com/?q=...") }}
    </div>
    <div class="mb-3">
      <label class="form-label">كود الخريطة (iframe اختياري)</label>
      {{ form.map_embed(class="form-control", rows="4", placeholder='<iframe src="..."></iframe>') }}
    </div>
    <button type="submit" class="btn btn-primary">حفظ</button>
    <a href="{{ url_for('contact_page') }}" class="btn btn-light ms-2">رجوع</a>
  </form>
</div>
{% endblock %}
"""

    write_if_missing("contact.html", contact_html)
    write_if_missing("admin_contact.html", admin_contact_html)

def patch_navbar(base_html_path):
    with open(base_html_path, "r", encoding="utf-8") as f:
        html = f.read()

    if "url_for('contact_page')" in html:
        print("[i] Navbar already contains contact links, skipping.")
        return

    m = re.search(r'(<ul[^>]*class="[^"]*navbar-nav[^"]*"[^>]*>)', html, flags=re.I)
    if not m:
        print("[!] Could not find <ul class='navbar-nav'> to insert links. Please add manually.")
        return

    insert_at = m.end()
    patched = html[:insert_at] + NAV_CONTACT + html[insert_at:]

    bak = base_html_path + ".bak_contact"
    import shutil
    shutil.copyfile(base_html_path, bak)
    with open(base_html_path, "w", encoding="utf-8") as f:
        f.write(patched)
    print("[+] Inserted navbar links. Backup:", bak)

def main():
    project_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    app_py = os.path.join(project_root, "app.py")
    base_html = os.path.join(project_root, "templates", "base.html")

    if not os.path.exists(app_py):
        print("[x] app.py not found at:", app_py)
        sys.exit(1)
    if not os.path.exists(os.path.dirname(base_html)):
        print("[x] templates/ folder not found at:", os.path.dirname(base_html))
        sys.exit(1)

    patch_app_py(app_py)
    ensure_templates(project_root)
    if os.path.exists(base_html):
        patch_navbar(base_html)
    else:
        print("[!] templates/base.html not found; add contact links manually to your navbar.")

    print("\nDone. Next steps:")
    print(" 1) pip install -r requirements.txt")
    print(" 2) set FLASK_APP=app.py (or $env:FLASK_APP in PowerShell)")
    print(" 3) flask --app app.py init-db")
    print(" 4) flask --app app.py run")

if __name__ == "__main__":
    main()
