# OpenBMB 与魔搭紫皮书 MiniCPM 共建章节初稿

初稿交付：2026-10-11；第五章公开材料更新：2026-10-15。两章围绕可实践的任务展开，章节编号待魔搭编辑统一安排。

## 阅读顺序

| 章节 | 主模型与任务 | 初稿内容 |
| --- | --- | --- |
| [Part 3 把自己微调的 MiniCPM 装进手机](chapters/part3-minicpm-finetune-phone.md) | MiniCPM5-2B，日常记录转固定格式待办 | 训练拆解、魔搭 Notebook、LoRA、前后评测、合并、GGUF、模型上传与自定义 Android 模型注册 |
| [Part 5 用 MiniCPM-V 搭建手机巡检助手](chapters/part5-minicpmv-inspection.md) | MiniCPM-V 4.6，物业现场观察记录 | 单图基线、字段责任、Android 图像推理组件、人工确认、离线保存与台账同步 |

模型版本按公开工程可核查程度选定。4.7 迁移路径见 Part 5 最后一节；它不改变业务任务契约，需重新固定模型、视觉组件与手机引擎并验收。

## 包含的文件

- `chapters/`：两章可审阅 Markdown。
- `source-html/`：初稿阶段的 HTML 正文候选源；当前课程以 `chapters/` 的 Markdown 为准。
- `figures/`：训练与巡检流程 SVG。
- `notebooks/`：4 份未执行的 Notebook 源文件，包含文本微调、视觉基线、20 图批测和第五章公开包复现入口。
- `data/`：320 条训练、64 条验证、96 条测试，标准答案和 EvalScope 格式；另有 20 张带归因的公开裂纹样本及 3 张注明变换方法的受控图片。
- `examples/`：数据生成、严格评测、Transformers 基线、GGUF 转换、模型上传、自定义手机模型注册及模拟台账。
- `android/`：巡检 Activity、生成与记录组件、Android 设备测试，以及固定工程的原生修复补丁。
- `model-card-template.md`：模型发布填写模板。
- `release-assets/`：Android 接入、APK 安装与验收说明，以及按范围适用的许可材料。
- `results/published/`：从已公开复现包提取的原始 GPU 回答、统计、失败历史和 APK 验收证据。
- `validation.json`：各章节的验证范围与结果索引。

模型权重、完整上游工程、APK/ZIP、编译缓存、签名私钥和私人验收资料由 [.gitignore](.gitignore) 排除，仍保留在作者本机。GitHub 保存课程与复现源码，已编译安装包从下方魔搭入口获取。

## 第五章复现与安装入口

- [魔搭公开数据集仓库](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5)：公开数据、GPU 复现包、Android 源码包、课程 Markdown/ZIP 和 APK。
- [魔搭 Notebook 作品](https://modelscope.cn/gallery/pzc163/minicpm-v-inspection-part5)：按顺序执行；也可打开 [本仓库的复现 Notebook](notebooks/Part5-MiniCPM-V-Reproduce.ipynb)，它会下载并核验已发布的固定 GPU 复现包。
- [v23 APK 安装说明](release-assets/APK-INSTALL.md)：原 MiniCPM-V 首页、模型下载与聊天入口保留，巡检为内部功能模块。
- [Android 源码接入与构建](release-assets/ANDROID.md)：使用本仓库的增量代码，另行克隆固定上游工程；本仓库不包含完整 Android Studio 上游工程。
- [已发布文件的 SHA256 与下载地址](results/published/artifacts.json)。

`examples/verify_part5_release.py` 在已解压的 GPU 复现包中执行，用其 `release-manifest.json` 校验文件。`examples/build_part5_release.py` 保留作者的发布组装流程，依赖本机原始验收目录；它不是读者运行推理的前置步骤，也不应覆盖既有发布 ZIP。

## 不需要 GPU 的本地检查

要求 Python 3.11+，在项目根目录执行：

```bash
python examples/build_data.py
python examples/verify_local.py
```

模拟业务流程：

```bash
python examples/ledger.py
```

另一个终端执行：

```bash
python examples/offline_queue.py add data/inspection_confirmed_example.json
python examples/offline_queue.py sync
```

示例确认记录是教学夹具，包含占位图片哈希，未进行真实图片推理。

## 验证状态

6 项本地检查覆盖划分去重与标签依据、非法 JSON 与字段计分、草稿契约、确认门槛、ACK 丢失后的幂等重试、状态版本冲突、离线队列恢复和 localhost HTTP 同步。4 份 Notebook 保留未执行状态；源码语法检查通过。

| 范围 | 已完成 | 证据与限制 |
| --- | --- | --- |
| GPU v2 公开 20 图 | A10 上 16x、4x 各 20/20 严格四字段合格；平均分别 1044.2、1055.1 ms | [统计](results/published/summary.json)、[逐图语义核对](results/published/semantic-review.md)；结构合格不等于观察准确，样本不是 20 个独立现场 |
| GPU 环境复现 | 新目录、新虚拟环境、普通 Python 3 内核的 5 单元全部执行；40 条原始回答与首次 v2 一致 | [环境复现报告](results/published/clean-room-v2/clean-room-report.json)；复用了重新校验的官方模型缓存 |
| v23 固定签名 APK | 荣耀真机首次安装、App 内下载两份权重、原文字/图片聊天、巡检离线生成、人工确认、本地保存、同步失败保留、同步成功与状态刷新；7 项契约/SQLite、3 项预处理测试通过 | [验收报告](results/published/apk-v23/acceptance-report.json)、[验收说明](release-assets/APK-VALIDATION.md)；同签名同版本覆盖保留数据，未测试未来版本升级；仅验证此 arm64/4KiB 设备 |
| 历史失败 | GPU v1 两模式各 0/20 严格合格；旧 Android v20 连续 20 图无闪退、19/20 结构合格；受控低质量 6 次仅 1 次结构合格 | [GPU v1 原始证据](results/published/legacy-v1/)；Android 与 GPU 提示不同，不能作为同提示量化比较 |

APK 首次公开图片生成出现非法 JSON，第二次通过，原始失败已保留。自然低质量现场、独立语义评审、完整视频处理和语音合成尚未全面验收。第三章 GPU 训练、GGUF 转换及可选 4.7 迁移仍未完成；第五章的测试不能计为这些项目完成。完整公开证据索引见 [results/published/README.md](results/published/README.md)。

## 内容与代码许可

`data/` 中通过本包生成的待办合成教学样本与生成规则可按 CC0-1.0 使用。其余本次新增教程、图示与示例代码提供为共建审稿材料，正式公开时由作者与魔搭确认最终许可；引用的模型、代码工程与数据遵循各自许可，不因本包而改变。无需分发上游完整源码即可使用本包的接入脚本。

2026-10-15 作者明确授权第五章公开复现包：20 图子集及新增清单/核对材料采用 CC BY 4.0，包内原创示例代码和复现说明采用 MIT，详见 [代码许可](release-assets/LICENSE-CODE-MIT)、[数据许可](release-assets/LICENSE-DATA-CC-BY-4.0.md) 和 [第三方说明](release-assets/THIRD_PARTY_NOTICES.md)。原发布清单副本保存在 [GPU 清单](results/published/gpu-release-manifest.json) 与 [Android 源码清单](results/published/apk-v23/source-release-manifest.json)。公开 GitHub 不扩张该许可范围：上游代码、模型、其它章节及未纳入授权清单的课程正文保留各自权利。
