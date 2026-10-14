# 第五章公开验证证据

本目录从已经发布到魔搭的白名单 ZIP 中逐字节提取。作者手机原始照片、数据库、设备序列号、签名私钥和日志采集目录未纳入。公开图片来源与归因见 `data/inspection-validation/public-cracks/`；APK 台账记录为明确标记的公开测试夹具。

| 文件/目录 | 用途 |
| --- | --- |
| `benchmark-gpu-v2-16x.json`、`benchmark-gpu-v2-4x.json` | v2 原始回答、严格解析结果与耗时；每种模式 20 张图 |
| `summary.json`、`comparison-40.csv`、`semantic-review.md` | 从原始回答计算的统计与逐图核对；不作为独立语义准确率 |
| `gpu-prompt-diagnostic.json` | 提示词诊断；曾参与诊断的图片不能视为独立测试集 |
| `legacy-v1/` | 早期两种模式的原始失败与统计，保留失败历史 |
| `clean-room-v2/` | 新目录、新虚拟环境下的环境记录、40 条原始回答及执行报告；模型缓存重新校验后复用 |
| `apk-v23/` | 固定签名 Release 的首次安装、模型下载、巡检、更新及 10 项设备测试证据；包含公开证书，不含私钥 |
| `artifacts.json` | 魔搭公开 ZIP/APK 的原文件大小、SHA256 与下载地址 |
| `gpu-release-manifest.json`、`apk-v23/source-release-manifest.json` | 原发布包清单副本；路径以各自 ZIP 的根目录为基准，不是本 Git 仓库全量校验清单 |

这些是历史测量，重新运行的结果应写入另一个目录。Notebook 源文件在仓库中不含执行输出；完整可运行入口与下载说明见根目录 README。

原公开数据、原创组件和第三方代码仍按各自许可范围使用，参阅 `release-assets/`。测试通过仅适用于报告中的配置和流程；自然现场低质量、其它机型和完整视频/语音流程尚未全面验收。
