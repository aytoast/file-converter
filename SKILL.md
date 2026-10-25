---
name: file-converter
description: 转换本地文档、媒体、表格、3D 模型、CAD、地理数据及字体；支持 OCR、音视频转文字/字幕、图片序列视频及资源提取。根据本机引擎提供目标，保留原件并验证输出，可供文件右键入口调用。
---

# 文件转换

状态：本地可运行扩展版，尚未接入天禧或 Windows 右键菜单，未安装到 Codex。普通格式转换由确定性工具执行；模型理解目标、处理必要决策并调用工具。

## 先发现能力

```text
python <技能目录>/scripts/convert.py --capabilities
python <技能目录>/scripts/convert.py --targets --input <文件绝对路径>
```

使用宿主实际可用的 Python。依赖缺失时依据 [使用与依赖说明](references/usage.md)处理，不宣称操作系统或天禧已提供所有引擎。requirements.txt 是基础依赖，requirements-extended.txt 是本次验证的扩展环境，Office 应用单独检测。

跨类别、OCR/ASR、3D/CAD/GIS、字体集合任务另读 [专业与跨类别说明](references/advanced-formats.md)。对应 Python 环境在 requirements-professional.txt，原生引擎和模型另行检测，不自动下载模型。

--targets 是按文件类型与依赖筛选的候选。具体任务仍可能因扫描页面、复杂结构、受保护文件或编码器问题失败。不能把研究目录当作已实现支持列表。

## 已实现路线

| 输入类别 | 当前转换 |
| --- | --- |
| 静态图片 | JPG、PNG、WebP、BMP、TIFF、GIF、ICO、AVIF；可用编解码器间转换及图片 PDF |
| 手机照片 | HEIC/HEIF 读取后输出常见图片 |
| 动画/多页图片 | GIF、PNG、WebP、TIFF、PDF 等支持的多帧输出，需明确保留全部帧 |
| 音频 | MP3、WAV、FLAC、AAC、M4A、OGG、Opus、AIFF、WMA，按编码器提供输出 |
| 视频 | MP4、MKV、MOV、AVI、WebM、WMV、FLV、TS、MPEG 等；提取音频、指定片段 GIF、指定时间截图 |
| Office | Word 类文档互转、表格工作簿互转、演示文稿互转与 PDF 导出；需对应 Office 应用或 LibreOffice |
| 表格数据 | CSV/TSV/JSON/JSONL 与 XLSX/ODS 数据交换，XLS 读取，工作表选择与公式策略 |
| PDF | 可编辑 DOCX 重建、表格提取为 XLSX/CSV/JSON、逐页图片/SVG、文字提取、图片型 PPTX |
| 图片合并 | 按用户传入顺序合并多张图片为一个 PDF |
| 内容文档/电子书 | Markdown、HTML、DOCX、ODT、EPUB、TXT 的支持方向；EPUB 导出 PDF |
| 字幕 | SRT、VTT、ASS、SSA 互转 |
| 结构化数据 | JSON/YAML 的共同数据模型互转，重复键拒绝 |
| 压缩包 | ZIP、7Z、TAR、TAR.GZ、TAR.XZ 的重打包 |
| 矢量图和字体 | SVG 渲染 PNG/JPG/PDF；TTF/OTF 与 WOFF/WOFF2 容器转换 |
| OCR | 图片/扫描 PDF → 文字、可编辑文字 DOCX、表格 XLSX/CSV、可搜索 PDF |
| ASR | 音视频 → TXT/Markdown/DOCX/SRT/VTT/JSON，需本地模型 |
| 图像跨类别 | 视频抽帧序列、图片序列/动图转 MP4、单色位图描摹为 SVG 路径 |
| 资源提取 | PDF/DOCX/PPTX/XLSX 中的嵌入图片；Office 文档逐页图片导出 |
| 3D | OBJ/STL/PLY/glTF/GLB/FBX/BLEND 的支持方向及 PNG 预览；OFF 网格备用路线 |
| CAD | DXF 读写与 SVG/PDF/PNG 导出；DWG 路线需要 ODA 引擎 |
| 地理数据 | GeoJSON/GPKG/Shapefile ZIP/KML/GPX/FGB，明确坐标列的 CSV/XLSX 与真实重投影 |
| 字体集合 | TTC/OTC 按指定索引拆出字体，再转支持的容器 |

表中是路线概述，具体方向以脚本为准。格式名相同不保证功能等价。详细限制、参数与依赖见 [使用说明](references/usage.md)。仅在规划其他路线时读 [转换目录](references/conversion-catalog.md)。

## 执行

```text
python <技能目录>/scripts/convert.py --input <文件绝对路径> --format <目标>
python <技能目录>/scripts/convert.py --input <文件1> --input <文件2> --format <目标>
```

1. 仅处理用户选择的文件。默认在原目录另存，保留原件，重名增加序号。可用 --output-dir 另选目录。路径用结构化参数传入，禁止拼接可执行命令。
2. 用户已明确源文件和目标且转换语义清楚时直接执行。缺少目标时只询问目标；确有信息损失决策时说明具体变化，复用已有选择，不重复索取授权。
3. 多选默认逐个转换。用户要求合并并确定顺序后用 --merge，支持图片合并 PDF 或 MP4；视频还需 fps 或原动画时长。
4. 透明图转 JPG/PDF/BMP 需 --background white 或 black。动画/多页用 --all-frames，避免丢首帧以外内容。
5. 多工作表导出数据用 --sheet 或 --all-sheets。公式默认拒绝；--formulas values 读取已有缓存且说明未重新计算，expressions 输出公式文本。原始编号、长整数与等号开头文字按数据保留。
6. 媒体默认路线只保留第一条相关音视频轨，去除额外轨道及元数据；调用者了解此范围后用 --allow-media-loss。用户要求提取音频本身已表达不要画面的意图。完整多轨/HDR/专业色彩任务不使用这一默认路线。
7. PDF 转 DOCX 是重建，复杂版式要复核。扫描或无文本页面用 --ocr，交付可编辑识别文字并说明未恢复完整排版。PDF 转 PPTX 是图片型幻灯片，需 --allow-layout-loss，不能称文字可编辑。
8. 视频 GIF 需明确 --start/--duration；--fps 控制抽帧，当前宽度为 480。视频 PNG/JPG 导出 --start 对应的一帧。
9. 内容提取、电子书重排、数据交换与原生排版导出分别说明；不得把删去图片后的纯文本叫成版式保真转换。
10. 专业转换按 [专业与跨类别说明](references/advanced-formats.md)选择参数：语音模型目录、GIS 图层和 CRS、CAD 布局、字体索引。源 CRS 缺失时不得猜测；目标格式无法保留结构、属性或动画时按明确选择处理。

## 返回结果

脚本 stdout 为 JSON，第三方日志写 stderr。每项列出 output、完整 outputs 列表、大小、实际验证及 warnings；失败项说明原因。部分成功仍提供已有成果，支持只重试失败项。

向用户提供可打开的输出路径与简短限制说明。多页/多工作表输出必须展示完整列表或输出目录，不只显示第一项。转换中不编造百分比。

临时文件与独占创建避免覆盖原件；输出发布失败时清理本次已发布项。原生图形取消、Office 超时后的进程回收和安装卸载需在入口集成阶段另行验证。

## 入口与平台

对话与未来右键入口调用同一脚本。原生菜单点击不必经过模型推理。接入时读 [Windows 入口说明](references/windows-entry.md)。天禧权限、依赖分发、右键注册和安装包规范仍待 SDK 验证；本包不是经天禧审核的上架包。

## 未实现范围

RAR、RAW、AZW3/MOBI、联系人/日历、STEP/IGES 实体 CAD、地理栅格，以及 TTF/OTF 轮廓转换仍为后续路线。DWG 适配已写但缺少 ODA 引擎实测。依赖缺失或内容不支持时明确失败，不能生成占位成果当作成功。

## 验证

执行 tests/ 下的本地测试可验证代表性样本与原件保留。测试覆盖不等于任意用户文件都可保真转换；最新实测范围见 references/verification.md。
