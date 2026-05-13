# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from docx import Document

p = Path(__file__).resolve().parents[1] / "短视频.docx"
d = Document(str(p))
start, end = int(sys.argv[1]), int(sys.argv[2])
for i, para in enumerate(d.paragraphs):
    if start <= i <= end:
        t = para.text
        st = para.style.name if para.style else ""
        print(f"{i}\t{st}\t{t[:200]}")
