# -*- coding: utf-8 -*-

import sys, os, re, io, pathlib

HELPERS = r"""
# ====== Video helpers ======
ALLOWED_VIDEO_EXTS = {"mp4"}
VIDEO_FOLDER = os.path.join(app.static_folder, "uploads", "videos")
os.makedirs(VIDEO_FOLDER, exist_ok=True)

def allowed_video(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTS

def save_video_file(file_storage, prefix="vid"):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_video(file_storage.filename):
        raise ValueError("صيغة الفيديو غير مسموحة. المسموح: mp4")
    unique = f"{prefix}-" + uuid.uuid4().hex[:10] + ".mp4"
    abs_path = os.path.join(VIDEO_FOLDER, unique)
    file_storage.save(abs_path)
    return f"uploads/videos/{unique}"

import re as _re
_YT_PATTERNS = [
    r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:\?|&|$)",
    r"youtu\.be\/([0-9A-Za-z_-]{11})",
]
def parse_youtube_id(url: str) -> str | None:
    if not url: return None
    for p in _re._pattern_type(_re.compile(_re.escape("")).pattern) if False else _YT_PATTERNS:
        m = _re.search(p, url)
        if m: return m.group(1)
    return None
"""

MODEL = r"""
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(16), nullable=False, default="youtube")  # youtube | mp4
    youtube_id = db.Column(db.String(16), nullable=True)
    file_path = db.Column(db.String(255), nullable=True)   # static path for mp4
    poster_path = db.Column(db.String(255), nullable=True) # صورة غلاف (اختياري)
    active = db.Column(db.Boolean, default=True)
    featured = db.Column(db.Boolean, default=False)
    sort = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
"""

FORM = r"""
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
"""

ROUTES = r"""
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
                        except Exception: pass
                    v.file_path = save_video_file(fs, prefix="video")

            if "poster" in request.files and request.files["poster"].filename:
                if v.poster_path:
                    try:
                        os.remove(os.path.join(app.static_folder, v.poster_path.replace("/", os.sep)))
                    except Exception: pass
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
                os.remove(os.path.join(app.static_folder, p.replace("/", os.sep)))
            except Exception: pass
    db.session.delete(v)
    db.session.commit()
    flash("تم حذف الفيديو.", "info")
    return redirect(url_for("admin_videos"))

# ---------- Public Videos ----------
@app.route("/videos")
def videos_page():
    items = db.session.scalars(
        db.select(Video).where(Video.active == True).order_by(Video.sort.asc(), Video.created_at.desc())
    ).all()
    return render_template("videos.html", items=items)
"""

UPGRADE = r"""
@app.cli.command("upgrade-db")
def upgrade_db():
    \"\"\"Create any missing tables without dropping existing data.\"\"\"
    db.create_all()
    print("✅ DB upgraded (created missing tables).")
"""
NAV_PUBLIC = "<li class=\"nav-item\"><a class=\"nav-link\" href=\"{{ url_for('videos_page') }}\">فيديوهاتنا</a></li>"
NAV_ADMIN  = "<li class=\"nav-item\"><a class=\"nav-link\" href=\"{{ url_for('admin_videos') }}\">إدارة الفيديو</a></li>"

def patch_app_py(app_py_path):
    s = open(app_py_path, "r", encoding="utf-8").read()

    # Ensure FileField import
    if "FileField" not in s:
        # Try to extend an existing wtforms import line
        m = re.search(r"^from\\s+wtforms\\s+import\\s+(.+)$", s, re.M)
        if m:
            line = m.group(0)
            if "FileField" not in line:
                s = s.replace(line, line.rstrip() + ", FileField")
        else:
            # Insert after FlaskForm import
            m2 = re.search(r"^from\\s+flask_wtf\\s+import\\s+FlaskForm.*$", s, re.M)
            insert_at = m2.end() if m2 else 0
            s = s[:insert_at] + "\\nfrom wtforms import FileField\\n" + s[insert_at:]

    # Where to insert blocks: just before "if __name__ =="
    main_idx = s.find("\\nif __name__")
    if main_idx == -1:
        main_idx = len(s)

    def ensure(block, marker_hint):
        nonlocal s, main_idx
        if marker_hint in s:
            return
        s = s[:main_idx] + "\\n\\n" + block.strip() + "\\n\\n" + s[main_idx:]
        main_idx = s.find("\\nif __name__")
        if main_idx == -1:
            main_idx = len(s)

    ensure(HELPERS, "Video helpers")
    ensure(MODEL, "class Video(db.Model)")
    ensure(FORM, "class VideoForm(FlaskForm)")
    ensure(ROUTES, "def admin_videos():")
    if "upgrade_db()" not in s:
        ensure(UPGRADE, "upgrade_db()")

    open(app_py_path, "w", encoding="utf-8").write(s)
    print(f"Patched: {app_py_path}")

def patch_base_html(base_html_path):
    try:
        s = open(base_html_path, "r", encoding="utf-8").read()
    except FileNotFoundError:
        print("WARNING: base.html not found, skipping navbar patch.")
        return

    changed = False
    if "url_for('videos_page')" not in s:
        # insert public link before first closing </ul> after navbar-nav
        m = re.search(r"<ul[^>]*navbar-nav[^>]*>.*?</ul>", s, re.S)
        if m:
            whole = m.group(0)
            new = whole.replace("</ul>", "  " + NAV_PUBLIC + "\n</ul>")
            s = s.replace(whole, new)
            changed = True

    if "url_for('admin_videos')" not in s:
        # try to insert inside admin-only block if exists
        if "{% if current_user.is_authenticated" in s:
            s = s.replace("{% endif %}", "  " + NAV_ADMIN + "\n{% endif %}", 1)
            changed = True
        else:
            m = re.search(r"<ul[^>]*navbar-nav[^>]*>.*?</ul>", s, re.S)
            if m:
                whole = m.group(0)
                new = whole.replace("</ul>", f"  {NAV_ADMIN}\\n</ul>")
                s = s.replace(whole, new)
                changed = True

    if changed:
        open(base_html_path, "w", encoding="utf-8").write(s)
        print(f"Patched navbar: {base_html_path}")
    else:
        print("Navbar already contains videos links.")

def write_templates(proj_dir):
    tdir = os.path.join(proj_dir, "templates")
    os.makedirs(tdir, exist_ok=True)
    files = {
        "admin_videos.html": """{% extends "base.html" %}
{% block title %}إدارة الفيديو{% endblock %}

{% block content %}
<div class="container my-4">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3 class="m-0">إدارة الفيديو</h3>
    <a class="btn btn-primary btn-sm" href="{{ url_for('admin_video_new') }}">+ إضافة فيديو</a>
  </div>

  {% if items %}
  <div class="table-responsive">
    <table class="table align-middle">
      <thead>
        <tr>
          <th>#</th><th>العنوان</th><th>المصدر</th><th>ترتيب</th><th>حالة</th><th>مميّز</th><th>أُضيف</th><th>إجراءات</th>
        </tr>
      </thead>
      <tbody>
        {% for v in items %}
        <tr>
          <td>{{ v.id }}</td>
          <td>{{ v.title }}</td>
          <td>{{ 'YouTube' if v.source=='youtube' else 'MP4' }}</td>
          <td>{{ v.sort }}</td>
          <td><span class="badge {{ 'bg-success' if v.active else 'bg-secondary' }}">{{ 'فعّال' if v.active else 'غير فعّال' }}</span></td>
          <td>{{ '✓' if v.featured else '—' }}</td>
          <td>{{ v.created_at.strftime('%Y-%m-%d') }}</td>
          <td class="actions">
            <a class="btn btn-sm btn-outline-primary" href="{{ url_for('admin_video_edit', video_id=v.id) }}">تعديل</a>
            <form method="post" action="{{ url_for('admin_video_delete', video_id=v.id) }}" style="display:inline" onsubmit="return confirm('حذف نهائي؟');">
              <button class="btn btn-sm btn-outline-danger">حذف</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% else %}
  <div class="alert alert-info">لا توجد فيديوهات حتى الآن.</div>
  {% endif %}
</div>
{% endblock %}""",
        "admin_video_form.html": """{% extends "base.html" %}
{% block title %}{{ 'تعديل' if is_edit else 'إضافة' }} فيديو{% endblock %}

{% block content %}
<div class="container my-4">
  <h3 class="mb-3">{{ 'تعديل' if is_edit else 'إضافة' }} فيديو</h3>

  <form method="post" enctype="multipart/form-data">
    {{ form.csrf_token }}

    <div class="mb-3">
      <label class="form-label">العنوان</label>
      {{ form.title(class="form-control") }}
    </div>

    <div class="mb-3">
      <label class="form-label">الوصف (اختياري)</label>
      {{ form.description(class="form-control", rows="3") }}
    </div>

    <div class="row g-3">
      <div class="col-md-4">
        <label class="form-label">المصدر</label>
        {{ form.source(class="form-select") }}
      </div>
      <div class="col-md-8">
        <label class="form-label">رابط يوتيوب</label>
        {{ form.youtube_url(class="form-control", placeholder="https://youtu.be/VIDEO_ID أو رابط يوتيوب كامل") }}
        <div class="form-text">يُستخدم فقط إذا كان المصدر “يوتيوب”.</div>
      </div>
    </div>

    <div class="mb-3 mt-3">
      <label class="form-label">ملف الفيديو (MP4)</label>
      {{ form.video_file(class="form-control") }}
      <div class="form-text">يُستخدم فقط إذا كان المصدر “MP4”.</div>
    </div>

    <div class="mb-3">
      <label class="form-label">صورة الغلاف (اختياري)</label>
      {{ form.poster(class="form-control") }}
    </div>

    <div class="row g-3">
      <div class="col-md-3">
        <label class="form-label">ترتيب</label>
        {{ form.sort(class="form-control") }}
      </div>
      <div class="col-md-3 d-flex align-items-center gap-3">
        <div class="form-check">
          {{ form.active(class="form-check-input", id="fActive") }}
          <label class="form-check-label" for="fActive">فعّال</label>
        </div>
        <div class="form-check">
          {{ form.featured(class="form-check-input", id="fFeat") }}
          <label class="form-check-label" for="fFeat">مميّز</label>
        </div>
      </div>
    </div>

    <div class="mt-4">
      <button class="btn btn-primary">{{ 'حفظ التعديلات' if is_edit else 'إضافة' }}</button>
      <a class="btn btn-light ms-2" href="{{ url_for('admin_videos') }}">رجوع</a>
    </div>
  </form>
</div>
{% endblock %}""",
        "videos.html": """{% extends "base.html" %}
{% block title %}فيديوهاتنا{% endblock %}

{% block content %}
<div class="container my-4">
  <h3 class="mb-3">فيديوهات من شغلنا</h3>

  <div class="row g-4">
    {% for v in items %}
      <div class="col-12 col-md-6 col-lg-4">
        <div class="card h-100 shadow-sm">
          <div class="ratio ratio-16x9">
            {% if v.source == 'youtube' and v.youtube_id %}
              <iframe
                src="https://www.youtube-nocookie.com/embed/{{ v.youtube_id }}?rel=0&modestbranding=1"
                title="{{ v.title }}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen loading="lazy"></iframe>
            {% elif v.source == 'mp4' and v.file_path %}
              <video controls preload="metadata" {% if v.poster_path %}poster="{{ url_for('static', filename=v.poster_path) }}"{% endif %}>
                <source src="{{ url_for('static', filename=v.file_path) }}" type="video/mp4">
                متصفحك لا يدعم تشغيل الفيديو.
              </video>
            {% else %}
              <div class="d-flex align-items-center justify-content-center bg-light">لا يمكن عرض الفيديو</div>
            {% endif %}
          </div>
          <div class="card-body">
            <h6 class="card-title mb-1">{{ v.title }}</h6>
            {% if v.description %}<p class="card-text small text-muted">{{ v.description }}</p>{% endif %}
          </div>
        </div>
      </div>
    {% else %}
      <div class="col-12">
        <div class="alert alert-info">لا توجد فيديوهات حتى الآن.</div>
      </div>
    {% endfor %}
  </div>
</div>
{% endblock %}""",
    }
    for name, content in files.items():
        path = os.path.join(tdir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Wrote template: {path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python apply_videos_patch.py <project_dir>")
        sys.exit(1)
    proj = sys.argv[1]
    app_py = os.path.join(proj, "app.py")
    base_html = os.path.join(proj, "templates", "base.html")
    if not os.path.isfile(app_py):
        print("ERROR: app.py not found in the given directory.")
        sys.exit(2)

    patch_app_py(app_py)
    patch_base_html(base_html)
    write_templates(proj)

    print("\\n✅ Done. Next steps:")
    print("1) flask --app app.py upgrade-db")
    print("2) flask --app app.py run")

if __name__ == "__main__":
    main()
