#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_newlines.py
----------------
تصليح سريع لـ app.py إذا ظهر فيه "\n" حرفيًا أو "\" قبل قسم فيديوهات
بعد تشغيل سكربت الإضافة. يحوّل السلاسل النصية الخاطئة لأسطر فعلية.

الاستعمال:
    python fix_newlines.py "C:\path\to\your\project\app.py"
    # أو تمرير مسار المجلد فقط:
    python fix_newlines.py "C:\path\to\your\project"
"""
from __future__ import annotations
import argparse, shutil, sys, re
from pathlib import Path
from datetime import datetime

def load_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def save_text(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")

def make_backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak-{ts}")
    shutil.copyfile(p, bak)
    return bak

def patch_content(s: str) -> tuple[str, dict]:
    stats = {"raw_to_real_newlines":0, "removed_backslash_before_video":0,
             "after_return_none":0, "collapse_many_before_class":0}

    # 1) لو فيه باك سلاش قبل سطر "Video helpers" نحذفه
    new_s, n = re.subn(r"\\\s*\n\s*(#\s*={2,}\s*Video helpers\s*={2,})", r"\n\1", s)
    if n:
        stats["removed_backslash_before_video"] += n
    s = new_s

    # 2) لو فيه "\n\n# ====== Video helpers ======" حروف، نخليها أسطر
    new_s, n = re.subn(r"\\n\\n(#\s*={2,}\s*Video helpers\s*={2,})", r"\n\n\1", s)
    if n:
        stats["raw_to_real_newlines"] += n
    s = new_s

    # 3) إصلاح "return None\n" إلى أسطر حقيقية بعد دالة parse_youtube_id
    new_s, n = re.subn(r"(return\s+None)\\n(\s*\\n)*", r"\1\n\n", s)
    if n:
        stats["after_return_none"] += n
    s = new_s

    # 4) تقليل \n\n\n\n قبل class Video إلى سطرين
    new_s, n = re.subn(r"\\n\\n\\n\\n(?=class\s+Video\b)", "\n\n", s)
    if n:
        stats["collapse_many_before_class"] += n
    s = new_s

    return s, stats

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="مسار app.py أو مجلد المشروع الذي يحوي app.py")
    args = ap.parse_args()

    p = Path(args.path)
    if p.is_dir():
        p = p / "app.py"
    if not p.exists():
        print("❌ لم يتم العثور على app.py:", p)
        sys.exit(2)

    # نسخة احتياطية
    bak = make_backup(p)
    print("🗂️  Backup:", bak.name)

    s = load_text(p)
    s2, stats = patch_content(s)

    if s2 == s:
        print("ℹ️ لا تغييرات مطلوبة (الملف يبدو سليم).")
        sys.exit(0)

    save_text(p, s2)
    print("✅ تم التصحيح.")
    print("تفاصيل:", stats)

if __name__ == "__main__":
    main()
