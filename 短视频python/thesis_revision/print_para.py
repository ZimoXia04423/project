# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from docx import Document

idx = int(sys.argv[1])
p = Path(__file__).resolve().parents[1] / "短视频.docx"
d = Document(str(p))
print(d.paragraphs[idx].text)
