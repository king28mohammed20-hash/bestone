# إضافة صفحة فيديوهات + إدارة (YouTube/MP4)

## ماذا في الباك؟
- `apply_videos_patch.py` — سكربت يحقن الأكواد تلقائيًا داخل `app.py`، يعدّل النافبار، ويكتب القوالب.
- `templates/*.html` — القوالب الجاهزة (سيتم نسخها تلقائيًا أيضًا).

## استخدام سريع
1) فك الضغط، ثم من PowerShell داخل مجلد مشروعك:
```powershell
python apply_videos_patch.py "C:\Users\harbi\OneDrive\Desktop\car\bestone_all_done"
```

2) أنشئ الجدول بدون حذف البيانات:
```powershell
$env:FLASK_APP="app.py"
flask --app app.py upgrade-db
flask --app app.py run
```

## ملاحظات
- يدعم رفع MP4 أو إدخال رابط يوتيوب. ملفات MP4 تحفظ داخل: `static/uploads/videos/`
- لو ظهرت رسالة حجم الملف كبير، ارفع الحد في `app.py`:
```python
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))
```
ثم في PowerShell:
```powershell
$env:MAX_CONTENT_LENGTH=52428800
```

## روابط النافبار
- عام: **فيديوهاتنا** → `/videos`
- للأدمن: **إدارة الفيديو** → `/admin/videos`
