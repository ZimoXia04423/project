using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

/// <summary>
/// Patch word/settings.xml to enable automatic field updates when the document is opened.
/// This causes Word/WPS to rebuild the TOC field on first open, which picks up the
/// new headings (1.3.3, 本章小结) and recomputes correct page numbers.
/// </summary>
internal static class SettingsPatcher
{
    public static void EnableUpdateFields(MainDocumentPart mainPart)
    {
        var settingsPart = mainPart.DocumentSettingsPart;
        if (settingsPart == null) return;
        var settings = settingsPart.Settings ?? new Settings();

        // Remove any existing UpdateFieldsOnOpen and add a fresh one (val="true").
        foreach (var existing in settings.Elements<UpdateFieldsOnOpen>().ToList())
        {
            existing.Remove();
        }
        settings.AppendChild(new UpdateFieldsOnOpen { Val = OnOffValue.FromBoolean(true) });

        settings.Save(settingsPart);
    }
}
