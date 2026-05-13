using System.Text;
using System.Text.RegularExpressions;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

internal static class Program
{
    static int Main(string[] args)
    {
        Console.OutputEncoding = Encoding.UTF8;

        var input = args.Length > 0 ? args[0]
            : @"d:\project\医学python\thesis_revision\thesis_working.docx";
        var output = args.Length > 1 ? args[1]
            : @"d:\project\医学python\thesis_revision\thesis_formatted.docx";

        if (!File.Exists(input))
        {
            Console.Error.WriteLine($"Input not found: {input}");
            return 1;
        }
        File.Copy(input, output, overwrite: true);

        Console.WriteLine($"[*] Working on {output}");

        using (var doc = WordprocessingDocument.Open(output, true))
        {
            var mainPart = doc.MainDocumentPart!;
            var stylesPart = mainPart.StyleDefinitionsPart!;
            var body = mainPart.Document.Body!;

            Console.WriteLine("[1/9] Injecting spec styles ...");
            StyleInjector.Inject(stylesPart);

            Console.WriteLine("[2/9] Identifying document zones ...");
            var zones = ZoneClassifier.Classify(body);
            zones.Print();

            Console.WriteLine("[3/9] Inserting chapter summaries ...");
            ChapterSummaryInserter.Insert(body, zones);

            Console.WriteLine("[4/9] Inserting references title and reformat refs ...");
            ReferencesFormatter.Insert(body, zones);

            Console.WriteLine("[5/9] Enriching content (1.3 expansion + extra citations) ...");
            ContentEnricher.Enrich(body);

            Console.WriteLine("[6/9] Reclassifying after insertion ...");
            zones = ZoneClassifier.Classify(body);
            zones.Print();

            Console.WriteLine("[7/9] Applying per-paragraph styles ...");
            ParagraphFormatter.Apply(body, zones);

            Console.WriteLine("[8/9] Adding citation hyperlinks + bookmarks ...");
            CitationLinker.Process(body, zones);

            Console.WriteLine("[9/9] Setting up sections + header + footer ...");
            HeaderFooterSetup.Setup(mainPart, body, zones);

            Console.WriteLine("[+] Replacing stale TOC with self-evaluating TOC field ...");
            TocRebuilder.Rebuild(body);

            Console.WriteLine("[+] Enabling auto-update of TOC field on open ...");
            SettingsPatcher.EnableUpdateFields(mainPart);

            mainPart.Document.Save();
            stylesPart.Styles!.Save();
        }

        Console.WriteLine("[OK] Done.");
        return 0;
    }
}
