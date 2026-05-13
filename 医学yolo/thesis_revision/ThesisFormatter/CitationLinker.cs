using System.Text.RegularExpressions;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

/// <summary>
/// Convert in-text citations like [1], [6], [12] (whether superscript or plain inline)
/// into clickable internal hyperlinks pointing to bookmarks at each reference list entry.
///
/// Steps:
///   1. Walk all reference list paragraphs ([N] ...) and add bookmarks "ref_N" at the start.
///   2. Walk all body paragraphs (excluding refs/ack/TOC/cover/abstract zones) and replace
///      [N] occurrences in any text run with a Hyperlink anchor referencing "ref_N".
/// </summary>
internal static class CitationLinker
{
    private static readonly Regex CitePattern = new(@"\[(\d{1,3})\]", RegexOptions.Compiled);
    private static readonly Regex RefStart = new(@"^\s*\[(\d{1,3})\]\s", RegexOptions.Compiled);

    public static void Process(Body body, ZoneInfo zones)
    {
        if (zones.RefBodyStart < 0 || zones.RefBodyEnd < 0) return;

        // Re-resolve paragraphs (insertion of summaries shifted indices), so just rebuild.
        var allParas = body.Elements<Paragraph>().ToList();

        // 1. Find reference paragraphs by matching [N] start.
        var refIdToPara = new Dictionary<int, Paragraph>();
        foreach (var p in allParas)
        {
            string s = ZoneClassifier.GetText(p).Trim();
            var m = RefStart.Match(s);
            if (!m.Success) continue;
            // Only consider as a reference if the paragraph is "long-ish" (not an inline citation)
            if (s.Length < 20) continue;
            int n = int.Parse(m.Groups[1].Value);
            // Add bookmark only if not already present.
            if (!refIdToPara.ContainsKey(n))
            {
                refIdToPara[n] = p;
            }
        }

        int bookmarkId = 1000;
        foreach (var (n, p) in refIdToPara.OrderBy(kv => kv.Key))
        {
            string bookmarkName = $"ref_{n}";
            // Skip if already bookmarked
            if (p.Descendants<BookmarkStart>().Any(bs => bs.Name?.Value == bookmarkName)) continue;

            string idStr = bookmarkId.ToString();
            var bmStart = new BookmarkStart { Id = idStr, Name = bookmarkName };
            var bmEnd = new BookmarkEnd { Id = idStr };

            // CRITICAL: BookmarkStart/End MUST come AFTER w:pPr to satisfy element order rules.
            // Inserting at index 0 would push pPr down and corrupt the paragraph structure,
            // which is what causes WPS to fail to navigate to the anchor.
            var pPr = p.GetFirstChild<ParagraphProperties>();
            if (pPr != null)
            {
                pPr.InsertAfterSelf(bmEnd);
                pPr.InsertAfterSelf(bmStart);  // appears between pPr and bmEnd because InsertAfterSelf prepends
            }
            else
            {
                p.PrependChild(bmEnd);
                p.PrependChild(bmStart);
            }
            bookmarkId++;
        }

        // 2. Identify body-zone paragraphs to process. We use simple criterion: paragraphs that
        //    are NOT reference list paragraphs (i.e. don't match RefStart with length>20),
        //    AND are NOT cover/TOC entries.
        // To keep it simple, process every paragraph that is not a reference list entry, not in TOC.
        var refParaSet = new HashSet<Paragraph>(refIdToPara.Values);

        // TOC paragraph anchors: paragraphs containing fldChar with 'TOC' fields - safer to skip them by checking pStyle.
        foreach (var p in allParas)
        {
            if (refParaSet.Contains(p)) continue;
            var styleId = p.GetFirstChild<ParagraphProperties>()?.GetFirstChild<ParagraphStyleId>()?.Val?.Value;
            // Skip TOC paragraphs (built-in TOC styles 12/16/18 in this file)
            if (styleId == "12" || styleId == "16" || styleId == "18") continue;
            // Skip TOC title paragraph
            if (styleId == StyleInjector.Ids.TocTitle) continue;

            // Pre-pass: stitch together broken citations that span 2+ runs
            // (e.g. "[6][9" in one superscript run followed by "]" in a non-superscript run).
            StitchBrokenCitations(p);

            ConvertCitationsInParagraph(p, refIdToPara.Keys.ToHashSet());
        }
    }

    /// <summary>
    /// Repair citation-bracket sequences that were split across adjacent runs.
    /// For each paragraph, walk through Text elements and look for a Text whose content
    /// ends with an unmatched "[N" (open bracket + digits, no closing bracket), where
    /// the next Text starts with "]" or "][N]" etc. Move the "]" into the previous run
    /// so that the bracket is complete and citation-conversion can pick it up.
    /// </summary>
    private static void StitchBrokenCitations(Paragraph p)
    {
        var texts = p.Descendants<Text>().ToList();
        for (int i = 0; i < texts.Count - 1; i++)
        {
            var cur = texts[i];
            var nxt = texts[i + 1];
            string a = cur.Text ?? "";
            string b = nxt.Text ?? "";
            if (string.IsNullOrEmpty(a) || string.IsNullOrEmpty(b)) continue;

            // Match pattern: a ends with "[N" (no ']') and b starts with "]"
            var m = Regex.Match(a, @"\[\d{1,3}$");
            if (!m.Success) continue;
            if (!b.StartsWith("]")) continue;

            cur.Text = a + "]";
            cur.Space = SpaceProcessingModeValues.Preserve;
            nxt.Text = b.Substring(1);
            nxt.Space = SpaceProcessingModeValues.Preserve;
        }
    }

    private static void ConvertCitationsInParagraph(Paragraph p, HashSet<int> validRefs)
    {
        // We process each Run that contains [N] in its Text. For each [N], split the run and
        // wrap the [N] in a Hyperlink with Anchor = "ref_N".
        var runs = p.Elements<Run>().ToList();
        foreach (var run in runs)
        {
            var textElems = run.Elements<Text>().ToList();
            if (textElems.Count == 0) continue;

            // Combine all text in the run (most runs have a single text element).
            string combined = string.Concat(textElems.Select(t => t.Text ?? ""));
            if (!CitePattern.IsMatch(combined)) continue;

            // Determine whether this run is already a "superscript citation" run.
            var rPr = run.GetFirstChild<RunProperties>();
            bool isSuperscript = rPr?.GetFirstChild<VerticalTextAlignment>()?.Val?.Value == VerticalPositionValues.Superscript;

            // Find all matches and convert this single run into multiple new elements.
            var matches = CitePattern.Matches(combined);
            int cursor = 0;
            var replacement = new List<OpenXmlElement>();

            foreach (Match m in matches)
            {
                if (m.Index > cursor)
                {
                    string before = combined.Substring(cursor, m.Index - cursor);
                    replacement.Add(BuildPlainRun(rPr, before, isSuperscript));
                }

                int n = int.Parse(m.Groups[1].Value);
                if (validRefs.Contains(n))
                {
                    replacement.Add(BuildHyperlinkRun($"ref_{n}", m.Value, rPr));
                }
                else
                {
                    // Unknown ref number: leave plain text
                    replacement.Add(BuildPlainRun(rPr, m.Value, isSuperscript));
                }
                cursor = m.Index + m.Length;
            }

            if (cursor < combined.Length)
            {
                string after = combined.Substring(cursor);
                replacement.Add(BuildPlainRun(rPr, after, isSuperscript));
            }

            // Insert replacement elements before the original run, then remove the run.
            foreach (var elem in replacement)
            {
                run.InsertBeforeSelf(elem);
            }
            run.Remove();
        }
    }

    private static Run BuildPlainRun(RunProperties? originalRPr, string text, bool isSuperscript)
    {
        var run = new Run();
        var rPr = (RunProperties?)originalRPr?.CloneNode(true) ?? new RunProperties();
        // Ensure superscript stays if the original was superscript
        if (isSuperscript)
        {
            if (rPr.GetFirstChild<VerticalTextAlignment>() == null)
            {
                rPr.AppendChild(new VerticalTextAlignment { Val = VerticalPositionValues.Superscript });
            }
        }
        if (rPr.HasChildren) run.AppendChild(rPr);
        run.AppendChild(new Text(text) { Space = SpaceProcessingModeValues.Preserve });
        return run;
    }

    /// <summary>
    /// Build a Hyperlink containing a Run with [N] superscripted and styled as a hyperlink.
    /// Always make the citation superscript regardless of the source run, per academic convention.
    /// </summary>
    private static Hyperlink BuildHyperlinkRun(string anchor, string text, RunProperties? originalRPr)
    {
        var hyperlink = new Hyperlink { Anchor = anchor, History = OnOffValue.FromBoolean(true) };

        var run = new Run();
        // Build clean RunProperties: hyperlink style + superscript + Times New Roman small four
        var rPr = new RunProperties();
        rPr.AppendChild(new RunStyle { Val = "Hyperlink" });
        rPr.AppendChild(new RunFonts
        {
            Ascii = "Times New Roman",
            HighAnsi = "Times New Roman",
            EastAsia = "宋体",
            ComplexScript = "Times New Roman"
        });
        rPr.AppendChild(new Color { Val = "0563C1", ThemeColor = ThemeColorValues.Hyperlink });
        rPr.AppendChild(new Underline { Val = UnderlineValues.Single });
        rPr.AppendChild(new VerticalTextAlignment { Val = VerticalPositionValues.Superscript });
        run.AppendChild(rPr);
        run.AppendChild(new Text(text) { Space = SpaceProcessingModeValues.Preserve });

        hyperlink.AppendChild(run);
        return hyperlink;
    }
}
