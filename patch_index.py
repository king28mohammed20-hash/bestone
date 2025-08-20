import sys, re, os
from pathlib import Path

def patch_index(index_path: Path):
    html = index_path.read_text(encoding="utf-8")

    # Remove our earlier "تبويب تواصل وموقعنا" block if present (between comment markers)
    html = re.sub(r"<!--\s*===== تبويب تواصل وموقعنا.*?===== -->", "", html, flags=re.DOTALL)

    # Remove any <li>/<div> blocks that reference {{ contact.* }}
    lines = html.splitlines()
    out = []
    skip = False
    buf = []
    def flush_buf():
        nonlocal out, buf
        if buf:
            out.extend(buf)
            buf = []

    for line in lines:
        if "{{ contact" in line or "{% if contact" in line or "admin_contact" in line or "contact_page" in line:
            # skip single line and avoid adding
            continue
        out.append(line)

    new_html = "\n".join(out)
    index_path.write_text(new_html, encoding="utf-8")
    print("Patched:", index_path)

def main():
    if len(sys.argv) != 2:
        print("Usage: python patch_index.py <project_dir>")
        sys.exit(1)
    project_dir = Path(sys.argv[1])
    idx = project_dir / "templates" / "index.html"
    if not idx.exists():
        print("index.html not found at", idx)
        sys.exit(2)
    patch_index(idx)

if __name__ == "__main__":
    main()
