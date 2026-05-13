# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from docx import Document

p = Path(__file__).parent / "短视频.docx"
d = Document(str(p))
for i, para in enumerate(d.paragraphs):
    t = para.text.strip()
    if not t:
        continue
    style = para.style.name if para.style else ""
    print(f"{i:4} [{style}] {t[:500]}")
