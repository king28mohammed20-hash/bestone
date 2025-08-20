#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_newlines_v2.py
------------------
تصحيح موسّع لمشكلة ظهور "\n" كحروف داخل app.py حول كود الفيديو (helpers/model/form).
- يحذف الباك سلاش قبل "# ====== Video helpers ======" إن وُجد.
- يحوّل "\n" إلى أسطر حقيقية فقط ضمن مقاطع الفيديو (لا يمس باقي الملف).
- يصلّح الفراغات بين موديل Video وبداية VideoForm.

الاستخدام:
    python fix_newlines_v2.py "C:\path\to\project\app.py"
    أو:
    python fix_newlines_v2.py "C:\path\to\project"
"""
import sys, re, shutil
from pathlib import Path
from datetime import datetime

def backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak-{ts}")
    shutil.copyfile(p, bak)
    return bak

def replace_slice(s: str, start: int, end: int, repl: str) -> str:
    return s[:start] + repl + s[end:]

def normalize_block(block: str) -> str:
    # حوّل أي "\n" إلى أسطر حقيقية
    block = block.replace("\\n", "\n")
    # أزل باك سلاش في نهاية الأسطر
    block = re.sub(r"\\\s*\n", "\n", block)
    # اضبط فراغات زائدة (أكثر من 3 أسطر فارغة → سطرين)
    block = re.sub(r"\n{3,}", "\n\n", block)
    return block

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_newlines_v2.py <app.py or project dir>")
        sys.exit(1)
    p = Path(sys.argv[1])
    if p.is_dir():
        p = p / "app.py"
    if not p.exists():
        print("❌ app.py not found:", p)
        sys.exit(2)

    s = p.read_text(encoding="utf-8")
    backup_path = backup(p)
    print("🗂️  Backup:", backup_path.name)

    # 1) أزل باك سلاش قبل Video helpers
    s = re.sub(r"\\\s*\n(\s*#\s*={2,}\s*Video helpers\s*={2,})", r"\n\1", s)

    # 2) حدد حدود كتلة الفيديو: من "# ====== Video helpers ======" حتى "class VideoForm" أو الراوتات
    helpers_m = re.search(r"#\s*={2,}\s*Video helpers\s*={2,}", s)
    model_m   = re.search(r"class\s+Video\s*\(db\.Model\)\s*:", s)
    form_m    = re.search(r"class\s+VideoForm\s*\(FlaskForm\)\s*:", s)

    changed = False
    if helpers_m and model_m:
        start = helpers_m.start()
        end = form_m.start() if form_m else (model_m.end() + 5000)
        block = s[start:end]
        new_block = normalize_block(block)
        if new_block != block:
            s = replace_slice(s, start, end, new_block)
            changed = True

    # 3) إصلاح خاص بين created_at .. و class VideoForm (إن بقيت \n)
    s = re.sub(
        r"(created_at\s*=\s*db\.Column\([^\n]*\))\\n(?:\\n)+\s*(?=class\s+VideoForm\b)",
        r"\1\n\n", s
    )

    # 4) إصلاح عام: لو بقيت "\n\n# ====== Video helpers", حوّلها
    s = re.sub(r"\\n\\n(\s*#\s*={2,}\s*Video helpers\s*={2,})", r"\n\n\1", s)

    p.write_text(s, encoding="utf-8")
    print("✅ Fixed. Try running Flask again.")

if __name__ == "__main__":
    main()
