# 转换工具使用与依赖

本包是 Python 转换工具与 Skill 说明。Python 3.10+，建议在独立虚拟环境中使用。本次验证环境的完整依赖在 requirements-extended.txt；它是可复现测试环境，不代表每位用户都需安装全部模块。

```text
python -m venv <独立环境目录>
<独立环境Python> -m pip install -r <技能目录>/requirements.txt
<独立环境Python> -m pip install -r <技能目录>/requirements-extended.txt
```

基础依赖含图片、FFmpeg 和 XLSX 数据交换；扩展依赖按任务安装。Office 引擎为用户已有的 Word/Excel/PowerPoint 或 LibreOffice，本包不捆绑或安装它们。只安装 Python 依赖不会获得 Office 的原生排版能力。

跨类别识别与专业格式详见 [扩展说明](advanced-formats.md)，完整 Python 扩展环境为 requirements-professional.txt；Blender、ODA 与 ASR 模型单独配置。

## 能力发现

```text
python scripts/convert.py --capabilities
python scripts/convert.py --targets --input C:/data/report.pdf
```

--targets 依据源扩展名和实际依赖返回候选，不读取全文；点击转换后还要检查具体内容，例如扫描页面、多工作表和透明度。能力发现是候选支持，不是质量承诺。

## 常用任务

```text
python scripts/convert.py --input C:/data/a.csv --format xlsx
python scripts/convert.py --input C:/data/a.xlsx --format csv --sheet 销售
python scripts/convert.py --input C:/data/a.xlsx --format csv --all-sheets
python scripts/convert.py --input C:/data/gb.csv --format xlsx --encoding gb18030
python scripts/convert.py --input C:/data/a.xlsx --format csv --formulas values
python scripts/convert.py --input C:/data/a.pdf --format docx
python scripts/convert.py --input C:/data/a.pdf --format xlsx
python scripts/convert.py --input C:/data/a.pdf --format png --pages 1-3,5 --dpi 144
python scripts/convert.py --input C:/data/a.pdf --format pptx --allow-layout-loss
python scripts/convert.py --input C:/data/a.docx --format pdf
python scripts/convert.py --input C:/data/a.pptx --format pdf
python scripts/convert.py --input C:/data/a.png --input C:/data/b.png --format pdf --merge
python scripts/convert.py --input C:/data/a.gif --format webp --all-frames
python scripts/convert.py --input C:/data/a.mp4 --format flac --allow-media-loss
python scripts/convert.py --input C:/data/a.mp4 --format webm --allow-media-loss
python scripts/convert.py --input C:/data/a.mp4 --format gif --start 1 --duration 3 --fps 10
python scripts/convert.py --input C:/data/a.mp4 --format png --start 1
python scripts/convert.py --input C:/data/a.srt --format vtt
python scripts/convert.py --input C:/data/a.md --format epub
python scripts/convert.py --input C:/data/a.epub --format docx
python scripts/convert.py --input C:/data/a.zip --format 7z
python scripts/convert.py --input C:/data/a.7z --format zip
python scripts/convert.py --input C:/data/a.svg --format png
python scripts/convert.py --input C:/data/a.ttf --format woff2
```

实际调用应使用绝对脚本路径和参数数组，示例相对路径仅为可读性。可重复 --input 实现各自转换；--merge 支持按传入顺序合并图片为 PDF 或 MP4。

## 数据和质量语义

- CSV 默认按 UTF-8 BOM 兼容方式读取和写入，逗号分隔；TSV 为制表符。其他编码用 --encoding 指定，其他分隔符用 --delimiter 指定。解码严格，失败时不替换成乱码。
- CSV/JSON 数据写 XLSX 时保护字符串、前导零与超过 15 位的整数。超长单元格文本拒绝而非截断。来自数据文件的等号开头字符串写成文字，不自动执行为公式。
- XLSX 导出 CSV/JSON 等数据格式时，多个工作表需 --sheet 或 --all-sheets。公式默认拒绝，values 使用已有缓存并说明未重算，expressions 输出公式文字。CSV 中公式样式的文字被表格软件重新打开时可能被当作公式，调用者应按交付对象选择格式。
- XLS/XLSX/ODS 相互转换使用 Office 引擎，尽量保留工作簿结构；CSV/JSON 转表格与 ODS 数据读取属于数据交换，不承诺保留样式和图表。
- XLSM 导出 XLSX/XLS/ODS 会移除宏，需在理解该变化后显式选择 --allow-layout-loss；Office 自动化禁用宏执行。
- 文本 PDF 转 DOCX 使用 pdf2docx 重建；扫描或无文字页面用 --ocr 识别为可编辑文字，原始完整排版未恢复。需要视觉复核复杂版面，不能只因生成了文件就称为完全还原。
- PDF 转 PPTX 是逐页图片封装，必须选择 --allow-layout-loss；输出文字不可直接编辑。PDF 转 Markdown 为纯文本提取，没有自动恢复全部标题语义。
- PDF 转表格采用线框/文字布局检测，未检测到表格即报告失败，不生成一份空 Excel 当作成功。
- 文档内容转 HTML/Markdown、电子书互转采用语义转换；DOCX 直接提取文本时不保留图片、脚注和复杂结构。Pandoc 沙箱限制外部资源，外链图片可能不保留。
- 图片动画需 --all-frames，静态格式拒绝隐式丢弃其他帧。透明转 JPG/PDF/BMP 需指定 --background。HEIC 先解码再输出常见图片，暂未提供 HEIC 输出和 RAW 显影。
- 媒体转换只保留第一条目标音轨/视频轨，删除额外轨道和元数据；用 --allow-media-loss 表达调用者已了解此范围。用户明确要求提取音频时，该要求本身已表达丢弃画面的意图，Agent 无需重复询问。需要多音轨、HDR 或专业色彩保留时不走此默认路线。
- 普通视频输出采用兼容编码；奇数宽高补齐到偶数像素。GIF 为指定片段，默认 480 像素宽。视频转 PNG/JPG 输出指定时间的一帧。
- 字幕转简单格式会减少样式；JSON/YAML 仅处理共同数据类型，重复键拒绝，注释不保留。
- ZIP/7Z/TAR 家族重打包不保留全部权限和归档元数据。原型拒绝链接、危险路径和大小/成员数超界的包；RAR 输入暂未实现。
- 字体支持容器压缩/解压，以及 TTC/OTC 按 --font-index 拆分；TTF/OTF 轮廓类型不转换，目标不匹配时拒绝。

## 验证与返回

脚本 stdout 只返回 JSON，第三方引擎日志写 stderr。每项有 input、output、outputs、bytes、validation、warnings；失败项有 error。部分成功时退出码 1，但成功输出可继续使用。

--merge 返回一个任务与多项 inputs。多个 PDF 页面、多个工作表返回 outputs 列表，不能只显示 output 中的第一个文件。

JSON 结果中的验证名称描述实际做过的检查：媒体全量解码、图片解码/帧数、PDF 页面渲染、Office 输出重开、表格读取、字幕事件数、字体字形表、压缩包校验。视觉保真、识别准确率和专业特性的完整性仍需对应样本验收。

当前没有原生进度窗口和任务级图形取消。Office 工作进程有 180 秒超时；超时和人工中断的进程回收仍需在原生集成中加强，不宣称系统级取消已验收。

## 尚未实现

RAR、RAW、AZW3/MOBI、联系人/日历、STEP/IGES、地理栅格、任意创作工程和字体轮廓转换。OCR/ASR 与 3D/CAD/GIS 已有独立实现，实际能力与外部依赖见 [扩展说明](advanced-formats.md)。
