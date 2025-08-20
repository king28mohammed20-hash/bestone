#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_newlines_v3.py
------------------
تصحيح موسّع لمشكلة ظهور "\\n" الحرفية في نهاية VideoForm وبداية راوتات الفيديو (Admin/Public).
- يحوّل "\\n" إلى أسطر حقيقية ضمن مقاطع Video helpers/model/form/routes فقط.
- يزيل أي backslash "\" آخر السطر داخل هذه المقاطع.
الاستعمال:
    python fix_newlines_v3.py "C:\path\to\project\app.py"
    أو:
    python fix_newlines_v3.py "C:\path\to\project"
"""
import sys, re, shutil
from pathlib import Path
from datetime import datetime

def backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak-{ts}")
    shutil.copyfile(p, bak)
    return bak

def norm_block(txt: str) -> str:
    txt = txt.replace("\\n", "\n")
    txt = re.sub(r"\\\s*\n", "\n", txt)       # remove trailing backslash
    txt = re.sub(r"\n{3,}", "\n\n", txt)      # collapse many newlines
    return txt

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_newlines_v3.py <app.py or project dir>")
        sys.exit(1)
    p = Path(sys.argv[1])
    if p.is_dir():
        p = p / "app.py"
    if not p.exists():
        print("❌ app.py not found:", p)
        sys.exit(2)

    s = p.read_text(encoding="utf-8")
    backup(p)

    # Locate blocks
    helpers = re.search(r"#\s*={2,}\s*Video helpers\s*={2,}", s)
    model   = re.search(r"class\s+Video\s*\(db\.Model\)\s*:", s)
    form    = re.search(r"class\s+VideoForm\s*\(FlaskForm\)\s*:", s)
    admin_b = re.search(r"#\s*-{2,}\s*Admin Videos\s*-{2,}", s)
    public_b= re.search(r"#\s*-{2,}\s*Public Videos\s*-{2,}", s)

    # Normalize helpers..form
    if helpers:
        end_idx = form.start() if form else (helpers.end()+6000)
        blk = s[helpers.start():end_idx]
        s = s[:helpers.start()] + norm_block(blk) + s[end_idx:]

    # Normalize form..admin routes
    if form and admin_b:
        blk = s[form.start():admin_b.start()]
        s = s[:form.start()] + norm_block(blk) + s[admin_b.start():]

    # Normalize admin routes .. public routes
    if admin_b and public_b:
        blk = s[admin_b.start():public_b.start()]
        s = s[:admin_b.start()] + norm_block(blk) + s[public_b.start():]

    # Normalize public routes .. little further (up to end of videos page route)
    if public_b:
        # find end of videos_page function by matching "return render_template(...)" then next ')'
        m_end = re.search(r"return\s+render_template\([^\)]*\)\s*", s[public_b.start():], re.S)
        if m_end:
            start = public_b.start()
            end = public_b.start() + m_end.end()
            blk = s[start:end]
            s = s[:start] + norm_block(blk) + s[end:]

    # Specific fix: collapse literal sequence after SubmitField("حفظ")
    s = re.sub(r'(SubmitField\(".*?"\))\\n(?:\\n)+\s*(#\s*-{2,}\s*Admin Videos\s*-{2,})', r"\1\n\n\2", s)

    p.write_text(s, encoding="utf-8")
    print("✅ Fixed. Try running Flask again.")

if __name__ == "__main__":
    main()
