# -*- coding: utf-8 -*-
"""
Adjust heading paragraph spacing per 规范(1): 段前、段后各 0.5 行.
Uses beforeLines/afterLines = 50 (hundredths of a line per OOXML).
Adds fixed 18pt line (360 twips, lineRule exact) where missing for h2/h3.
Does not modify document.xml (text unchanged).
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "医学骨架30012(2)_格式调整_目录修复.docx"
DEFAULT_DST = ROOT / "医学骨架30012(2)_格式调整_段间距规范.docx"

SPEC_SPACING = (
    '<w:spacing w:beforeLines="50" w:afterLines="50" '
    'w:line="360" w:lineRule="exact"/>'
)


def patch_styles_xml(xml: str) -> str:
    out = xml

    out = out.replace(
        '<w:spacing w:before="100" w:beforeAutospacing="1" '
        'w:after="100" w:afterAutospacing="1"/>',
        SPEC_SPACING,
    )

    out = out.replace(
        '<w:spacing w:before="20" w:after="20"/>',
        SPEC_SPACING,
    )

    out = out.replace(
        '<w:spacing w:before="240" w:after="60" w:line="360" w:lineRule="exact"/>',
        SPEC_SPACING,
    )

    out = out.replace(
        "<w:keepLines/><w:jc w:val=\"left\"/><w:outlineLvl w:val=\"1\"/>",
        "<w:keepLines/>"
        + SPEC_SPACING
        + "<w:jc w:val=\"left\"/><w:outlineLvl w:val=\"1\"/>",
    )

    return out


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DST
    if not src.is_file():
        print("Missing:", src)
        return 1
    shutil.copy2(src, dst)
    with zipfile.ZipFile(dst, "r") as zin:
        names = zin.namelist()
        style_names = [n for n in names if n.startswith("word/styles") and n.endswith(".xml")]
        if not style_names:
            print("No word/styles*.xml")
            return 1
        members = [(n, zin.read(n)) for n in names]
    sf = "word/styles.xml" if "word/styles.xml" in names else style_names[0]
    styles_xml = dict(members)[sf].decode("utf-8")
    new_styles = patch_styles_xml(styles_xml)
    if new_styles == styles_xml:
        print("WARN: no replacements matched — check styles.xml spacing markup.")

    fd, tmp = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name, data in members:
                if name == sf:
                    data = new_styles.encode("utf-8")
                zout.writestr(name, data)
        try:
            os.replace(tmp, dst)
        except OSError:
            shutil.copy2(tmp, dst)
            os.remove(tmp)
    finally:
        if os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    print("Wrote:", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
