# -*- coding: utf-8 -*-
"""
After apply-template from 烟台理工学院范文, styleId numbers point to different
semantics than the thesis. TOC lines still reference old ids (heading 2/3/4 or
toc 1/2/3 from the thesis package). Remap ONLY paragraphs that contain Word TOC
bookmarks (_Toc...) to the template's toc styles:

  范文: toc 1 -> styleId 23, toc 2 -> 25, toc 3 -> 16

Thesis TOC paragraphs may use: 2 (heading1), 3 (heading2), 4 (heading3),
12 (toc3), 16 (toc1), 18 (toc2).
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

MAP = {
    "2": "23",
    "3": "25",
    "4": "16",
    "12": "16",
    "16": "23",
    "18": "25",
}

PSTYLE_RE = re.compile(r'(<w:pStyle w:val=")([^"]+)(")')


def iter_wp_blocks(xml: str):
    pos = 0
    n = len(xml)
    while pos < n:
        start = xml.find("<w:p ", pos)
        if start < 0:
            start = xml.find("<w:p>", pos)
        if start < 0:
            if pos < n:
                yield xml[pos:], False
            return
        if start > pos:
            yield xml[pos:start], False
        end = xml.find("</w:p>", start)
        if end < 0:
            raise ValueError("Malformed document.xml: missing </w:p>")
        end += len("</w:p>")
        yield xml[start:end], True
        pos = end


def fix_paragraph(p: str) -> tuple[str, bool]:
    if "_Toc" not in p:
        return p, False
    m = PSTYLE_RE.search(p)
    if not m:
        return p, False
    old = m.group(2)
    new = MAP.get(old)
    if not new or new == old:
        return p, False
    return PSTYLE_RE.sub(rf"\g<1>{new}\g<3>", p, count=1), True


def patch_document_xml(xml: str) -> tuple[str, int]:
    out = []
    changed = 0
    for block, is_p in iter_wp_blocks(xml):
        if is_p:
            nb, did = fix_paragraph(block)
            if did:
                changed += 1
            out.append(nb)
        else:
            out.append(block)
    return "".join(out), changed


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: fix_toc_pstyle_ids.py <thesis.docx> [output.docx]")
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + "_tocfix.docx")
    shutil.copy2(src, dst)
    with zipfile.ZipFile(dst, "r") as zin:
        names = zin.namelist()
        has_styles = any(
            n.startswith("word/styles") and n.endswith(".xml") for n in names
        )
        if not has_styles:
            print("ERROR: no word/styles*.xml in package — close Word and use a fresh copy.")
            return 1
        xml = zin.read("word/document.xml").decode("utf-8")
        members = [(n, zin.read(n)) for n in names]
    new_xml, n = patch_document_xml(xml)
    print(f"Remapped pStyle on {n} TOC paragraph(s).")
    fd, tmp = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name, data in members:
                if name == "word/document.xml":
                    data = new_xml.encode("utf-8")
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
