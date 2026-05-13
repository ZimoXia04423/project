using System.Text.RegularExpressions;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

/// <summary>
/// Insert "参考文献" title before the first [N] entry, if missing.
/// </summary>
internal static class ReferencesFormatter
{
    public static void Insert(Body body, ZoneInfo zones)
    {
        if (zones.RefBodyStart < 0) return;

        // If we already have a "参考文献" title within 5 paragraphs before the first [1] line,
        // don't insert another one.
        bool found = false;
        for (int j = Math.Max(0, zones.RefBodyStart - 5); j < zones.RefBodyStart; j++)
        {
            if (Regex.IsMatch(zones.Texts[j].Trim(), @"^参\s*考\s*文\s*献\s*$"))
            {
                found = true;
                break;
            }
        }
        if (found) return;

        // Build new heading paragraph.
        var heading = new Paragraph();
        heading.AppendChild(new ParagraphProperties(
            new ParagraphStyleId { Val = StyleInjector.Ids.H1 }
        ));
        heading.AppendChild(new Run(new Text("参考文献")
        {
            Space = DocumentFormat.OpenXml.SpaceProcessingModeValues.Preserve
        }));

        // Insert before [1] paragraph.
        var anchor = zones.Paragraphs[zones.RefBodyStart];
        anchor.InsertBeforeSelf(heading);
    }
}
