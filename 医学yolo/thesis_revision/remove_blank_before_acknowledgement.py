# -*- coding: utf-8 -*-
"""
删除「参考文献」最后一条与「致谢」之间的空白段落（常见成因：多余空行占满一页）。
"""
from pathlib import Path

from docx import Document


def delete_paragraph(paragraph):
    el = paragraph._element
    el.getparent().remove(el)
    paragraph._p = paragraph._element = None


def strip_empty_before_acknowledgement(doc: Document) -> int:
    ack_para = None
    for p in doc.paragraphs:
        t = p.text.strip()
        if t == "致谢" or (len(t) <= 4 and t.startswith("致谢")):
            ack_para = p
            break
    if ack_para is None:
        raise RuntimeError("未找到「致谢」段落")

    removed = 0
    while True:
        prev_el = ack_para._element.getprevious()
        if prev_el is None:
            break
        local = prev_el.tag.split("}")[-1]
        if local != "p":
            break
        text = "".join(prev_el.itertext())
        if text.strip():
            break
        parent = prev_el.getparent()
        parent.remove(prev_el)
        removed += 1

    return removed


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / "医学骨架30012.docx"
    doc = Document(str(path))
    n = strip_empty_before_acknowledgement(doc)
    try:
        doc.save(str(path))
    except PermissionError:
        alt = path.with_name(path.stem + "_已删空白页.docx")
        doc.save(str(alt))
        print(f"原文档被占用，已保存：{alt}")
        return
    print(f"已删除致谢前连续空段落 {n} 个，已保存：{path}")


if __name__ == "__main__":
    main()
