using System.Text.RegularExpressions;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

/// <summary>
/// Apply per-paragraph styles to the body based on zone classification.
/// </summary>
internal static class ParagraphFormatter
{
    private static readonly Regex L4 = new(@"^\s*\d+\.\d+\.\d+\.\d+\s", RegexOptions.Compiled);
    private static readonly Regex L3 = new(@"^\s*\d+\.\d+\.\d+\s+[^\d\.]", RegexOptions.Compiled);
    private static readonly Regex L2 = new(@"^\s*\d+\.\d+\s+[^\d\.]", RegexOptions.Compiled);
    private static readonly Regex Ch = new(@"^\s*\d+\s+[^\d\.]", RegexOptions.Compiled);
    private static readonly Regex RefLine = new(@"^\s*\[\d+\]\s", RegexOptions.Compiled);

    public static void Apply(Body body, ZoneInfo zones)
    {
        for (int i = 0; i < zones.Paragraphs.Count; i++)
        {
            var p = zones.Paragraphs[i];
            var s = zones.Texts[i].Trim();

            // Skip cover page paragraphs entirely (do nothing) - paragraphs 0..CoverEnd
            if (zones.CoverEnd >= 0 && i <= zones.CoverEnd) continue;

            // Cover -> abstract: leave existing simple format mostly,
            // but for the abstract title and keyword title paragraphs we apply a label style.
            if (zones.AbstractCnStart >= 0 && i == zones.AbstractCnStart)
            {
                // The chinese abstract paragraph contains both the [摘 要] label run AND the body run.
                // We apply abstract body style and then make sure the first run keeps 黑体.
                ApplyParagraphStyle(p, StyleInjector.Ids.AbsBody);
                continue;
            }
            // Keywords paragraph (Chinese)
            if (zones.AbstractCnStart >= 0 && i > zones.AbstractCnStart && i < (zones.AbstractEnStart >= 0 ? zones.AbstractEnStart : i + 1))
            {
                if (s.StartsWith("[关键词") || s.StartsWith("【关键词"))
                {
                    ApplyParagraphStyle(p, StyleInjector.Ids.AbsBody);
                    continue;
                }
            }
            // English abstract & keywords
            if (zones.AbstractEnStart >= 0 && i >= zones.AbstractEnStart && i <= (zones.AbstractEnEnd >= 0 ? zones.AbstractEnEnd : i))
            {
                ApplyParagraphStyle(p, StyleInjector.Ids.AbsEn);
                continue;
            }

            // 目录 title
            if (zones.TocTitleIdx >= 0 && i == zones.TocTitleIdx)
            {
                ApplyParagraphStyle(p, StyleInjector.Ids.TocTitle);
                continue;
            }

            // TOC body — use existing TOC styles 16/18/12; we leave them as-is but
            // adjust to stable size 24.
            if (zones.TocBodyStart >= 0 && i >= zones.TocBodyStart &&
                zones.TocBodyEnd >= 0 && i <= zones.TocBodyEnd)
            {
                NormalizeTocEntry(p);
                continue;
            }

            // Body zone
            if (zones.BodyStart >= 0 && i >= zones.BodyStart &&
                zones.BodyEnd >= 0 && i <= zones.BodyEnd)
            {
                if (string.IsNullOrWhiteSpace(s))
                {
                    // empty paragraph: keep as-is but normalize line spacing
                    continue;
                }
                if (L4.IsMatch(s))
                {
                    ApplyParagraphStyle(p, StyleInjector.Ids.H4);
                }
                else if (L3.IsMatch(s))
                {
                    ApplyParagraphStyle(p, StyleInjector.Ids.H3);
                }
                else if (L2.IsMatch(s))
                {
                    ApplyParagraphStyle(p, StyleInjector.Ids.H2);
                }
                else if (Ch.IsMatch(s))
                {
                    // Chapter heading
                    ApplyParagraphStyle(p, StyleInjector.Ids.H1);
                    // Make sure pageBreakBefore is preserved
                    EnsurePageBreakBefore(p);
                }
                else
                {
                    ApplyParagraphStyle(p, StyleInjector.Ids.Body);
                }
                continue;
            }

            // 参考文献 title
            if (zones.RefTitleIdx >= 0 && i == zones.RefTitleIdx)
            {
                ApplyParagraphStyle(p, StyleInjector.Ids.H1);
                EnsurePageBreakBefore(p);
                continue;
            }

            // References body
            if (zones.RefBodyStart >= 0 && i >= zones.RefBodyStart &&
                zones.RefBodyEnd >= 0 && i <= zones.RefBodyEnd)
            {
                ApplyParagraphStyle(p, StyleInjector.Ids.Ref);
                continue;
            }

            // 致谢 title + body
            if (zones.AckTitleIdx >= 0 && i == zones.AckTitleIdx)
            {
                ApplyParagraphStyle(p, StyleInjector.Ids.H1);
                EnsurePageBreakBefore(p);
                continue;
            }
            if (zones.AckBodyStart >= 0 && i >= zones.AckBodyStart &&
                zones.AckBodyEnd >= 0 && i <= zones.AckBodyEnd)
            {
                if (!string.IsNullOrWhiteSpace(s))
                {
                    ApplyParagraphStyle(p, StyleInjector.Ids.Body);
                }
                continue;
            }
        }
    }

    /// <summary>
    /// Replace the paragraph's pStyle, strip direct paragraph-level formatting overrides
    /// that conflict with the new style, and clean inline rPr fonts/sizes that override style.
    /// </summary>
    private static void ApplyParagraphStyle(Paragraph p, string styleId)
    {
        var pPr = p.GetFirstChild<ParagraphProperties>();
        if (pPr == null)
        {
            pPr = new ParagraphProperties();
            p.PrependChild(pPr);
        }

        // Remove existing pStyle and add new one as the FIRST child.
        var oldStyle = pPr.GetFirstChild<ParagraphStyleId>();
        oldStyle?.Remove();
        pPr.PrependChild(new ParagraphStyleId { Val = styleId });

        // Clean conflicting direct paragraph properties so the style takes effect.
        // We keep: pageBreakBefore, sectPr, bookmarks (those aren't pPr children), tabs (for TOC).
        RemoveAll<Justification>(pPr);
        RemoveAll<Indentation>(pPr);
        RemoveAll<SpacingBetweenLines>(pPr);
        // Don't remove pageBreakBefore - sometimes carried from source.

        // Clean direct run-level fonts/colors/sizes.
        foreach (var run in p.Elements<Run>())
        {
            var rPr = run.GetFirstChild<RunProperties>();
            if (rPr == null) continue;
            // Remove fonts (direct override); colors; sizes; bold; italic; emphasis. Keep vertAlign for citations.
            RemoveAll<RunFonts>(rPr);
            RemoveAll<FontSize>(rPr);
            RemoveAll<FontSizeComplexScript>(rPr);
            RemoveAll<Color>(rPr);
            RemoveAll<Bold>(rPr);
            RemoveAll<BoldComplexScript>(rPr);
            RemoveAll<Italic>(rPr);
            RemoveAll<ItalicComplexScript>(rPr);
            RemoveAll<Kern>(rPr);
        }
    }

    private static void NormalizeTocEntry(Paragraph p)
    {
        // Existing TOC entries already use pStyle 16/18/12. Just remove any inline font size overrides
        // smaller than 24 to ensure 小四 appearance.
        foreach (var run in p.Elements<Run>())
        {
            var rPr = run.GetFirstChild<RunProperties>();
            if (rPr == null) continue;
            RemoveAll<FontSize>(rPr);
            RemoveAll<FontSizeComplexScript>(rPr);
        }
    }

    private static void EnsurePageBreakBefore(Paragraph p)
    {
        var pPr = p.GetFirstChild<ParagraphProperties>();
        if (pPr == null) return;
        if (!pPr.Elements<PageBreakBefore>().Any())
        {
            pPr.AppendChild(new PageBreakBefore());
        }
    }

    private static void RemoveAll<T>(OpenXmlElement parent) where T : OpenXmlElement
    {
        foreach (var e in parent.Elements<T>().ToList()) e.Remove();
    }
}
