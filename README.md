# File Converter

A local file-conversion skill for documents, media, spreadsheets, 3D, CAD, geographic data and fonts.

[Website](https://aytoast.github.io/file-converter/) · [Download skill](https://aytoast.github.io/file-converter/downloads/file-converter.zip) · [Skill instructions](SKILL.md) · [Verified scope](references/verification.md)

## 文件在本机转换

将已有转换工具组织成一个可由 Agent 调用的 Skill。支持按文件和目标执行、动态查询目标、批量转换、保留原件、重名保护和输出检查。

网站是静态介绍、格式查询与下载站，不接收或转换用户文件。当前没有 Windows 右键安装程序，尚未接入天禧技能市场。

## 支持范围

| 类别 | 代表路线 |
| --- | --- |
| 办公与 PDF | Word/Excel/PowerPoint 转 PDF、文本 PDF 转 DOCX、表格提取、逐页图片 |
| 表格与数据 | CSV/TSV/XLS/XLSX/ODS、JSON/JSONL/YAML 的支持方向 |
| 图片 | 常见位图互转、HEIC 输入、动图、图标、图片合并 PDF |
| 音视频 | 常见格式互转、提取音频、片段 GIF、截图与抽帧序列 |
| 跨类别 | 本地 OCR、语音转文字/字幕、图片序列转视频、嵌入图片提取、单色矢量描摹 |
| 3D | OBJ/STL/PLY/glTF/GLB/FBX/BLEND、网格备用路线和预览图 |
| CAD | DXF 读写与 SVG/PDF/PNG；DWG 需 ODA，尚未实测 |
| 地理数据 | GeoJSON/GPKG/Shapefile ZIP/KML/GPX/FGB、坐标表与重投影 |
| 字体 | TTF/OTF ↔ WOFF/WOFF2 容器、TTC/OTC 按索引拆分 |
| 其他 | 字幕、Markdown/HTML/EPUB、ZIP/7Z/TAR 家族 |

每种格式的读取、写入、内容限制和依赖不同。详见 [使用说明](references/usage.md)、[跨类别与专业格式](references/advanced-formats.md)。

## 快速开始

Python 3.10+。在项目独立环境安装所需依赖，不会安装为 Codex 全局技能：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python scripts/convert.py --capabilities
.venv/Scripts/python scripts/convert.py --targets --input "C:/data/report.pdf"
.venv/Scripts/python scripts/convert.py --input "C:/data/table.csv" --format xlsx
```

完整办公、PDF、字幕等 Python 依赖在 `requirements-extended.txt`，OCR/ASR/3D/CAD/GIS 依赖在 `requirements-professional.txt`。按任务安装即可。

Word/Excel/PowerPoint 或 LibreOffice、Blender、ODA 和 ASR 模型属于单独的本地依赖。转换过程不自动下载 ASR 模型。其他支持本地脚本的 Agent 可读取根目录 `SKILL.md` 使用；天禧宿主权限仍需适配验证。

## 转换示例

```powershell
python scripts/convert.py --input "C:/data/report.docx" --format pdf
python scripts/convert.py --input "C:/data/report.pdf" --format docx
python scripts/convert.py --input "C:/data/scan.pdf" --format docx --ocr
python scripts/convert.py --input "C:/data/a.png" --input "C:/data/b.png" --format pdf --merge
python scripts/convert.py --input "C:/data/scene.fbx" --format glb
python scripts/convert.py --input "C:/data/drawing.dxf" --format pdf
python scripts/convert.py --input "C:/data/places.geojson" --format gpkg --target-crs EPSG:3857
```

## 验证与限制

2026-10-25 的本地完整测试：**43 项通过**，包含真实 Office、Blender、OCR、英文 ASR 和地理数据样本。它不代表所有输入输出组合都能保真转换。[验证记录](references/verification.md)

- PDF → DOCX 涉及版面重建；扫描件 OCR 输出可编辑文字，未恢复全部排版。
- 媒体默认路线保留第一条相关音视频轨，需明确接受额外轨道与元数据变化。
- TTF/OTF 轮廓转换、STEP/IGES、RAW、RAR 输入、地理栅格等未实现。
- Windows 右键菜单、安装卸载和天禧集成尚未完成。

测试命令：

```powershell
python -m unittest discover -s tests -v
```

测试的专业路线需要对应引擎。ASR 测试可用 `FILE_CONVERTER_ASR_MODEL` 指定本地 tiny.en 模型；模型不随仓库分发。

## 静态网站

`docs/` 是纯 HTML、CSS、JavaScript，通过 GitHub Pages 发布。格式目录只解释已实现路线和依赖，不执行转换。[独立界面评审](https://aytoast.github.io/file-converter/review/)

```powershell
python scripts/package_skill.py
python -m http.server 8767 --directory docs
```

网站检查使用 `python scripts/check_site.py`。浏览器测试使用 `npm ci`、`npx playwright install chromium` 和 `npm test`，覆盖搜索、复制、下载、异常状态、手机布局和独立评审页。推送到 `main` 后，GitHub Actions 通过基础转换及网站测试再发布 Pages；完整专业测试需在配置相应引擎的电脑运行。

## 许可证

本仓库原创代码采用 [MIT](LICENSE)。第三方工具、模型、字体及 Office 应用遵循各自许可证；本仓库不包含它们的二进制、权重或授权。
