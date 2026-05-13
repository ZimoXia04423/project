using System.Text.RegularExpressions;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

internal sealed class ZoneInfo
{
    public List<Paragraph> Paragraphs { get; } = new();
    public List<string> Texts { get; } = new();

    // Boundaries (inclusive paragraph indices into Paragraphs list)
    public int CoverEnd = -1;          // last index of cover (the "烟台理工学院" page-break para)
    public int AbstractCnStart = -1;   // [摘  要] start
    public int AbstractCnEnd = -1;     // last keyword paragraph
    public int AbstractEnStart = -1;   // Abstract: start
    public int AbstractEnEnd = -1;     // Key words end
    public int TocTitleIdx = -1;       // 目录 title
    public int TocBodyStart = -1;
    public int TocBodyEnd = -1;
    public int BodyStart = -1;          // first chapter heading "1 ..."
    public int BodyEnd = -1;            // last paragraph before references
    public int RefTitleIdx = -1;        // 参考文献 title (may be inserted later)
    public int RefBodyStart = -1;       // [1] ... starts
    public int RefBodyEnd = -1;         // [N] ... ends
    public int AckTitleIdx = -1;        // 致谢
    public int AckBodyStart = -1;
    public int AckBodyEnd = -1;

    public List<int> ChapterHeadingIdx { get; } = new(); // indices of "N 标题"
    public List<int> Level2Idx { get; } = new(); // N.N
    public List<int> Level3Idx { get; } = new(); // N.N.N
    public List<int> Level4Idx { get; } = new(); // N.N.N.N

    public void Print()
    {
        Console.WriteLine($"  total paragraphs        = {Paragraphs.Count}");
        Console.WriteLine($"  cover end               = {CoverEnd}");
        Console.WriteLine($"  abstract zh             = [{AbstractCnStart}, {AbstractCnEnd}]");
        Console.WriteLine($"  abstract en             = [{AbstractEnStart}, {AbstractEnEnd}]");
        Console.WriteLine($"  toc title               = {TocTitleIdx}, body=[{TocBodyStart}, {TocBodyEnd}]");
        Console.WriteLine($"  body                    = [{BodyStart}, {BodyEnd}]");
        Console.WriteLine($"  references title        = {RefTitleIdx}, body=[{RefBodyStart}, {RefBodyEnd}]");
        Console.WriteLine($"  acknowledgements        = {AckTitleIdx}, body=[{AckBodyStart}, {AckBodyEnd}]");
        Console.WriteLine($"  chapter headings count  = {ChapterHeadingIdx.Count}");
        Console.WriteLine($"  L2 / L3 / L4 counts     = {Level2Idx.Count} / {Level3Idx.Count} / {Level4Idx.Count}");
    }
}

internal static class ZoneClassifier
{
    private static readonly Regex ChapterHeading = new(@"^\s*(\d+)\s+[^\d\.]", RegexOptions.Compiled);
    private static readonly Regex L2Heading = new(@"^\s*\d+\.\d+\s+[^\d\.]", RegexOptions.Compiled);
    private static readonly Regex L3Heading = new(@"^\s*\d+\.\d+\.\d+\s+[^\d\.]", RegexOptions.Compiled);
    private static readonly Regex L4Heading = new(@"^\s*\d+\.\d+\.\d+\.\d+\s", RegexOptions.Compiled);
    private static readonly Regex RefLine = new(@"^\s*\[\d+\]\s", RegexOptions.Compiled);

    public static ZoneInfo Classify(Body body)
    {
        var zones = new ZoneInfo();
        foreach (var p in body.Elements<Paragraph>())
        {
            zones.Paragraphs.Add(p);
            zones.Texts.Add(GetText(p));
        }

        var t = zones.Texts;
        var styleIds = zones.Paragraphs.Select(GetStyleId).ToList();

        for (int i = 0; i < t.Count; i++)
        {
            var s = t[i].Trim();

            // Cover: ends at "烟台理工学院" right before the abstract
            if (zones.CoverEnd < 0 && s.Contains("烟台理工学院") &&
                i > 0 && i < 20 && i + 1 < t.Count &&
                (t[i + 1].Contains("摘") || t[i + 1].Contains("[摘") || t[i + 1].Contains("【摘")))
            {
                zones.CoverEnd = i;
            }

            // Chinese abstract title
            if (zones.AbstractCnStart < 0 && (s.StartsWith("[摘") || s.StartsWith("【摘") || s.Contains("摘  要]") || s.Contains("摘 要]")))
            {
                zones.AbstractCnStart = i;
            }

            // English abstract start
            if (zones.AbstractEnStart < 0 && Regex.IsMatch(s, @"^\s*Abstract\s*[:：]"))
            {
                zones.AbstractEnStart = i;
                if (zones.AbstractCnEnd < 0 && i > 0) zones.AbstractCnEnd = i - 1;
            }

            // Key words end of english abstract block
            if (zones.AbstractEnEnd < 0 && zones.AbstractEnStart >= 0 &&
                Regex.IsMatch(s, @"^\s*Key\s*words\s*[:：]"))
            {
                zones.AbstractEnEnd = i;
            }

            // 目录 title
            if (zones.TocTitleIdx < 0 && Regex.IsMatch(s, @"^目\s*录\s*$"))
            {
                zones.TocTitleIdx = i;
                zones.TocBodyStart = i + 1;
            }

            // First body chapter — must NOT be a TOC entry. Use pStyle to filter.
            if (zones.BodyStart < 0 && ChapterHeading.IsMatch(s) && !IsTocStyle(styleIds[i]))
            {
                bool likelyBody = zones.TocTitleIdx >= 0 && i > zones.TocTitleIdx + 1;
                if (likelyBody)
                {
                    zones.BodyStart = i;
                    if (zones.TocBodyEnd < 0) zones.TocBodyEnd = i - 1;
                }
            }

            // 参考文献 title (might exist, might not)
            if (zones.RefTitleIdx < 0 && Regex.IsMatch(s, @"^参\s*考\s*文\s*献\s*$"))
            {
                zones.RefTitleIdx = i;
            }

            // First reference [1] ... line
            if (zones.RefBodyStart < 0 && RefLine.IsMatch(s) && zones.BodyStart >= 0 && i > zones.BodyStart + 50)
            {
                // Distinguish from inline citations: this whole paragraph starts with [N] and looks like a long ref
                if (s.Length > 30 && Regex.IsMatch(s, @"^\s*\[1\]\s"))
                {
                    zones.RefBodyStart = i;
                }
            }

            // 致谢 title
            if (zones.AckTitleIdx < 0 && Regex.IsMatch(s, @"^致\s*谢\s*$"))
            {
                zones.AckTitleIdx = i;
                zones.AckBodyStart = i + 1;
                zones.AckBodyEnd = t.Count - 1;
            }
        }

        // Compute references body end and ack start
        if (zones.RefBodyStart >= 0)
        {
            int last = zones.RefBodyStart;
            for (int i = zones.RefBodyStart; i < t.Count; i++)
            {
                var s = t[i].Trim();
                if (s.StartsWith("致谢") || (zones.AckTitleIdx >= 0 && i >= zones.AckTitleIdx))
                {
                    break;
                }
                if (RefLine.IsMatch(s)) last = i;
            }
            zones.RefBodyEnd = last;
        }

        // Body end (before references)
        if (zones.BodyStart >= 0)
        {
            int end = (zones.RefTitleIdx > 0) ? zones.RefTitleIdx - 1
                      : (zones.RefBodyStart > 0 ? zones.RefBodyStart - 1
                      : (zones.AckTitleIdx > 0 ? zones.AckTitleIdx - 1
                      : t.Count - 1));
            zones.BodyEnd = end;
        }

        // Build chapter heading lists in body zone (skip TOC-styled entries just in case).
        if (zones.BodyStart >= 0 && zones.BodyEnd >= zones.BodyStart)
        {
            for (int i = zones.BodyStart; i <= zones.BodyEnd; i++)
            {
                if (IsTocStyle(styleIds[i])) continue;
                var s = t[i].Trim();
                if (L4Heading.IsMatch(s)) zones.Level4Idx.Add(i);
                else if (L3Heading.IsMatch(s)) zones.Level3Idx.Add(i);
                else if (L2Heading.IsMatch(s)) zones.Level2Idx.Add(i);
                else if (ChapterHeading.IsMatch(s) && !IsLikelyNotChapter(s)) zones.ChapterHeadingIdx.Add(i);
            }
        }

        return zones;
    }

    private static bool IsTocStyle(string? styleId)
    {
        // TOC paragraph styles in this document: 12=toc3, 16=toc1, 18=toc2.
        // Also our own ThesisTocTitle.
        return styleId is "12" or "16" or "18" or StyleInjector.Ids.TocTitle;
    }

    private static bool IsLikelyNotChapter(string s)
    {
        // Filter false positives like "16 GB", "5 系统实现 17" (TOC entries with page number),
        // by requiring NO trailing digit after Chinese characters.
        // Also exclude pure unit lines like "16 GB", "8 GB", etc.
        if (Regex.IsMatch(s, @"^\d+\s+(GB|MB|KB|TB|MHz|GHz|cm|mm|kg|m|min|s|fps)\b", RegexOptions.IgnoreCase))
            return true;
        // TOC-like trailing page number: "1 绪论 6" — the simplest heuristic is reject if string ends with isolated digits.
        if (Regex.IsMatch(s, @"\s+\d+\s*$"))
            return true;
        return false;
    }

    private static string? GetStyleId(Paragraph p)
    {
        return p.GetFirstChild<ParagraphProperties>()?.GetFirstChild<ParagraphStyleId>()?.Val?.Value;
    }

    public static string GetText(Paragraph p)
    {
        var sb = new System.Text.StringBuilder();
        foreach (var t in p.Descendants<Text>()) sb.Append(t.Text);
        return sb.ToString();
    }
}
