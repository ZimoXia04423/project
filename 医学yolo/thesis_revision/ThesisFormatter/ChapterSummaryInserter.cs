using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

/// <summary>
/// Insert a "本章小结" sub-section at the end of each chapter (i.e. before the next chapter
/// heading, OR before the references title for the last chapter).
///
/// We use heuristics to derive a brief summary text per chapter from the chapter's heading
/// and known content. Each summary contains:
///   - L2 heading "X.Y 本章小结" (where X is the chapter number, Y = next sub-section index)
///   - One or two paragraphs of natural prose summarizing the chapter.
/// </summary>
internal static class ChapterSummaryInserter
{
    private record SummaryPlan(int ChapterNumber, string SummaryHeadingText, string[] BodyParagraphs);

    private static readonly Dictionary<int, string[]> SummaryByChapter = new()
    {
        [1] = new[]
        {
            "本章首先围绕腕部X光骨折检测在急诊与基层影像诊断中的现实需求展开，分析了人工阅片在高负荷与疲劳情境下的局限性，论证了基于深度学习的辅助诊断系统在临床预筛中的研究意义。" +
            "随后从目标检测算法演进与骨折影像分析两条主线对国内外研究现状进行了综述，重点关注了实时端到端检测框架与小目标、低对比病灶建模相关的最新进展。" +
            "在此基础上明确了本文的研究内容、创新点与论文结构安排，为后续章节的算法改进与系统设计奠定了问题域和技术路线的基础。"
        },
        [2] = new[]
        {
            "本章对论文涉及的核心理论与关键技术进行了梳理。首先讨论了医学影像骨折检测任务的特点，包括灰度纹理单一、目标尺寸偏小、类别不平衡等问题。" +
            "随后分别介绍了YOLOv10的整体架构与一致性双重标签分配策略、坐标注意力机制对位置敏感特征的建模优势，以及Focal Loss对难分类样本与正负样本失衡的调节作用。" +
            "最后简要说明了PyTorch、OpenCV与PyQt5在模型训练、推理和图形界面构建中的支撑作用，为后续章节的算法改进与系统实现提供了理论与工具基础。"
        },
        [3] = new[]
        {
            "本章面向腕部X光骨折辅助检测的应用场景，从功能需求与非功能需求两个维度对系统进行了需求分析，明确了数据处理、模型训练、图像检测、结果可视化与图形交互五个核心功能模块及对应的准确性、实时性、可维护性与可扩展性指标。" +
            "在此基础上，给出了由数据层、算法层、服务层与表现层构成的四层总体架构，并对模块划分与目录组织方式进行了说明。" +
            "本章工作明确了系统的总体形态与职责边界，为后续章节算法改进与系统实现提供了结构化的设计依据。"
        },
        [4] = new[]
        {
            "本章是论文的核心章节，围绕改进YOLOv10骨折检测模型的设计与实现展开。" +
            "首先，参考公开腕部创伤数据集的组织方式，完成了数据清洗、预处理、增强与训练/验证/测试集划分，并对类别构成进行了统计。" +
            "其次，针对骨折线细小、空间位置敏感的特点，在Backbone末端引入坐标注意力模块，强化对方向敏感特征的建模能力；" +
            "针对骨折样本与背景之间的严重不平衡问题，在分类分支中引入Focal Loss思想，提高了模型对难分类样本的关注度。" +
            "最后给出了配套的训练策略、评价指标与对比/消融实验设计，为下一章的实验分析提供了完整的方法支撑。"
        },
        [5] = new[]
        {
            "本章结合系统实现过程对改进YOLOv10骨折检测系统进行了实验分析。" +
            "首先说明了基于Windows + PyTorch + PyQt5的开发与实验环境，并描述了数据预处理、模型训练、推理可视化与图形界面四类关键功能的实现方式。" +
            "随后从功能测试与性能测试两个角度验证了系统的可用性与稳定性，结果表明系统能够稳定完成图像加载、模型推理、结果显示与异常提示等核心功能。" +
            "在实验对比方面，改进YOLOv10在Precision、Recall、mAP@0.5与mAP@0.5:0.95等关键指标上均优于Faster R-CNN、SSD、YOLOv8与原生YOLOv10，且在推理速度上保持了较好的实时性；" +
            "消融实验进一步证明了坐标注意力模块与Focal Loss思想的协同增益效果。" +
            "本章工作系统验证了所提出方法的有效性，并从急诊预筛、基层辅助判读和教学演示等角度分析了系统的应用价值。"
        }
        // Chapter 6 is itself a summary chapter (总结与展望) so we do NOT add a 本章小结 after it.
    };

    public static void Insert(Body body, ZoneInfo zones)
    {
        if (zones.BodyStart < 0 || zones.BodyEnd < 0) return;

        // Build chapter slices: each chapter starts at a heading like "1 ..." in body zone.
        // Chapter ends at the paragraph index immediately before the next chapter heading, or zones.BodyEnd otherwise.
        var chapters = new List<(int chapterNumber, int startIdx, int endIdx)>();
        for (int k = 0; k < zones.ChapterHeadingIdx.Count; k++)
        {
            int s = zones.ChapterHeadingIdx[k];
            int e = (k + 1 < zones.ChapterHeadingIdx.Count) ? zones.ChapterHeadingIdx[k + 1] - 1 : zones.BodyEnd;
            int chapNum = ParseChapterNumber(zones.Texts[s]);
            chapters.Add((chapNum, s, e));
        }

        // Walk chapters in REVERSE so that inserting elements doesn't shift the indices we still need.
        for (int k = chapters.Count - 1; k >= 0; k--)
        {
            var c = chapters[k];
            if (!SummaryByChapter.TryGetValue(c.chapterNumber, out var bodyParas))
                continue;

            // Compute next L2 sub-section number for the heading
            int nextSub = NextSubSectionIndex(zones, c.chapterNumber, c.startIdx, c.endIdx);
            string headingText = $"{c.chapterNumber}.{nextSub} 本章小结";

            // Find the paragraph BEFORE which we will insert. That is:
            //   - The paragraph at index (c.endIdx + 1), i.e. the next chapter heading, OR
            //   - For last chapter (c.endIdx == zones.BodyEnd), the paragraph after BodyEnd.
            Paragraph? anchor = null;
            int anchorIdx = c.endIdx + 1;
            if (anchorIdx < zones.Paragraphs.Count) anchor = zones.Paragraphs[anchorIdx];

            // Build the new paragraphs.
            var newParas = new List<Paragraph>();
            newParas.Add(BuildHeading(headingText));
            foreach (var line in bodyParas)
            {
                newParas.Add(BuildBodyPara(line));
            }

            // Insert before anchor (or append at end of body)
            if (anchor != null)
            {
                foreach (var np in newParas)
                {
                    anchor.InsertBeforeSelf(np);
                }
            }
            else
            {
                foreach (var np in newParas)
                {
                    body.AppendChild(np);
                }
            }
        }
    }

    private static int ParseChapterNumber(string text)
    {
        var m = System.Text.RegularExpressions.Regex.Match(text.Trim(), @"^(\d+)\b");
        return m.Success ? int.Parse(m.Groups[1].Value) : 0;
    }

    private static int NextSubSectionIndex(ZoneInfo zones, int chapterNumber, int startIdx, int endIdx)
    {
        int max = 0;
        var rx = new System.Text.RegularExpressions.Regex($@"^{chapterNumber}\.(\d+)\b");
        for (int i = startIdx; i <= endIdx && i < zones.Texts.Count; i++)
        {
            var m = rx.Match(zones.Texts[i].Trim());
            if (m.Success && int.TryParse(m.Groups[1].Value, out int n))
            {
                if (n > max) max = n;
            }
        }
        return max + 1;
    }

    private static Paragraph BuildHeading(string text)
    {
        var p = new Paragraph();
        var pPr = new ParagraphProperties(
            new ParagraphStyleId { Val = StyleInjector.Ids.H2 }
        );
        p.AppendChild(pPr);
        p.AppendChild(new Run(new Text(text) { Space = DocumentFormat.OpenXml.SpaceProcessingModeValues.Preserve }));
        return p;
    }

    private static Paragraph BuildBodyPara(string text)
    {
        var p = new Paragraph();
        var pPr = new ParagraphProperties(
            new ParagraphStyleId { Val = StyleInjector.Ids.Body }
        );
        p.AppendChild(pPr);
        p.AppendChild(new Run(new Text(text) { Space = DocumentFormat.OpenXml.SpaceProcessingModeValues.Preserve }));
        return p;
    }
}
