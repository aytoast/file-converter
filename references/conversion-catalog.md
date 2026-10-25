# 文件转换范围与路线

调研日期：2026-10-25。面向联想 Windows 个人用户的产品能力规划，覆盖常见办公、媒体、创作和数据文件，不穷举所有历史或私有格式。

本文是路线目录，列出工具可行性与产品范围，不等于其中全部路线已实现。随后已扩展本地脚本，并在项目隔离环境安装测试依赖，未安装到 Codex 或注册系统扩展。当前可执行能力以 SKILL.md、convert.py --capabilities 及 [验证记录](verification.md)为准。

## 1. 总体判断

用户提出的音频互转、视频互转、图片互转、Office、CSV/XLSX、PDF/DOCX 均属于产品核心范围。之前的脚本是窄范围原型，不应据此缩减产品定义。

常见音频、视频、位图格式通常可以在相应解码器和编码器可用时互转。目标格式可能无法承载全部源信息；有损文件转无损格式不会恢复已丢失的信息。

每条路线分别记录读取支持、写入支持、源内容要求、依赖和可保留属性。一个工具“支持某格式”不等于能读写，也不等于该格式能与全部其他格式双向互转。

下文 → 表示指定方向，↔ 表示可规划双向路线；双向不保证往返恢复原件。表内“成熟”表示有现成工具路线，不代表本产品已经测试。

## 2. 核心类别

| 类别 | 应覆盖的路线 | 执行方式与条件 | 关键变化 |
| --- | --- | --- | --- |
| 常见音频 | MP3、WAV、FLAC、AAC、M4A、OGG、Opus、AIFF、WMA 间有条件互转 | FFmpeg；逐项检测解码、编码和封装支持 | 有损再编码会损失音质；保留声道、采样率、章节和封面需逐项检查 |
| 音频封装 | AAC → M4A，合适编码的音轨在兼容容器间重新封装 | 流复制优先，编码兼容时无需重编码 | M4A 可以承载 AAC 或 ALAC；扩展名不代表压缩方式 |
| 常见视频 | MP4、MKV、MOV、AVI、WebM、WMV、FLV、MPEG、TS、MTS/M2TS 间有条件互转 | FFmpeg；容器和编码分别判断 | 分辨率、帧率、HDR、色彩、透明度、多音轨、字幕及章节可能变化 |
| 视频兼容性 | HEVC/AV1 视频 → H.264 MP4 | 解码后重新编码；常见兼容性需求 | 即使前后都叫 MP4，也可能发生真实转换；重新编码可能有损 |
| 常见静态图片 | JPG/JPEG、PNG、WebP、BMP、TIFF、AVIF 间有条件互转 | Pillow 或 ImageMagick 及可用插件 | 透明度、位深、ICC、EXIF、尺寸；JPG 不支持透明通道 |
| 手机照片 | HEIC/HEIF → JPG、PNG；反向输出按编码器能力提供 | 专用 HEIF/HEIC 解码与编码依赖 | HEIF 可能含多图、深度信息、HDR；单张导出不是完整资产保留 |
| 相机原始照片 | CR2/CR3、NEF、ARW、DNG 等 → JPG、PNG、TIFF | RAW 解码与显影工具；逐型号验证 | 显影涉及白平衡、曝光与色彩；不能由 JPG 逆向恢复原始 RAW |
| 动图 | GIF、APNG、动画 WebP 间有条件互转 | 帧、时长、循环和画面处置规则逐项处理 | GIF 颜色限制，透明度和帧间处理可能改变 |
| Word 类文档 | DOC、DOCX、ODT、RTF 间有条件互转；分别 → PDF、TXT、HTML | Word 或 LibreOffice；语义文档可用 Pandoc | 字体、分节、批注、修订、宏、公式和嵌入对象需要检查 |
| 表格 | CSV ↔ XLSX；TSV ↔ CSV/XLSX；XLS、XLSX、ODS 间有条件互转 | 表格读写工具或 Excel/LibreOffice | CSV 是单表文本；公式、样式、多工作表、图表不能完整保留 |
| 表格导出 | XLSX/XLS/ODS → PDF、HTML；选区/工作表 → PNG | 实际表格排版引擎或选区渲染 | 需确定工作表、打印区域、缩放和分页，不能只导出首个工作表 |
| 演示文稿 | PPT、PPTX、ODP 间有条件互转；分别 → PDF、逐页 PNG/JPG | PowerPoint 或 LibreOffice 等支持的导出引擎 | 动画、转场、嵌入媒体、备注和字体可能变化 |
| PDF 正向导出 | DOCX/XLSX/PPTX/ODT/ODS/ODP → PDF | 原生办公引擎或兼容渲染引擎 | 渲染后检查页数、字体、表格及裁切 |
| PDF → Word | 普通文本 PDF → DOCX | Word PDF 重排或专用布局重建工具 | 标题、段落、栏、表格等是推断结果，复杂版式不保证复原 |
| 扫描 PDF → Word | 扫描 PDF/图片 → OCR → DOCX | OCR、版面分析和 DOCX 生成 | 字符识别错误与排版重建错误分别标明；仅加 OCR 文本层还不是 Word 转换 |
| PDF → 表格 | 文本 PDF 表格 → CSV/XLSX；扫描表格先 OCR | 表格检测、单元格重建、字段检查 | 合并单元格、多页表头、小数、负号、日期和前导零需重点核对 |
| PDF ↔ 图片 | PDF → 每页 PNG/JPG/TIFF；图片 → 单页/多页 PDF | PDF 渲染与图片封装 | 页面渲染不同于提取嵌入原图；图片 PDF 默认没有可编辑文字 |
| PDF → 演示 | PDF → 每页一张图片的 PPTX；可编辑 PPTX 为独立高级路线 | 页面封装或版面重建 | 必须区分“外观保留”和“文字/图形可编辑”，不能混称完全还原 |

工具证据：[FFmpeg](https://ffmpeg.org/ffmpeg.html)、[FFmpeg 格式支持](https://ffmpeg.org/general.html)、[ImageMagick 格式表](https://imagemagick.org/formats/)、[Pillow](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)、[LibreOffice 过滤器](https://help.libreoffice.org/latest/en-US/text/shared/guide/convertfilters.html)、[Word PDF 重排限制](https://support.microsoft.com/en-gb/word/opening-pdfs-in-word)、[PDF 表格提取](https://tabula.technology/)、[OCRmyPDF](https://ocrmypdf.readthedocs.io/en/latest/introduction.html)。

## 3. 表格转换应单独处理的决策

- CSV → XLSX：识别编码、分隔符、引号与表头。身份证号、邮编、订单号与长数字按字段语义保留，不能统一转成浮点数或科学计数法。
- XLSX → CSV：确定导出工作表，或每张工作表各输出一个 CSV。公式导出选择结果或表达式；没有可靠重算引擎时不能把过时缓存结果当成最新值。
- 输出到 Excel 的外部文本按数据写入，避免被意外解释成公式。合法公式要走明确的公式保留路线。
- XLSM → XLSX：会移除宏，不能静默操作。XLSB 等格式按具体读写引擎提供，不从“可读取”推断“可导出”。
- 数值表与办公工作簿分开实现：pandas 等适合数据交换，不应直接用于完整保留 Excel 样式、图表、宏和公式关系。

数据引擎证据：[pandas 输入输出能力](https://pandas.pydata.org/docs/user_guide/io.html)。

## 4. 值得补充的常见路线

| 类别 | 转换路线 | 用户用途与边界 |
| --- | --- | --- |
| 字幕 | SRT ↔ VTT ↔ ASS/SSA，在工具支持范围内转换 | 平台投稿、剪辑与播放器兼容；ASS 的字体、位置和特效转 SRT 会丢失 |
| 文本内容 | Markdown ↔ HTML ↔ DOCX/ODT，在各方向读写能力内转换；分别导出 PDF | 笔记、文档与网页发布；复杂排版与扩展语法不保证往返 |
| 文本编码 | UTF-8 ↔ UTF-16 ↔ GB18030，指定换行规则 | 解决导入乱码和系统兼容；未知编码存在歧义，不能损坏后再猜回原文 |
| 电子书 | EPUB、AZW3、MOBI、FB2、TXT、HTML、DOCX 间按 calibre 支持方向转换；导出 PDF | 设备阅读兼容；固定分页转流式排版需重排，处理可合法读取的文件 |
| 矢量设计 | SVG → PNG/JPG/PDF；支持的 PDF/SVG 内容间转换 | Logo、插图、办公插图与印刷；滤镜、字体和嵌入位图分别处理 |
| 图标 | PNG → 多尺寸 ICO；ICO → PNG；ICNS 按平台工具处理 | Windows 图标、网站图标；不同尺寸需实际生成，不只改后缀 |
| 压缩包 | ZIP ↔ 7Z；RAR → ZIP/7Z；TAR、TAR.GZ、TAR.XZ 间重打包 | 解包再压缩；7-Zip 可读 RAR 不等于能创建 RAR；GZ/XZ 本身通常压缩单个数据流 |
| 数据交换 | CSV/TSV ↔ 扁平 JSON/JSONL ↔ XLSX；Parquet/Feather ↔ CSV/XLSX | 数据导入导出；嵌套对象需字段映射，类型、精度和行数限制需检查 |
| 结构化配置 | JSON ↔ YAML ↔ XML 的受约束子集 | 需明确 schema；注释、重复键、属性、命名空间和数据类型不普遍可逆 |
| 邮件文件 | EML/MSG → HTML、TXT、PDF，并另存附件 | 邮件留档、交付；正文转 PDF 不等于附件也已保留，完整 EML/MSG 互转另评估 |
| 联系人 | VCF/vCard ↔ CSV/XLSX，按字段映射 | 通讯录迁移；多号码、标签、头像、姓名拆分存在一对多关系 |
| 日历 | ICS → CSV/XLSX；结构明确的 CSV/XLSX → ICS | 整理日程和批量导入；时区、重复规则与例外日期不能被普通表格默默抹掉 |

工具证据：[Pandoc](https://pandoc.org/MANUAL.html)、[calibre](https://manual.calibre-ebook.com/generated/en/ebook-convert.html)、[Inkscape](https://inkscape-manuals.readthedocs.io/en/latest/export-pdf.html)、[7-Zip 的读写区别](https://www.7-zip.org/)、[Python 编码处理](https://docs.python.org/3/library/codecs.html)、[MSG 提取工具](https://github.com/TeamMsgExtractor/msg-extractor)、[vobject](https://pypi.org/project/vobject/)、[icalendar](https://icalendar.readthedocs.io/en/latest/)。

## 5. 跨类型提取和识别

这些路线值得纳入“转换为”的产品范围，但要有独立名称和验收。生成内容的步骤应明确，不能把提取或模型推断称为无损格式转换。

| 输入 → 输出 | 实际操作 | 用户必须知道的变化 |
| --- | --- | --- |
| 视频 → MP3/WAV/FLAC | 提取音轨，必要时转码 | 可以选择音轨，画面不会进入音频文件 |
| 视频 → GIF/动画 WebP | 片段转动画 | 需时段、帧率和尺寸；通常无音频，整段大视频不宜默认输出巨大 GIF |
| 视频 → PNG/JPG 序列 | 抽帧 | 需频率或关键帧规则；输出大量文件 |
| 图片序列/GIF → MP4 | 编排与转码 | 需顺序、帧率或每张时长；不能推断原本不存在的音轨 |
| 音视频 → TXT/DOCX/SRT/VTT | 语音识别与时间对齐 | 是 ASR；名称、术语和时间轴可能需要校正 |
| 图片/扫描件 → TXT/DOCX | OCR 与排版重建 | 识别结果可能有误；保留原图供检查 |
| 表格截图 → XLSX/CSV | OCR 与表格结构重建 | 金额、日期、合并单元格、行列顺序需要预览核对 |
| 扫描 PDF → 可搜索 PDF | 增加 OCR 文本层 | 外观可保留，但识别出的隐藏文字不是天然正确 |
| PDF/Word → Markdown | 提取内容与结构 | 适合阅读与知识库；布局、栏与公式需检查 |
| PDF → SVG | 提取/重建页面中的矢量对象 | 页面含位图时不能因此变成真正矢量素材 |
| PNG/JPG → SVG 路径 | 描摹/矢量化 | Logo 和轮廓较适合；把位图嵌进 SVG 不算路径矢量化 |
| PDF/Office → 图片资源 | 提取嵌入图片 | 与整页转图片不同；要保留源图片关联位置 |

工具证据：[Whisper 语音识别](https://github.com/openai/whisper)、[OCRmyPDF](https://ocrmypdf.readthedocs.io/en/latest/introduction.html)、[PyMuPDF4LLM](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/index.html)、[Inkscape 描摹限制](https://inkscape-manuals.readthedocs.io/en/latest/tracing-an-image.html)。具体输出格式还需拼接文件写入与验证步骤。

文本转音频、文稿生成 PPT、音乐转 MIDI 也可作为后续独立能力。前两类是合成或内容生成，后一类是音乐转录；不纳入首批普通文件格式转换承诺。MIDI 可以由音源渲染成音频，但音频逆向转 MIDI 不能当作普通可逆转码。

## 6. 深挖后的专业扩展

| 类别 | 可研究路线 | 专业条件 |
| --- | --- | --- |
| 3D 网格 | OBJ、STL、PLY、glTF/GLB 间按工具实际读写能力转换；FBX 选择性支持 | 单位、坐标轴、法线、材质、贴图和动画；STL 不能承载完整材质与骨骼；FBX 输出需验证成熟度 |
| CAD 图纸 | DWG ↔ DXF；图纸 → PDF/PNG | 依赖 CAD 引擎或 ODA 工具，检查版本、图层、单位、字体与外部参照 |
| 地理数据 | GeoJSON、KML、GPX、Shapefile、GeoPackage 间按数据模型转换 | 坐标系、几何类型、字段长度；Shapefile 是多个关联文件，CSV 地图数据需指定坐标列 |
| 字体容器 | TTF/OTF → WOFF/WOFF2；Web 字体解封装为对应原始轮廓格式 | 需要相应压缩依赖；轮廓类型转换另处理，不能把 OTF/TTF 当作改后缀；检查字体许可 |
| 科研数据 | HDF5、NetCDF、MAT、NPY、Parquet 等按变量映射导出 | 数组维度、单位、属性和大文件大小；不是全量压成一张 CSV 即可 |
| 磁盘镜像 | VHD/VHDX、VMDK、QCOW2 等在专用工具支持内转换 | 另做容量、快照、启动与文件系统验收，不复用普通文档流程；不列首批 |
| 创作工程 | PSD、AI、INDD、音频工程等 → 可交付格式 | 优先原生应用或经过验证的适配；图层、链接素材、插件与编辑历史不可普遍保留 |

其中 3D、DXF、地理矢量与字体已有本地扩展，具体方向及条件见 [扩展说明](advanced-formats.md)。科研数据、磁盘镜像与任意创作工程尚未完成逐格式工具选型和可行性验证，不据此对外宣传支持。

已查工具证据：[Assimp 导入导出列表](https://raw.githubusercontent.com/assimp/assimp/master/doc/Fileformats.md)、[DWG/DXF 与 ODA](https://ezdxf.readthedocs.io/en/stable/addons/odafc.html)、[GDAL 矢量驱动](https://gdal.org/en/stable/drivers/vector/index.html)、[FontTools](https://github.com/fonttools/fonttools)。

## 7. 产品优先级

### 核心交付范围

1. 常见音频互转、视频互转与视频提取音频。
2. JPG/PNG/WebP/BMP/TIFF、HEIC/HEIF 的常见图片转换；动图作为独立分支。
3. DOC/DOCX/ODT/RTF 与 PDF 导出。
4. CSV/TSV/XLS/XLSX/ODS；包括编码、工作表与字段保护。
5. PPT/PPTX/ODP 与 PDF、图片导出。
6. PDF → DOCX；普通文本、扫描与复杂布局分别处理。
7. PDF → XLSX/CSV、PDF ↔ 图片，以及图片合并 PDF。

PDF → DOCX 是核心需求，不能仅因需要复杂引擎就从范围删去；应按不同文件类型提供正确流程、质量检查与失败说明。

### 随后补齐

字幕、Markdown/HTML、EPUB 电子书、SVG/ICO、ZIP/7Z 重打包，以及 OCR/ASR。后两项按用户希望的“提取文字/生成字幕”展示，不伪装为纯转码。

### 专业扩展

RAW 显影、数据交换、邮件/联系人/日历、3D/CAD/GIS、字体。逐类核实目标用户和依赖体积，避免首次安装携带所有工具。

## 8. 右键菜单如何使用此目录

菜单只列当前源文件、目标内容需求和已安装工具确实支持的转换。读取成功但无目标写入能力的格式，不列为输出选项。目标分为“导出整个文件”“提取音频/文字/表格”和“高级重建”，但用户只需看到清楚的操作名称。

示例：右键 PDF 可出现“Word 文档”“Excel 表格”“逐页图片”“提取文字”“可搜索 PDF”；选择 Word 后检测页面类型再选引擎。复杂页面需告知转换限制或给结果预览，不让用户先猜 PDF 的内部结构。

运行时路线应具备：源类型与内容检测、目标格式、工具及最低能力检查、必要参数、预期损失、输出验证与当前实现状态。用户不需要理解这些内部字段。

加密或损坏文件、缺少依赖和不支持的内容应明确报告。改扩展名、截图塞入可编辑容器、将未知结构直接转成文字，不得当作相应高质量转换成功。

## 9. 维护与验证

工具官方格式表是能力候选来源；运行时检测与样本测试决定实际支持。每条路线分别验证有效输出、原件不变、内容完整性及该类别的关键属性。

PDF2DOCX 可作为候选评估，但上游已声明不再由 Artifex 主动维护，不能仅因存在现成库就视为长期稳定方案：[项目状态](https://github.com/ArtifexSoftware/pdf2docx#%EF%B8%8F-project-status)。办公文档转换还需对比 Word/Excel/PowerPoint 原生引擎与 LibreOffice 的实际结果。

最新版本已完成基础、跨类别识别和专业路线的代表性样本验证，详见 [验证记录](verification.md)。未覆盖的格式仍为规划；本包尚未通过天禧验收。
