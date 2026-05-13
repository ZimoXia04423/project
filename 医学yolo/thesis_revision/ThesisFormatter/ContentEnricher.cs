using System.Text.RegularExpressions;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ThesisFormatter;

/// <summary>
/// Expand thin sections of the thesis body and add inline [N] citations so that
/// the article visibly cites references throughout, not only in the literature
/// review section. This module runs AFTER chapter summaries are inserted but
/// BEFORE citation hyperlink conversion, so the new [N] markers we add will be
/// converted to clickable hyperlinks downstream.
/// </summary>
internal static class ContentEnricher
{
    /// <summary>
    /// (signature, citationsToAppend) — find a paragraph whose combined text contains
    /// `signature` and append `citationsToAppend` (e.g. "[2]", "[14][17]") just before
    /// the trailing period (if any). Pass each signature once — duplicates are skipped.
    /// </summary>
    private static readonly (string Signature, string Cites)[] CitationInjections = new[]
    {
        // Chapter 2 — technical foundations
        ("YOLO 系列以统一的回归式框架持续迭代",        "[14][17][25][27]"),
        ("坐标注意力机制由 Hou",                          "[2]"),
        ("坐标注意力机制由Hou",                            "[2]"),
        ("这种注意力机制计算开销小",                       "[2]"),
        ("使易分类样本（p_t 接近",                         "[3]"),
        ("Lin 等人在 RetinaNet 中提出 Focal",             "[3]"),
        ("图像预处理、结果绘制和文件读写采用OpenCV",     "[16]"),

        // Chapter 4 — model design
        ("本文研究对象为腕部X光图像。数据集构建时",     "[6]"),
        ("加载公开预训练权重",                             "[14]"),
        ("具体插值与采样方式与",                           "[26]"),

        // Chapter 4.7 — comparative experiments
        ("Faster R-CNN",                                   "[4]"),
        ("通过对比可分析单阶段与两阶段模型",            "[5]"),

        // Chapter 5 — experiments / discussion
        ("在普通GPU环境下，系统应具备较快的推理速度", "[15]"),
        ("更适合实际辅助诊断场景下对实时性的要求",   "[7][24]"),
        ("当前训练数据规模仍然有限",                       "[22][28]"),
        ("二维X光图像本身存在结构重叠问题",             "[12][29]"),

        // Chapter 6 — conclusion & outlook
        ("完善患者级去重与独立外部测试集",                "[22]"),
        ("引入概率校准与错误类型分析",                    "[20]"),
        ("需另行规划医疗器械软件生命周期",                "[21]"),
        ("增强模型关注区域的可视化",                       "[20][21]"),
    };

    /// <summary>
    /// Paragraphs to insert into the body. Each entry specifies an anchor signature
    /// (a unique phrase from an existing paragraph), a position relative to the anchor
    /// ("before" or "after"), and a list of (style, text) tuples that become new paragraphs.
    /// </summary>
    private record InsertionSpec(string AnchorSignature, string Position, (string StyleId, string Text)[] Paragraphs);

    private static readonly InsertionSpec[] Insertions = new[]
    {
        // 1.3.1 — append one paragraph about DETR / RT-DETR right before "1.3.2 骨折检测研究进展"
        new InsertionSpec("1.3.2 骨折检测研究进展", "before",
            new (string, string)[]
            {
                (StyleInjector.Ids.Body,
                "此外，端到端目标检测在医学影像中的应用也出现了若干新方向。基于 Transformer 的 DETR 系列摆脱了显式锚框设计，通过集合预测直接学习目标位置与类别[19]；RT-DETR 则在保持 Transformer 全局建模能力的同时进一步提升了实时性，在通用目标检测基准上对 YOLO 系列形成有力补充[18]。这些方法在复杂场景下的全局关系建模能力，为后续将注意力机制与端到端思想引入小目标医学检测提供了参考。"),
            }),

        // 1.3.2 — add Chinese-domestic research paragraph + then insert 1.3.3 section
        new InsertionSpec("综合来看，骨折检测研究正从", "before",
            new (string, string)[]
            {
                (StyleInjector.Ids.Body,
                "此外，国内研究者也在医学骨折影像辅助诊断方向开展了多角度探索。熊山等基于深度学习构建肋骨骨折辅助诊断系统，验证了卷积神经网络在多类型骨折判读中的可行性[30]；谭辉等针对急性肋骨骨折提出了模型与放射科医生协同读片的工作流，进一步证明AI辅助可在繁忙急诊环境下提高诊断效能[31]；田冲等系统综述了机器学习在创伤骨科中的应用现状与挑战，指出在数据规模、外部验证与临床落地方面仍需更多严谨工作[32]。这些研究与国外腕部、髋部骨折智能化分析工作共同构成了医学骨折影像目标检测研究的整体图谱，为本文方法选择与实验设计提供了参考。"),
            }),

        // Insert 1.3.3 现有研究存在的问题 between 1.3.2 closing paragraph and 1.4
        new InsertionSpec("1.4 研究内容与创新点", "before",
            new (string, string)[]
            {
                (StyleInjector.Ids.H3, "1.3.3 现有研究存在的问题"),
                (StyleInjector.Ids.Body,
                "尽管腕部X光骨折智能辅助检测研究已经取得了显著进展，但在向真实临床场景落地的过程中仍存在若干尚需解决的问题，归纳起来主要体现为以下几个方面[9][20]。"),
                (StyleInjector.Ids.Body,
                "第一，公开数据集规模与多样性仍受限。多数已公开的腕部X光骨折数据集来源较为集中，影像设备、患者年龄构成、骨折类型分布与标注口径在不同来源之间存在差异，导致模型在跨机构、跨设备场景下的泛化能力难以充分评估[6][22]。"),
                (StyleInjector.Ids.Body,
                "第二，小目标与隐匿性骨折检测仍是难点。腕部解剖结构在二维投影下重叠严重，细小骨折线在灰度上与正常骨皮质纹理高度相似，模型在低对比度、轻微皮质中断及小尺度目标上的召回率仍有较大提升空间[12][29]。"),
                (StyleInjector.Ids.Body,
                "第三，类别与样本不平衡问题尚未充分解决。骨折正样本占整幅图像与候选框的比例极低，大量易分类负样本主导梯度更新，常规交叉熵难以充分关注难分类样本，影响召回率与mAP表现[3][28]。"),
                (StyleInjector.Ids.Body,
                "第四，工程与临床评估闭环尚不完整。当前研究多聚焦于算法精度比较，对模型在阅片流程中的嵌入位置、可解释性、错误类型分布与长期可用性证据的报告仍相对有限，缺乏与TRIPOD+AI、DECIDE-AI等报告规范相一致的系统化外部验证设计[20][21]。"),
                (StyleInjector.Ids.Body,
                "针对上述不足，本文在实时端到端检测框架基础上，结合腕部骨折影像的小目标、低对比度与样本不平衡等特点，从结构改进、损失优化与桌面端可视化三方面开展工作，并保留对比实验与消融实验的设计接口，为后续在更大规模数据上的进一步验证奠定基础。"),
            }),

        // ===================================================================================
        // Chapter 3 — expand the System Design section (was too thin per user feedback)
        // ===================================================================================

        // 3.1 系统设计目标 — append elaboration after the existing list of 4 goals
        new InsertionSpec("3.2 功能需求分析", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "具体而言，系统需在保证骨折检测精度的同时兼顾实时响应能力，确保在普通桌面端硬件环境下也能完成单张图像的快速推理；同时，系统应当具备良好的可视化呈现能力，将复杂的深度学习推理结果以直观的边界框、类别标签与置信度形式展示给医师，避免因黑盒输出导致的使用障碍。"),
            (StyleInjector.Ids.Body,
            "在工程实现上，系统应采用模块化设计原则，将数据层、算法层、服务层与表现层进行明确划分，便于后续算法替换、功能扩展与跨平台移植；在使用场景上，系统需考虑到答辩演示、教学讲解和基层辅助判读等多种用例，因此需要兼顾界面易用性、操作流畅度与结果可解释性。综合而言，本系统的核心定位是在科研演示与初步临床辅助之间形成连接，为后续实际部署积累可用经验。"),
        }),

        // 3.2 功能需求分析 — append additional intro paragraphs after "结合课题目标..."
        new InsertionSpec("3.2.1 数据处理模块", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "在功能需求分析阶段，本文将系统按照腕部X光骨折辅助检测的端到端工作流进行拆解，形成围绕「数据—模型—推理—展示—交互」的五个核心模块。这种拆解方式既符合深度学习项目的常见组织方式，也方便在科研阶段和工程阶段对不同模块进行独立调试与替换，避免单点故障在整个系统范围内放大。"),
            (StyleInjector.Ids.Body,
            "具体来说，数据处理模块负责把原始 X 光图像与标注转化为模型可消费的标准数据集，并保证训练/验证/测试三集的患者级别独立性；模型训练模块负责加载数据、构建改进 YOLOv10 网络、配置训练超参数并保存权重文件；图像检测模块在加载好的权重之上执行推理并产出结构化结果；结果可视化模块按设定的颜色与文本规则将检测结果渲染回原图，并把分级判定写入界面与可导出的报告；图形交互模块则面向使用者提供完整的可视化操作入口，避免命令行使用方式带来的门槛。"),
            (StyleInjector.Ids.Body,
            "下文将分别从这五个模块出发，进一步明确各自的输入、输出、关键流程与对外接口，使后续的总体架构设计与系统模块设计可以在统一的功能粒度上进行展开。"),
        }),

        // 3.2.1 数据处理模块 — append a follow-up paragraph
        new InsertionSpec("3.2.2 模型训练模块", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "具体来说，数据处理模块需要支持YOLO格式标签的自动生成与转换，并能够对原始图像执行去重、尺寸归一化、对比度增强与噪声抑制等操作。模块还应保留预处理参数的可配置接口，例如增强强度、缩放比例与归一化方式等，以便后续根据数据分布情况进行调整。同时，为支持后续的复现与审计，模块输出的训练/验证/测试清单需要保留患者级别的归属信息和数据来源记录。"),
            (StyleInjector.Ids.Body,
            "在异常处理方面，模块需要识别并隔离损坏图像、空标签文件和坐标越界的标注样本，避免在后续训练阶段抛出难以定位的错误；同时，模块在数据集划分时应支持指定随机种子，以便不同实验之间在划分结果上保持一致，从而提升实验对比的可复现性。"),
        }),

        // 3.2.2 模型训练模块
        new InsertionSpec("3.2.3 图像检测模块", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "训练模块需要提供完整的命令行入口和配置文件支持，允许用户指定数据集路径、模型权重、训练轮数、批大小、学习率等关键超参数。模块还应在训练过程中自动保存最优权重和最新权重，并将损失曲线、Precision、Recall、mAP等指标记录到日志或TensorBoard，便于训练过程监控与后续可视化分析。在异常情况下，模块还应提供训练中断恢复、断点续训和权重比较等辅助能力，以减少长时训练带来的实验风险[15]。"),
            (StyleInjector.Ids.Body,
            "针对腕部 X 光骨折检测样本量有限、类别不平衡的特点，训练模块还需要内置数据增强、采样平衡、损失加权等可配置策略，并允许在不修改核心代码的前提下通过配置文件切换 Backbone、Neck 和 Head 的具体实现，方便后续在改进 YOLOv10 之外尝试其他网络结构进行横向对比。"),
        }),

        // 3.2.3 图像检测模块
        new InsertionSpec("3.2.4 结果可视化模块", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "该模块在接收单张或批量X光图像后，需先调用预处理流程将图像统一缩放与归一化，再通过加载好的改进YOLOv10模型完成前向推理，输出每个候选框对应的位置坐标、所属类别及置信度。为提高响应速度，推理过程应在独立线程中执行，避免阻塞图形用户界面，并支持基于置信度阈值与IoU阈值的灵活过滤设置，使医师可以根据不同任务对敏感度与特异度的偏好进行调整。"),
            (StyleInjector.Ids.Body,
            "为支撑后续的可解释性与对比分析，图像检测模块在返回单张图像结果的同时，还应输出推理耗时、模型版本号与所使用的阈值组合等元数据，使每一次检测均具备可追溯性；当用户切换不同模型权重时，模块应自动重新加载并复用底层算子缓存，避免重复初始化带来的额外开销。"),
        }),

        // 3.2.4 结果可视化模块
        new InsertionSpec("3.2.5 图形交互模块", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "模块按预设颜色方案在原始图像上叠加检测框：`Fracture` 类使用红色框突出显示，`No_Fracture` 类使用绿色框，`Object` 类使用蓝色框，并在框上方注明类别名称与置信度数值。同时，模块需提供分级结果的文本与表格展示，并支持一键将可视化图像与结果信息导出为本地文件，方便后续答辩演示与教学使用。"),
            (StyleInjector.Ids.Body,
            "考虑到不同显示设备对色彩呈现的差异，模块对边框颜色采用高对比度搭配，并通过加粗字体显示类别名称与置信度，确保在投影与笔记本屏幕上都具备良好的可读性；同时，模块支持把多张检测结果图组合为带索引的输出目录，方便后续整理对比报告或撰写病例资料。"),
        }),

        // 3.2.5 图形交互模块
        new InsertionSpec("3.3 非功能需求分析", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "模块在主界面上集中放置文件加载按钮、模型选择下拉框、置信度滑块、检测启动按钮以及结果保存按钮等控件，并通过左右双视图区域分别展示原图与检测后图像。系统还应在右侧信息区实时显示检测耗时、检出目标数量与分级结论，使用户能够直观地获取算法输出与判断依据；为方便答辩演示，模块还应支持原图与检测结果图的快速切换以及多模型并行对比展示。"),
            (StyleInjector.Ids.Body,
            "在交互细节上，模块需要充分考虑非专业用户的使用场景：对所有关键按钮提供文字提示和图标双重表达；对耗时较长的推理操作以进度提示而非长时间无响应的方式呈现；对异常输入（例如非图像格式、超大文件、缺失模型权重等）给出明确、可操作的错误说明，避免界面卡死或抛出原始异常栈，从而保证使用过程中的稳定性与可恢复性。"),
        }),

        // 3.3.1 准确性需求
        new InsertionSpec("3.3.2 实时性需求", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "系统应在测试集上达到Precision不低于85%、Recall不低于80%、mAP@0.5不低于90%的总体性能指标，并对小尺度骨折与低对比度病灶保持稳定的检测能力。在分类层面，模型需能够准确区分骨折、非骨折与解剖目标三类标签，避免在繁忙阅片场景中将正常解剖结构误判为骨折，从而降低医师对辅助系统的信任度。"),
        }),

        // 3.3.2 实时性需求
        new InsertionSpec("3.3.3 可维护性需求", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "在配备入门级独立显卡的桌面端环境下，单张X光图像从加载到完成可视化的整体耗时应控制在数百毫秒以内；在仅有CPU的受限环境下，单图响应时间也应保持在2秒以内，以满足教学演示与基层快速筛查需求。同时，连续检测时系统不应出现界面卡顿、显存累积或泄漏等问题，以保证在长时间使用中的稳定性。"),
        }),

        // 3.3.3 可维护性需求
        new InsertionSpec("3.3.4 可扩展性需求", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "系统目录结构应按数据、模型、推理、界面、训练等功能进行分层组织，使后续维护人员能够在不影响其他模块的前提下完成模型替换、数据集扩展或界面优化。代码应遵循统一的命名与注释规范，关键函数提供明确的输入输出说明，并保留必要的日志输出便于问题排查；同时，权重文件、配置文件与代码版本之间需保持可追溯关系，避免因模型迭代导致的复现困难。"),
        }),

        // 3.3.4 可扩展性需求
        new InsertionSpec("3.4 系统总体架构设计", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "系统设计需为后续从单机桌面端扩展到Web服务、移动端APP或PACS系统集成预留接口，例如通过封装统一的推理服务API，将图像检测能力对外暴露；同时，模块化的架构允许在不重写界面的情况下切换底层算法，例如从改进YOLOv10替换为更新一代的检测模型，或加入多模态融合分析能力以应对更复杂的临床场景。"),
        }),

        // 3.4 系统总体架构设计 — append architecture description before the workflow
        new InsertionSpec("3.5 系统模块设计", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "为支撑上述功能与非功能需求，系统采用四层分层架构设计。该架构通过严格的层间依赖单向流动原则，确保上层模块只能调用下层服务接口，避免出现循环依赖；底层数据层与算法层的实现细节对上层服务层与表现层透明，便于后续局部替换与升级。"),
            (StyleInjector.Ids.Body,
            "在具体落地中，数据层负责对外屏蔽数据采集、清洗与转换的细节，将训练集、验证集与测试集以统一的数据接口暴露给算法层；算法层封装改进YOLOv10模型的训练、验证与推理流程，对外提供权重加载与推理调用接口；服务层在算法层之上聚合图像预处理、模型加载、结果后处理、文件保存等业务流程，并对界面层提供高内聚的检测服务；表现层基于PyQt5实现图形界面，仅通过服务层提供的接口完成用户交互，不直接依赖底层算法实现。这种自下而上的分层使整个系统在保证功能完整性的同时具备良好的可测试性与可演化性。"),
        }),

        // 3.5 系统模块设计 — append module-relationship paragraph at the end of chapter 3
        new InsertionSpec("4 改进YOLOv10骨折检测模型设计与实现", "before", new (string, string)[]
        {
            (StyleInjector.Ids.Body,
            "进一步地，模块之间的依赖关系大致可以归纳为：`preprocess` 与 `datasets` 共同支撑数据层，为模型训练与评估提供统一格式的数据；`models`、`train` 与 `infer` 共同实现算法层，封装改进YOLOv10的结构定义、训练流程与推理接口；`infer` 中的可视化与导出工具构成服务层的核心，负责将算法输出转换为可读、可保存的检测结果；`gui` 模块则作为表现层独立存在，仅通过服务层接口与底层算法交互。这种分层组织一方面便于在科研阶段聚焦算法改进，另一方面也为后续工程化迭代与功能扩展奠定基础。"),
        }),
    };

    public static void Enrich(Body body)
    {
        // 1. Insert new paragraphs at the requested anchor positions.
        foreach (var spec in Insertions)
        {
            ApplyInsertion(body, spec);
        }

        // 2. Append [N] citation markers to existing paragraphs.
        //    For each signature, search every paragraph; pick the shortest paragraph
        //    that CONTAINS the signature AND does NOT already contain any of the
        //    individual [N] citations we want to add. This avoids hitting long survey
        //    paragraphs that already cite multiple references.
        var citeRx = new Regex(@"\[\d{1,3}\]", RegexOptions.Compiled);
        var alreadyTouched = new HashSet<Paragraph>();
        foreach (var (sig, cites) in CitationInjections)
        {
            var citesNeeded = citeRx.Matches(cites).Select(m => m.Value).ToHashSet();

            Paragraph? best = null;
            int bestLen = int.MaxValue;
            foreach (var p in body.Elements<Paragraph>())
            {
                if (alreadyTouched.Contains(p)) continue;
                if (IsTocParagraph(p)) continue;
                string text = ZoneClassifier.GetText(p);
                if (!text.Contains(sig)) continue;

                // Skip if all the desired [N] markers are already present somewhere in the paragraph.
                var present = citeRx.Matches(text).Select(m => m.Value).ToHashSet();
                bool allAlready = citesNeeded.All(c => present.Contains(c));
                if (allAlready) continue;

                if (text.Length < bestLen)
                {
                    bestLen = text.Length;
                    best = p;
                }
            }
            if (best != null)
            {
                AppendCitations(best, cites);
                alreadyTouched.Add(best);
            }
        }
    }

    private static void ApplyInsertion(Body body, InsertionSpec spec)
    {
        Paragraph? anchor = null;
        foreach (var p in body.Elements<Paragraph>())
        {
            // Skip TOC paragraphs (TOC builtin styles 12=toc3, 16=toc1, 18=toc2)
            if (IsTocParagraph(p)) continue;
            string text = ZoneClassifier.GetText(p).Trim();
            if (text.Contains(spec.AnchorSignature))
            {
                anchor = p;
                break;
            }
        }
        if (anchor == null)
        {
            Console.WriteLine($"[WARN] ContentEnricher anchor not found: {spec.AnchorSignature}");
            return;
        }

        // Skip if the FIRST text already exists in the paragraph adjacent to the anchor.
        // This guards against double-inserting on re-runs.
        string firstNewText = spec.Paragraphs[0].Text;
        var probe = spec.Position == "before" ? anchor.PreviousSibling<Paragraph>() : anchor.NextSibling<Paragraph>();
        if (probe != null && ZoneClassifier.GetText(probe).Contains(firstNewText.Substring(0, Math.Min(20, firstNewText.Length))))
        {
            return;
        }

        var built = spec.Paragraphs.Select(BuildParagraph).ToList();
        if (spec.Position == "before")
        {
            foreach (var np in built) anchor.InsertBeforeSelf(np);
        }
        else
        {
            // Insert in reverse so they end up in correct order
            foreach (var np in built.AsEnumerable().Reverse()) anchor.InsertAfterSelf(np);
        }
    }

    private static bool IsTocParagraph(Paragraph p)
    {
        var styleId = p.GetFirstChild<ParagraphProperties>()?.GetFirstChild<ParagraphStyleId>()?.Val?.Value;
        return styleId is "12" or "16" or "18" or StyleInjector.Ids.TocTitle;
    }

    private static Paragraph BuildParagraph((string StyleId, string Text) data)
    {
        var p = new Paragraph();
        p.AppendChild(new ParagraphProperties(new ParagraphStyleId { Val = data.StyleId }));
        p.AppendChild(new Run(new Text(data.Text) { Space = SpaceProcessingModeValues.Preserve }));
        return p;
    }

    /// <summary>
    /// Append plaintext "[N]" citation markers at the end of the paragraph (just before the
    /// trailing CJK / Latin period if present). The CitationLinker downstream will convert
    /// them into superscript hyperlinks pointing to the bookmarked references.
    /// </summary>
    private static void AppendCitations(Paragraph p, string cites)
    {
        var lastText = p.Descendants<Text>().LastOrDefault();
        if (lastText == null)
        {
            p.AppendChild(new Run(new Text(cites) { Space = SpaceProcessingModeValues.Preserve }));
            return;
        }

        string content = lastText.Text;
        char[] trailers = { '。', '.', '；', ';', '!', '！', '?', '？', ' ', '\t' };
        int idx = content.Length;
        while (idx > 0 && Array.IndexOf(trailers, content[idx - 1]) >= 0) idx--;

        string before = content.Substring(0, idx);
        string after = content.Substring(idx);
        lastText.Text = before + cites + after;
        lastText.Space = SpaceProcessingModeValues.Preserve;
    }
}
