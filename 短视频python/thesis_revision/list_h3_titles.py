# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from docx import Document

p = Path(__file__).resolve().parents[1] / "短视频.docx"
d = Document(str(p))
for i, para in enumerate(d.paragraphs):
    t = para.text.strip()
    if not t:
        continue
    if t[0].isdigit() and ("3." in t[:4] or t.startswith("3 ") or t.startswith("4")):
        print(i, para.style.name if para.style else "", "|", t[:90])
