1. 核心原则：Mermaid 是起点，不是终点
Mermaid 的优势在于通过代码快速生成矢量图（SVG），这比用 Visio 或 PPT 手动画要高效得多，且逻辑清晰。但是，IEEE 期刊对图片的排版细节有严格要求，Mermaid 的默认样式通常无法直接满足这些要求。

2. 必须满足的 IEEE 规范 (Mermaid 默认通常不达标)
根据 IEEE 的投稿标准，你的图需要满足以下条件，而 Mermaid 的默认输出往往需要调整：
表格
规范维度	IEEE 典型要求	Mermaid 默认情况	解决方案
文件格式	EPS 或 PDF (矢量), 或 TIFF (≥600 dpi)	通常导出为 SVG 或 PNG	将 SVG 转换为 EPS/PDF，或导出高分辨率 PNG。
字体	Times New Roman 或 Arial，字号通常 ≥ 8pt	默认通常是 sans-serif (无衬线体)	在 Mermaid 代码中通过 %%{init: {'themeVariables': {'fontFamily': 'Times New Roman'}}}%% 强制指定字体。
线宽	清晰可见，通常 ≥ 0.5 pt	默认较细	使用 style 或 classDef 增加 stroke-width。
配色	建议黑白灰或高对比度（适应黑白打印）	默认色彩较鲜艳	自定义配色方案，避免使用纯红/纯绿，改用深蓝、深灰等。

第二步：导出矢量图 (SVG)
在支持 Mermaid 的编辑器（如 Typora, VS Code, 或 Mermaid Live Editor）中，将图表导出为 SVG 格式。SVG 是矢量图，放大不失真，是后续处理的最佳素材。
第三步：后期处理 (关键步骤)
这是让图表达到“出版级”质量的关键：

    使用矢量编辑软件：下载 Inkscape (免费) 或 Adobe Illustrator。
    导入 SVG：打开刚才导出的 Mermaid SVG 文件。
    微调：
        检查字体是否已正确渲染为 Times New Roman。
        调整线条粗细，确保打印出来清晰。
        去除多余的背景色，确保背景透明或纯白。
    最终导出：保存为 EPS 或 PDF 格式，这是 IEEE 最推荐的矢量格式；或者导出为 600 dpi 以上的 TIFF/PNG。

4. 避坑指南

    不要直接截图：截图是位图，放入论文中放大后会模糊，会被 IEEE 格式审查退回。
    不要依赖默认配色：Mermaid 默认的蓝色/紫色在某些黑白打印机上可能无法区分，建议使用深色边框+白色填充的经典学术风格。
    注意文字转曲：如果在 Word 或 LaTeX 中插入 EPS 图片，最好确保图片内的字体已经“嵌入”或“转曲”（Create Outlines），防止换台电脑字体丢失变成乱码。

总结： Mermaid 是生成 IEEE 图表的高效工具，但请务必配合矢量编辑软件进行最后的格式和样式清洗，这样才能达到顶级期刊的出版要求


IEEE JSTARS 示例格式
paper_use/image_ground_conversion_flow.mmd