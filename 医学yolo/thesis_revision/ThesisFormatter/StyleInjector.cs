using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

/// <summary>
/// Inject thesis spec-compliant styles into styles.xml.
/// We use string-based style IDs ("ThesisH1", "ThesisH2", ...) so we don't conflict with
/// the existing numeric IDs in the source document.
/// </summary>
internal static class StyleInjector
{
    public static class Ids
    {
        public const string H1 = "ThesisH1";   // 一级 黑体小二号 居中
        public const string H2 = "ThesisH2";   // 二级 黑体小三号 左对齐
        public const string H3 = "ThesisH3";   // 三级 黑体四号 左对齐
        public const string H4 = "ThesisH4";   // 四级 黑体小四号 左对齐
        public const string Body = "ThesisBody";       // 宋体小四号 18磅 首行2字
        public const string AbsLabel = "ThesisAbsLbl"; // 黑体小四号
        public const string AbsBody = "ThesisAbsBody"; // 宋体小四号 1.5倍行距
        public const string AbsEn = "ThesisAbsEn";     // Abstract: Times New Roman 小四号 加粗
        public const string TocTitle = "ThesisTocTitle"; // 黑体三号 居中 段前段后1行
        public const string Ref = "ThesisRef";          // 参考文献正文 宋体/TNR 小四号
    }

    public static void Inject(StyleDefinitionsPart stylesPart)
    {
        var stylesElem = stylesPart.Styles!;

        Upsert(stylesElem, MakeH1());
        Upsert(stylesElem, MakeH2());
        Upsert(stylesElem, MakeH3());
        Upsert(stylesElem, MakeH4());
        Upsert(stylesElem, MakeBody());
        Upsert(stylesElem, MakeAbsLabel());
        Upsert(stylesElem, MakeAbsBody());
        Upsert(stylesElem, MakeAbsEn());
        Upsert(stylesElem, MakeTocTitle());
        Upsert(stylesElem, MakeRef());

        // Ensure Hyperlink character style exists (style ID "22" already does in source styles.xml,
        // but we need a known reference for new hyperlinks).
        EnsureHyperlinkStyle(stylesElem);
    }

    private static void Upsert(Styles styles, Style style)
    {
        var existing = styles.Elements<Style>().FirstOrDefault(s => s.StyleId?.Value == style.StyleId?.Value);
        if (existing != null) existing.Remove();
        styles.AppendChild(style);
    }

    private static void EnsureHyperlinkStyle(Styles styles)
    {
        if (styles.Elements<Style>().Any(s => s.StyleId?.Value == "Hyperlink")) return;
        // Source already uses styleId "22" for Hyperlink — also expose under conventional ID "Hyperlink"
        var s = new Style
        {
            Type = StyleValues.Character,
            StyleId = "Hyperlink",
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Hyperlink" });
        s.Append(new BasedOn { Val = "21" });
        s.Append(new UIPriority { Val = 99 });
        s.Append(new UnhideWhenUsed());
        s.Append(new StyleRunProperties(
            new Color { Val = "0563C1", ThemeColor = ThemeColorValues.Hyperlink },
            new Underline { Val = UnderlineValues.Single }
        ));
        styles.AppendChild(s);
    }

    // ==================================================================================
    //                                     STYLES
    // ==================================================================================

    // 一级标题 黑体小二号(18pt -> sz="36"), 段前段后0.5行(=120/240 * 0.5 ≈ 100 dxa->but spec says 0.5行
    //         in line units we use 156 lines (50 lines = 156 dxa = 0.5 line). Use beforeLines=50 / afterLines=50.
    //         居中, OutlineLevel=0, basedOn Normal(=1), keepNext, pageBreakBefore for chapter heading.
    private static Style MakeH1()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.H1,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis H1" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = "1" });
        s.Append(new UIPriority { Val = 1 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new KeepNext(),
            new KeepLines(),
            new PageBreakBefore(),
            new SpacingBetweenLines
            {
                BeforeLines = 50,
                AfterLines = 50,
                Line = "440",
                LineRule = LineSpacingRuleValues.Auto
            },
            new Justification { Val = JustificationValues.Center },
            new OutlineLevel { Val = 0 }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "黑体", ComplexScript = "Times New Roman", Hint = FontTypeHintValues.EastAsia },
            new Bold { Val = false },
            new FontSize { Val = "36" },        // 小二号 = 18pt = sz 36 (half-points)
            new FontSizeComplexScript { Val = "36" },
            new Color { Val = "auto" }
        ));
        return s;
    }

    // 二级标题 黑体小三号 (15pt -> sz=30), 段前段后0.5行, 左对齐, OutlineLevel=1
    private static Style MakeH2()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.H2,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis H2" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = "1" });
        s.Append(new UIPriority { Val = 2 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new KeepNext(),
            new KeepLines(),
            new SpacingBetweenLines
            {
                BeforeLines = 50,
                AfterLines = 50,
                Line = "440",
                LineRule = LineSpacingRuleValues.Auto
            },
            new Justification { Val = JustificationValues.Left },
            new OutlineLevel { Val = 1 }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "黑体", ComplexScript = "Times New Roman", Hint = FontTypeHintValues.EastAsia },
            new Bold { Val = false },
            new FontSize { Val = "30" },        // 小三号 = 15pt
            new FontSizeComplexScript { Val = "30" },
            new Color { Val = "auto" }
        ));
        return s;
    }

    // 三级标题 黑体四号 (14pt -> sz=28), 段前段后0.5行, 左对齐, OutlineLevel=2
    private static Style MakeH3()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.H3,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis H3" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = "1" });
        s.Append(new UIPriority { Val = 3 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new KeepNext(),
            new KeepLines(),
            new SpacingBetweenLines
            {
                BeforeLines = 50,
                AfterLines = 50,
                Line = "440",
                LineRule = LineSpacingRuleValues.Auto
            },
            new Justification { Val = JustificationValues.Left },
            new OutlineLevel { Val = 2 }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "黑体", ComplexScript = "Times New Roman", Hint = FontTypeHintValues.EastAsia },
            new Bold { Val = false },
            new FontSize { Val = "28" },
            new FontSizeComplexScript { Val = "28" },
            new Color { Val = "auto" }
        ));
        return s;
    }

    // 四级标题 黑体小四号 (12pt -> sz=24), 段前段后0.5行, 左对齐, OutlineLevel=3
    private static Style MakeH4()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.H4,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis H4" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = "1" });
        s.Append(new UIPriority { Val = 4 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new KeepNext(),
            new KeepLines(),
            new SpacingBetweenLines
            {
                BeforeLines = 50,
                AfterLines = 50,
                Line = "440",
                LineRule = LineSpacingRuleValues.Auto
            },
            new Justification { Val = JustificationValues.Left },
            new OutlineLevel { Val = 3 }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "黑体", ComplexScript = "Times New Roman", Hint = FontTypeHintValues.EastAsia },
            new Bold { Val = false },
            new FontSize { Val = "24" },
            new FontSizeComplexScript { Val = "24" },
            new Color { Val = "auto" }
        ));
        return s;
    }

    // 正文 宋体小四号(12pt = sz24), 行间距18磅(=固定360 dxa, lineRule=exact line=360),
    //      首行空两个字符(firstLineChars=200), 两端对齐
    private static Style MakeBody()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.Body,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis Body" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = Ids.Body });
        s.Append(new UIPriority { Val = 5 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new SpacingBetweenLines
            {
                After = "0",
                Line = "360",
                LineRule = LineSpacingRuleValues.Exact
            },
            new Indentation { FirstLineChars = 200 },
            new Justification { Val = JustificationValues.Both }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "宋体", ComplexScript = "Times New Roman", Hint = FontTypeHintValues.EastAsia },
            new FontSize { Val = "24" },
            new FontSizeComplexScript { Val = "24" }
        ));
        return s;
    }

    // 摘要标识 [摘 要]: 黑体小四号 左对齐
    private static Style MakeAbsLabel()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.AbsLabel,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis Abs Label" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = Ids.AbsBody });
        s.Append(new UIPriority { Val = 6 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new SpacingBetweenLines
            {
                After = "120",
                Line = "360",
                LineRule = LineSpacingRuleValues.Auto
            },
            new Justification { Val = JustificationValues.Left }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "黑体", ComplexScript = "Times New Roman", Hint = FontTypeHintValues.EastAsia },
            new FontSize { Val = "24" },
            new FontSizeComplexScript { Val = "24" }
        ));
        return s;
    }

    // 摘要正文: 宋体小四号 1.5倍行距
    private static Style MakeAbsBody()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.AbsBody,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis Abs Body" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = Ids.AbsBody });
        s.Append(new UIPriority { Val = 7 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new SpacingBetweenLines
            {
                After = "0",
                Line = "360",
                LineRule = LineSpacingRuleValues.Auto
            },
            new Indentation { FirstLineChars = 200 },
            new Justification { Val = JustificationValues.Both }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "宋体", ComplexScript = "Times New Roman", Hint = FontTypeHintValues.EastAsia },
            new FontSize { Val = "24" },
            new FontSizeComplexScript { Val = "24" }
        ));
        return s;
    }

    // 英文摘要 Abstract: Times New Roman 小四号 加粗 左对齐
    private static Style MakeAbsEn()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.AbsEn,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis Abs En" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = Ids.AbsEn });
        s.Append(new UIPriority { Val = 8 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new SpacingBetweenLines
            {
                After = "0",
                Line = "360",
                LineRule = LineSpacingRuleValues.Auto
            },
            new Justification { Val = JustificationValues.Left }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "Times New Roman", ComplexScript = "Times New Roman" },
            new FontSize { Val = "24" },
            new FontSizeComplexScript { Val = "24" }
        ));
        return s;
    }

    // 目录标题 黑体三号(16pt->sz32), 居中, 段前段后1行
    private static Style MakeTocTitle()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.TocTitle,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis TOC Title" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = "1" });
        s.Append(new UIPriority { Val = 9 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new SpacingBetweenLines
            {
                BeforeLines = 100,
                AfterLines = 100,
                Line = "440",
                LineRule = LineSpacingRuleValues.Auto
            },
            new Justification { Val = JustificationValues.Center }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "黑体", ComplexScript = "Times New Roman", Hint = FontTypeHintValues.EastAsia },
            new FontSize { Val = "32" },
            new FontSizeComplexScript { Val = "32" }
        ));
        return s;
    }

    // 参考文献正文 宋体小四号
    private static Style MakeRef()
    {
        var s = new Style
        {
            Type = StyleValues.Paragraph,
            StyleId = Ids.Ref,
            CustomStyle = true
        };
        s.Append(new StyleName { Val = "Thesis Reference" });
        s.Append(new BasedOn { Val = "1" });
        s.Append(new NextParagraphStyle { Val = Ids.Ref });
        s.Append(new UIPriority { Val = 10 });
        s.Append(new PrimaryStyle());
        s.Append(new StyleParagraphProperties(
            new SpacingBetweenLines
            {
                After = "0",
                Line = "360",
                LineRule = LineSpacingRuleValues.Auto
            },
            new Justification { Val = JustificationValues.Both }
        ));
        s.Append(new StyleRunProperties(
            new RunFonts { Ascii = "Times New Roman", HighAnsi = "Times New Roman",
                EastAsia = "宋体", ComplexScript = "Times New Roman", Hint = FontTypeHintValues.EastAsia },
            new FontSize { Val = "24" },
            new FontSizeComplexScript { Val = "24" }
        ));
        return s;
    }
}
