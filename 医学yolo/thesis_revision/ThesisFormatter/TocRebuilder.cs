using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

/// <summary>
/// Replace the document's existing pre-rendered TOC field content with a freshly empty TOC
/// field. This forces Word / WPS to (re-)evaluate the field on open, picking up every
/// outline-level heading currently in the document, including the newly-inserted
/// "本章小结" sub-sections and "1.3.3 现有研究存在的问题" — which the cached TOC
/// content does not contain.
///
/// Strategy:
///   1. Locate the TOC field by scanning for a Run containing FieldCode/InstrText that
///      starts with " TOC ".
///   2. Walk forward across runs (across paragraphs) until we find the matching
///      FieldChar.End for the TOC.
///   3. Delete EVERY paragraph that consists only of TOC-field machinery + leftover
///      static TOC entries. (Paragraphs whose pStyle is one of the TOC-entry styles or
///      that are inside the TOC field span are removed.)
///   4. In place of the original TOC starter paragraph, insert ONE clean paragraph that
///      contains a self-evaluating TOC field with `\o "1-3" \h \z \u` switches.
/// </summary>
internal static class TocRebuilder
{
    public static void Rebuild(Body body)
    {
        // 1. Find the paragraph that starts the TOC field.
        Paragraph? tocOpenPara = null;
        foreach (var p in body.Elements<Paragraph>())
        {
            foreach (var instr in p.Descendants<FieldCode>())
            {
                if ((instr.Text ?? "").TrimStart().StartsWith("TOC", StringComparison.OrdinalIgnoreCase))
                {
                    tocOpenPara = p;
                    break;
                }
            }
            if (tocOpenPara != null) break;
        }

        if (tocOpenPara == null)
        {
            Console.WriteLine("[WARN] No TOC field found; skipping TOC rebuild.");
            return;
        }

        // 2. Walk forward through paragraphs until we balance the field begin/end markers.
        //    The walk MUST track Begin/End pairs robustly because nested HYPERLINK / PAGEREF
        //    fields are common inside TOC entries.
        var tocParas = new List<Paragraph> { tocOpenPara };
        int depth = 0;
        bool started = false;
        Paragraph? cursor = tocOpenPara;
        // Count begin/end across all paragraphs in scan range.
        while (cursor != null)
        {
            foreach (var fc in cursor.Descendants<FieldChar>())
            {
                if (fc.FieldCharType == null) continue;
                if (fc.FieldCharType.Value == FieldCharValues.Begin)
                {
                    depth++;
                    started = true;
                }
                else if (fc.FieldCharType.Value == FieldCharValues.End)
                {
                    depth--;
                }
            }

            if (started && depth <= 0)
            {
                // The TOC field ended somewhere inside `cursor` (or earlier).
                break;
            }

            var next = cursor.NextSibling<Paragraph>();
            if (next == null) break;
            cursor = next;
            tocParas.Add(cursor);
        }

        // 3. Build the replacement paragraph: a fresh TOC field with auto-update switches.
        //    Use FieldCode (legacy InstructionText element) so older readers also handle it.
        var newToc = new Paragraph();
        var pPr = new ParagraphProperties(
            new ParagraphStyleId { Val = "16" }   // built-in TOC1 style — gives reasonable defaults
        );
        newToc.Append(pPr);

        var run1 = new Run(new FieldChar { FieldCharType = FieldCharValues.Begin, Dirty = OnOffValue.FromBoolean(true) });
        var run2 = new Run(new FieldCode("TOC \\o \"1-3\" \\h \\z \\u ") { Space = SpaceProcessingModeValues.Preserve });
        var run3 = new Run(new FieldChar { FieldCharType = FieldCharValues.Separate });
        // Placeholder text shown until the field is evaluated
        var run4 = new Run(new Text("（请在 Word/WPS 中右键此目录 → 更新域，目录将自动按当前标题与页码重建）")
        { Space = SpaceProcessingModeValues.Preserve });
        var run5 = new Run(new FieldChar { FieldCharType = FieldCharValues.End });

        newToc.Append(run1);
        newToc.Append(run2);
        newToc.Append(run3);
        newToc.Append(run4);
        newToc.Append(run5);

        // 4. Insert the new TOC paragraph before the first old TOC paragraph and remove all old ones.
        tocOpenPara.InsertBeforeSelf(newToc);
        foreach (var p in tocParas)
        {
            p.Remove();
        }
    }
}
