using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

/// <summary>
/// Configure two sections:
///   Section 1: cover → abstract → TOC. No header. No page numbering.
///   Section 2: body (从绪论起) → references → 致谢. Header "烟台理工学院毕业论文（设计）"
///              (隶书 3号 居中). Footer with Arabic page numbers (小五号 居中) starting at 1.
///
/// Approach:
///   - Insert a paragraph immediately BEFORE the first chapter heading paragraph that contains
///     an empty body but pPr with sectPr describing section 1's settings (no headers/footers,
///     type=nextPage). This "ends" section 1 there.
///   - Modify the existing trailing sectPr (last child of body) to:
///       * Reference the new header part (with 烟台理工学院毕业论文（设计） text)
///       * Reference the new footer part (with PAGE field)
///       * pgNumType { Start = 1 }
///       * Same page size & margins (per 规范): top=3cm, bottom=2.5cm, left=2.5cm, right=2cm,
///         header=2cm, footer=1.75cm
/// </summary>
internal static class HeaderFooterSetup
{
    // DXA conversions: 1cm ≈ 567 dxa (more precisely 566.929)
    private const int Cm3_0 = 1701;   // 3cm top
    private const int Cm2_5 = 1417;   // 2.5cm bottom/left
    private const int Cm2_0 = 1134;   // 2cm right
    private const int Cm2_0_Hdr = 1134; // header distance
    private const int Cm1_75 = 992;   // footer distance

    public static void Setup(MainDocumentPart mainPart, Body body, ZoneInfo zones)
    {
        // 1. Re-resolve paragraph list (after insertions of summaries / refs heading).
        var allParas = body.Elements<Paragraph>().ToList();

        // 2. Find the BODY chapter-1 heading paragraph. We MUST skip TOC entries that also
        //    contain "1 绪论" — otherwise the section break gets inserted before the TOC,
        //    which throws TOC content into Section 2 and shifts every page number by the
        //    length of the TOC. Body heading uses ThesisH1 style after ParagraphFormatter ran.
        Paragraph? firstChapterPara = null;
        foreach (var p in allParas)
        {
            var styleId = p.GetFirstChild<ParagraphProperties>()?.GetFirstChild<ParagraphStyleId>()?.Val?.Value;
            // Skip TOC paragraphs (built-in TOC styles 12/16/18 and our TOC title)
            if (styleId is "12" or "16" or "18" or StyleInjector.Ids.TocTitle) continue;
            // Body chapter heading must be ThesisH1
            if (styleId != StyleInjector.Ids.H1) continue;
            string s = ZoneClassifier.GetText(p).Trim();
            if (System.Text.RegularExpressions.Regex.IsMatch(s, @"^1\s+绪论"))
            {
                firstChapterPara = p;
                break;
            }
        }
        if (firstChapterPara == null)
        {
            Console.WriteLine("[WARN] Could not find chapter 1 heading; skipping section split.");
            return;
        }

        // 3. Remove any existing header/footer parts and rebuild.
        var existingHeaders = mainPart.HeaderParts.ToList();
        foreach (var hp in existingHeaders) mainPart.DeletePart(hp);
        var existingFooters = mainPart.FooterParts.ToList();
        foreach (var fp in existingFooters) mainPart.DeletePart(fp);

        // 4. Create header part (隶书 3号 烟台理工学院毕业论文（设计）, 居中).
        var headerPart = mainPart.AddNewPart<HeaderPart>();
        var headerHeader = new Header(
            new Paragraph(
                new ParagraphProperties(
                    new ParagraphStyleId { Val = "15" },     // header style id
                    new Justification { Val = JustificationValues.Center }
                ),
                new Run(
                    new RunProperties(
                        new RunFonts
                        {
                            Ascii = "Times New Roman",
                            HighAnsi = "Times New Roman",
                            EastAsia = "隶书",
                            ComplexScript = "Times New Roman",
                            Hint = FontTypeHintValues.EastAsia
                        },
                        new FontSize { Val = "32" },          // 三号 = 16pt -> sz="32" (per 规范)
                        new FontSizeComplexScript { Val = "32" }
                    ),
                    new Text("烟台理工学院毕业论文（设计）")
                )
            )
        );
        // Add namespace declarations to root
        headerPart.Header = headerHeader;
        headerPart.Header.Save();
        string headerRefId = mainPart.GetIdOfPart(headerPart);

        // 5. Create footer part (PAGE field, centered, 小五号(9pt -> sz=18)).
        var footerPart = mainPart.AddNewPart<FooterPart>();
        var footerPara = new Paragraph(
            new ParagraphProperties(
                new ParagraphStyleId { Val = "14" },   // footer style id
                new Justification { Val = JustificationValues.Center }
            )
        );
        var footerRPr = new RunProperties(
            new RunFonts
            {
                Ascii = "Times New Roman",
                HighAnsi = "Times New Roman",
                EastAsia = "宋体",
                ComplexScript = "Times New Roman"
            },
            new FontSize { Val = "18" },   // 小五号 = 9pt -> sz=18
            new FontSizeComplexScript { Val = "18" }
        );
        footerPara.AppendChild(new Run((RunProperties)footerRPr.CloneNode(true), new FieldChar { FieldCharType = FieldCharValues.Begin }));
        footerPara.AppendChild(new Run((RunProperties)footerRPr.CloneNode(true), new FieldCode(" PAGE   \\* MERGEFORMAT ") { Space = SpaceProcessingModeValues.Preserve }));
        footerPara.AppendChild(new Run((RunProperties)footerRPr.CloneNode(true), new FieldChar { FieldCharType = FieldCharValues.End }));
        footerPart.Footer = new Footer(footerPara);
        footerPart.Footer.Save();
        string footerRefId = mainPart.GetIdOfPart(footerPart);

        // 6. Build section 1 sectPr (cover/abstract/TOC) - no header/footer, page size A4 with same margins.
        var section1Pr = BuildBaseSectPr(headerRef: null, footerRef: null, restartNumbering: false);

        // 7. Build section 2 sectPr (body+) - with header/footer, page numbering starts at 1.
        var section2Pr = BuildBaseSectPr(headerRef: headerRefId, footerRef: footerRefId, restartNumbering: true);

        // 8. Insert a section break before the first chapter heading.
        //    OpenXML: a section ends at a paragraph whose pPr contains a sectPr.
        //    We place section1's sectPr inside the LAST paragraph BEFORE the first chapter heading.
        //    To minimize structural disturbance, we pick the immediate previous paragraph; if it doesn't
        //    exist (or has special properties), we insert an empty paragraph for the section break.
        Paragraph sectionBreakPara;
        var prev = firstChapterPara.PreviousSibling<Paragraph>();
        if (prev != null && string.IsNullOrWhiteSpace(ZoneClassifier.GetText(prev)))
        {
            sectionBreakPara = prev;
            // Ensure pPr exists
            var pPr = sectionBreakPara.GetFirstChild<ParagraphProperties>();
            if (pPr == null)
            {
                pPr = new ParagraphProperties();
                sectionBreakPara.PrependChild(pPr);
            }
            // Remove any existing sectPr inside its pPr (would be unusual)
            foreach (var sp in pPr.Elements<SectionProperties>().ToList()) sp.Remove();
            pPr.AppendChild(section1Pr);
        }
        else
        {
            sectionBreakPara = new Paragraph(
                new ParagraphProperties(section1Pr)
            );
            firstChapterPara.InsertBeforeSelf(sectionBreakPara);
        }

        // 9. Replace the trailing body-level SectionProperties (last child of body) with section2.
        var oldTail = body.Elements<SectionProperties>().LastOrDefault();
        if (oldTail != null) oldTail.Remove();
        body.AppendChild(section2Pr);

        // 10. Override pageBreakBefore on the first chapter heading because the section break
        //     already introduces a page break. (Otherwise we'd get TWO page breaks.)
        //     The ThesisH1 style sets pageBreakBefore by default; we explicitly disable it for
        //     this single paragraph by adding `<w:pageBreakBefore w:val="false"/>`.
        var fcPPr = firstChapterPara.GetFirstChild<ParagraphProperties>();
        if (fcPPr != null)
        {
            foreach (var pbb in fcPPr.Elements<PageBreakBefore>().ToList()) pbb.Remove();
            fcPPr.AppendChild(new PageBreakBefore { Val = OnOffValue.FromBoolean(false) });
        }
    }

    private static SectionProperties BuildBaseSectPr(string? headerRef, string? footerRef, bool restartNumbering)
    {
        var sectPr = new SectionProperties();

        if (headerRef != null)
        {
            sectPr.AppendChild(new HeaderReference
            {
                Type = HeaderFooterValues.Default,
                Id = headerRef
            });
        }
        if (footerRef != null)
        {
            sectPr.AppendChild(new FooterReference
            {
                Type = HeaderFooterValues.Default,
                Id = footerRef
            });
        }

        sectPr.AppendChild(new SectionType { Val = SectionMarkValues.NextPage });
        sectPr.AppendChild(new PageSize { Width = 11907, Height = 16839 }); // A4
        sectPr.AppendChild(new PageMargin
        {
            Top = Cm3_0,
            Right = Cm2_0,
            Bottom = Cm2_5,
            Left = Cm2_5,
            Header = (UInt32Value)(uint)Cm2_0_Hdr,
            Footer = (UInt32Value)(uint)Cm1_75,
            Gutter = 0
        });
        sectPr.AppendChild(new Columns { Space = "425", ColumnCount = 1 });
        if (restartNumbering)
        {
            sectPr.AppendChild(new PageNumberType { Start = 1, Format = NumberFormatValues.Decimal });
        }
        sectPr.AppendChild(new DocGrid
        {
            Type = DocGridValues.Lines,
            LinePitch = 312,
            CharacterSpace = 0
        });

        return sectPr;
    }
}
