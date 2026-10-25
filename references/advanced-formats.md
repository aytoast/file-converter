# 跨类别与专业格式

本地扩展实现。按任务选择依赖，完整测试环境额外依赖在 requirements-professional.txt。Blender、ODA 与 ASR 模型不包含在压缩包中，未注册到 Codex 或系统菜单。

## 跨类别转换

| 任务 | 实现与限制 |
| --- | --- |
| 音视频 → TXT/Markdown/DOCX/SRT/VTT/JSON | faster-whisper 本地模型；模型目录必须显式提供，转换过程不会自动下载模型。识别文字及时间可能有误 |
| 图片/扫描 PDF → TXT/Markdown/DOCX/JSON | RapidOCR 本地识别；Word 是可编辑识别文字，没有恢复原始完整排版 |
| 表格截图/扫描表格 → XLSX/CSV/TSV | 从文字框位置推断行列，保留编号文本；不恢复合并单元格，需检查数字与列对应 |
| 图片/扫描 PDF → 可搜索 PDF | 原图或原 PDF 保留外观，叠加隐藏文字；已有文字页面不重复添加 |
| 视频 → 图片序列 | 指定时间范围与采样帧率，返回全部 PNG 路径 |
| 图片序列/动图 → MP4 | 图片保持输入顺序；静态图按 fps，动图按原帧时长；不同尺寸留边，透明需背景，无音频 |
| PDF/DOCX/PPTX/XLSX → 嵌入图片 | 提取可读图片资源，与整页截图分开；PDF 图像遮罩和矢量资源可能需要额外处理 |
| 位图 → SVG 路径 | 单色轮廓描摹，实际生成 path；需要明确接受颜色/纹理损失，不承诺照片级还原 |
| PDF/文档 → Markdown | 保留已有内容提取路线；不同输入的标题与表格保留能力不同 |
| Word/Excel/PPT → 逐页图片 | 通过原生 Office 导出 PDF 再渲染，支持页码选择；与嵌入图片提取分开 |
| Markdown/HTML/TXT → PDF | 语义转换为 DOCX 后经办公引擎排版；不承诺复现网页的全部交互与 CSS |

```text
python scripts/convert.py --input C:/data/recording.mp4 --format srt --asr-model-path C:/models/whisper --language zh
python scripts/convert.py --input C:/data/scan.pdf --format docx --ocr
python scripts/convert.py --input C:/data/scan.pdf --format pdf --ocr --pages 1-3 --dpi 144
python scripts/convert.py --input C:/data/table.png --format xlsx
python scripts/convert.py --input C:/data/video.mp4 --format frames --start 2 --duration 3 --fps 5
python scripts/convert.py --input C:/data/a.png --input C:/data/b.png --format mp4 --merge --fps 2
python scripts/convert.py --input C:/data/animation.gif --format mp4
python scripts/convert.py --input C:/data/document.docx --format images
python scripts/convert.py --input C:/data/logo.png --format svg --allow-layout-loss --vector-threshold 128
```

音视频转音轨、片段 GIF、指定时间截图，以及图片合并 PDF 延用原有实现。TXT 与 SRT 的识别输出不等于自动区分说话人；本版没有说话人分离或翻译。

### 模型配置

RapidOCR 使用安装包中的检测与识别模型。ASR 使用 CTranslate2 格式的本地模型目录，例如 faster-whisper tiny/base/small 的相应模型包。CLI 只接受存在的本地目录；可以用 FILE_CONVERTER_ASR_MODEL 指定用户环境的默认路径。

模型下载是独立设置步骤，需要用户已有授权；下载模型不会上传用户音视频。本次只用 tiny.en 验证英文样本；中文及其他语种需要合适的多语言模型并另作质量验收。

## 3D 模型

Blender 后台进程支持 OBJ、STL、PLY、glTF/GLB、FBX、BLEND 输入，导出 OBJ/STL/PLY/glTF/GLB/FBX/BLEND 或 PNG 概览图。每次从工厂空场景开始，并禁用文件脚本，不连接当前打开的 Blender 会话。

导出后在同一后台进程重新导入，检查几何存在和包围盒尺寸。glTF 输出将引用的缓冲和图片嵌入数据 URI，避免只交付一个缺失资源的文件。FBX/GLB 等特有材质、动画、约束和插件效果仍需专项检查。

OBJ/STL/PLY 等几何输出遇到材质、骨骼、动画或修改器时要求 --allow-layout-loss。该选择表达接受相关损失，不代表引擎可以保留目标格式不支持的内容。

OFF 及无 Blender 的网格路线使用 trimesh，明确采用扁平网格，支持 OBJ/STL/PLY/OFF/GLB，需接受场景信息损失。不能把网格转换宣称为参数化 CAD 重建。

```text
python scripts/convert.py --input C:/data/scene.fbx --format glb
python scripts/convert.py --input C:/data/scene.glb --format gltf
python scripts/convert.py --input C:/data/model.glb --format stl --allow-layout-loss
python scripts/convert.py --input C:/data/model.glb --format png
```

Blender 可从 PATH、常见 Windows 安装目录或 FILE_CONVERTER_BLENDER 查找。本次使用 Blender 5.1，预览采用 CPU Cycles；没有引擎的机器不应显示依赖该引擎的目标。

## CAD 图纸

DXF 读写、审计及 SVG/PDF/PNG 导出由 ezdxf 与 matplotlib 执行。可指定 --layout，默认 Model。3D 实体使用二维顶视投影，复杂字体、外部参照、ACIS 和专业对象不保证与原生 CAD 外观一致。

DWG ↔ DXF、DWG 导出图形已编写 ODA 适配路径，需要已安装 ODA File Converter，并通过 FILE_CONVERTER_ODA 或 PATH 指明。当前没有该引擎，未实测 DWG 正向转换；能力发现会隐藏这些路线。

```text
python scripts/convert.py --input C:/data/drawing.dxf --format pdf --layout Model
python scripts/convert.py --input C:/data/drawing.dxf --format svg
python scripts/convert.py --input C:/data/drawing.dwg --format dxf
```

STEP/IGES 实体 CAD、DWG 专业实体保真及模型编辑历史尚未实现，不使用 STL 网格冒充这些结果。

## 地理数据

输入 GeoJSON、GeoPackage、Shapefile、KML、GPX、FlatGeobuf，以及明确坐标列或 WKT 列的 CSV/XLSX。输出根据本机 GDAL 写入驱动提供 GeoJSON/GPKG/KML/GPX/FGB、Shapefile ZIP 或属性表。

- 坐标系缺失时要求 --source-crs；已知源坐标系与指定值冲突时拒绝。--target-crs 执行真实重投影。
- GeoJSON/KML/GPX 输出使用 WGS84；不能通过替换标签假装坐标已经转换。
- 多图层数据要求 --layer。Shapefile 以 .shp.zip 打包关联文件，不能只交付 .shp。
- Shapefile 无法完整保留的长字段名或复杂字段拒绝转换。目标丢失字段时默认拒绝，明确接受损失后才输出并列出遗漏字段。
- GPX 支持点、路线和轨迹，不接受多边形；当前 GPX 输出只保留几何，需明确选择相关损失。
- 地理数据转 CSV/XLSX 包含 geometry_wkt，并在结果中记录 CRS；恢复时要显式指定该 CRS。表格读取的坐标字段必须指定。
- 检查输出要素数与 CRS；复杂字段、样式与所有几何精度不作无条件保真承诺。

```text
python scripts/convert.py --input C:/data/places.geojson --format gpkg --target-crs EPSG:3857
python scripts/convert.py --input C:/data/map.gpkg --format geojson --layer places
python scripts/convert.py --input C:/data/places.geojson --format shp.zip
python scripts/convert.py --input C:/data/places.shp.zip --format geojson
python scripts/convert.py --input C:/data/coords.csv --format geojson --x-column lon --y-column lat --source-crs EPSG:4326
python scripts/convert.py --input C:/data/geometry.csv --format gpkg --geometry-column geometry_wkt --source-crs EPSG:3857
```

当前支持矢量数据；GeoTIFF 等地理栅格是后续路线。

## 字体

延用 TTF/OTF 与 WOFF/WOFF2 容器转换，并支持 TTC/OTC 中按 --font-index 选择字体。输出重开并核对字形顺序。

```text
python scripts/convert.py --input C:/data/fonts.ttc --format woff2 --font-index 1
python scripts/convert.py --input C:/data/font.woff2 --format ttf
```

TTF/OTF 轮廓转换没有实现；解封装时只能导出对应轮廓类型。转换不改变字体的嵌入许可或授权范围。

## 调研与接口来源

- https://trimesh.org/trimesh.exchange.load.html
- https://ezdxf.readthedocs.io/en/stable/addons/drawing.html
- https://ezdxf.readthedocs.io/en/stable/addons/odafc.html
- https://pyogrio.readthedocs.io/en/latest/introduction.html
- https://github.com/RapidAI/RapidOCR
- https://github.com/SYSTRAN/faster-whisper
- https://github.com/fonttools/fonttools
