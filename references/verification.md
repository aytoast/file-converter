# 本地验证记录

日期：2026-10-25。环境：Windows、Python 3.10、隔离虚拟环境；Word/Excel/PowerPoint 16.0 与 Blender 5.1 原生引擎可用。扩展依赖版本见 requirements-extended.txt、requirements-professional.txt。

没有安装到 Codex、注册系统菜单或连接天禧。依赖安装位于项目 .cache 下的测试环境，压缩包不包含虚拟环境、第三方二进制或 Office 安装文件。

## 测试结果

基础版本的 28 项测试继续保留；本轮新增 15 项跨类别与专业测试。完整运行共 43 项，全部通过，耗时 156.273 秒，退出码 0，无跳过项。测试位于 tests/。

主要验证：

- 图片 JPG/PNG/WebP/BMP/TIFF/GIF/ICO/AVIF 输出、HEIC 输入、动画帧数、透明背景、EXIF 方向、图片合并 PDF 顺序。
- 当前 FFmpeg 检测出的 9 种音频和 9 种视频输出；每项完整解码输出，另测片段 GIF 和视频截图。
- CSV/XLSX/JSON 数据往返，前导零、长整数、等号开头文字、多个工作表选择、公式策略与超长单元格拒绝。
- ODS 数据输出及经 Excel 转 XLSX。
- Word/Excel/PowerPoint 原生 PDF 导出；Word 导出 ODT/RTF、Excel 导出 XLS、PowerPoint 导出 ODP。
- 文本 PDF 重建可编辑 DOCX、逐页图片、页码选择、纯文字提取、表格提取 XLSX，以及需明确选择的图片型 PPTX。
- 扫描 PDF 明确报告需要 OCR，避免生成不含可编辑内容的占位 Word。
- Markdown → DOCX/EPUB、EPUB → HTML/PDF。
- SRT → VTT/ASS/SSA，核对事件文字与时间。
- JSON/YAML 往返及重复键拒绝。
- SVG 渲染，字体 WOFF2/TTF 往返与轮廓类型筛选。
- ZIP/TAR.GZ/7Z 重打包与文件内容一致性，危险路径拒绝。
- 原件字节保持、重名保护、批量部分失败、临时文件清理、CLI JSON 返回和动态目标发现。

新增验证：

- 真实本地 ASR：Windows SAPI 合成固定英文测试音频，用本地 tiny.en 模型生成文字和 SRT，检查关键词和字幕事件。英文模型接收中文语言请求时明确拒绝。
- OCR：英文和中文印刷文字、金额与前导零编号；图片/扫描 PDF 转可编辑文字 DOCX、表格截图转 XLSX。
- 可搜索 PDF：检查能提取识别文字，并比较扫描 PDF 加隐藏文字前后的渲染像素，样本外观不变。
- 图片序列/动图转 MP4、视频按时段抽 PNG 序列、单色轮廓描摹为真实 SVG 路径。
- PDF/DOCX/PPTX 提取嵌入图片；Office 按页渲染图片；Markdown 经 Word 导出 PDF。
- Blender 独立后台进程：GLB 导出 OBJ/STL/PLY/glTF/FBX/BLEND 并重新导入，检查几何和包围盒；PNG 概览；glTF 缓冲内嵌；OFF 网格备用路线。
- DXF 读写审计，以及 SVG/PDF/PNG 实际渲染；缺失 ODA 时 DWG 路线明确拒绝。
- 地理数据：GeoJSON/GPKG/FGB/KML/Shapefile ZIP/属性表、真实坐标重投影及反向核对；CSV 坐标列、图层选择、长字段拒绝、配套 .prj/.dbf 打包。
- TTC 字体集合按索引导出，缺少索引时拒绝，并核对输出字形顺序。

## 版面抽查

另生成一份包含中文/英文标题、正文、日期、前导零编号和表格的 DOCX，运行 Word → PDF → 可编辑 DOCX → PDF。原始 PDF 与重建 PDF 均渲染并人工查看。

样例中正文与表格可读，编号 0000123 保留。重建版本的标题字体及装饰线出现变化，证明该路线属于可编辑重建，不能称为像素级还原。复杂用户文档仍需预览和专项验收。

另外渲染并人工查看 3D 长方体概览和 DXF 线框/圆/文字样例，确认图形实际可见。3D 预览使用 CPU Cycles，避免 Blender 不同版本的 EEVEE 引擎名称差异；没有修改当前 GUI 场景。

## 未验证或未实现

- LibreOffice 备用引擎存在实现，当前机器未安装，未作端到端实测。
- 各输出格式并未与所有输入格式做穷举组合；代表性样本通过不等于全部组合均保真。
- ODA 本机未安装。DWG 适配代码存在，未执行 DWG 正向转换，不作实测支持承诺。
- ASR 只实测 tiny.en 英文模型；其他语言需多语言模型和相应样本。OCR 已测中英文印刷字，手写、复杂版面和识别准确率没有全面验收。
- RAR、RAW、AZW3/MOBI、联系人/日历、STEP/IGES 实体 CAD、地理栅格和字体轮廓转换尚未实现。
- 极大文件、所有损坏文件、全部 Office 对象、HDR、多轨保留和专业色彩尚未全面验收。
- Windows 原生菜单、进度窗口、图形取消、Office 超时进程回收、安装卸载与天禧市场接入尚未完成。
- 本包依赖多种开源引擎，上架与二进制分发前需核对相应许可证及平台政策。
