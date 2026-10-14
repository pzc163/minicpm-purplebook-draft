---
license: CC-BY-4.0
tags:
  - MiniCPM-V
  - inspection
  - reproducibility
multi-modal:
  image-captioning:
    languages:
      - cn
    resolutions:
      - 227 x 227
    encoding:
      - jpeg
---

# MiniCPM-V 巡检实践：第五章复现包

固定 MiniCPM-V 4.6 模型提交，在魔搭 A10 上复现单张图片基线和20张公开混凝土图片的16x/4x开发回归。配套原MiniCPM-V Android App的巡检模块、严格解析、人工确认、本地保存及显式台账同步代码。

数据 CC BY 4.0；原创代码和本包复现说明 MIT；上游工程、依赖和模型保留各自许可。参阅许可文件与第三方说明。模型权重、上游完整工程和私人照片/记录不在公开包中。另提供下方固定签名实践版APK及源码构建补充包；APK整体不以数据集CC BY 4.0或原创组件MIT重新授权。

## 第五章课程正文

[下载课程Markdown](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5/resolve/master/part5-minicpmv-inspection.md?view=false)；[下载正文与流程图离线包](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5/resolve/master/part5-course.zip?view=false)。课程包含任务契约、Notebook基线、Android模块接入、离线确认、台账同步、实测结果及待验证范围。

离线包保留`chapters/part5-minicpmv-inspection.md`与`figures/inspection-workflow.svg`的原始相对目录，两份文件与作者本地原稿逐字节一致。独立Markdown仅将流程图地址改为本仓库HTTPS链接，正文没有其它修改。课程ZIP为18348字节，SHA256：`835cbbce2a9a57e57bb75d473f310354f4b7a06ed78d92a35efac50dd1d6b743`；独立Markdown SHA256：`5d11578b35cca09e289bb2e544276465e0facdaeccb469d5125555588a0f0c9a`，其它校验见`COURSE-SHA256.txt`。

课程内代码命令在下方对应代码包的解压根目录执行。`results/part5-validation/...`是作者本地历史验收路径，公开证据见GPU包`results/published/`、新环境执行证据ZIP和Android包`acceptance/`。文中`verify_local.py`是跨章节本地验证脚本，并非公开Notebook运行步骤；课程离线包README解释对应关系。课程正文与流程图保留原作者权利，不因数据集标签而自动适用CC BY 4.0。

## Android 安装包与源码构建补充

[下载固定签名APK](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5/resolve/master/MiniCPM-V-demo-Android-v2.5.apk?view=false)：MiniCPM-V 巡检实践版，2.5 / versionCode23，独立.practice包名，原MainActivity唯一入口，arm64、minSdk24、Release不可调试。21137824字节，SHA256：`6615b7de73245a2dde9f45dae12da46298fe46bc97022a24329213afedba1283`。

[安装与更新说明](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5/resolve/master/APK-INSTALL.md?view=false)；[下载源码与验收补充包](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5/resolve/master/part5-apk-v23-source.zip?view=false)，77940字节，SHA256：`777b64f9878cfbb548c231dd48933c9dc38deef6b516f122624b8ac94e0a560e`。该ZIP包含原创Android模块、增量补丁、固定签名构建脚本、公开证书、许可全文、匿名化验收报告和原始失败/成功样例；需配合固定上游工程，不包含私钥、口令、模型或测试组件APK。

固定证书SHA256：`3eddc4d89ab27dc97302e839da128905e71779c276cd34c79e2aded29e230791`。新包首次安装、App内两份权重实际下载及SHA256、原文字/图片聊天、模块往返、离线生成、人工核对本地保存、同步失败保留、显式同步与状态刷新完成。同签名同版本覆盖更新后模型/草稿/正式记录保留，7项契约/存储与3项预处理设备测试通过。

本次一张公开图尝试两次：首次非法`missing_fields:[][]`被拦截，第二次通过；宽泛英文对象仍经人工核对修改。这是流程验收，不是独立准确率或必然一次成功的承诺。语音合成、完整视频处理、自然低质量场景、独立语义评审与其它机型未全面验证。模型权重约1.53GiB，从原模型管理下载，不包含在APK。旧.inspection包资料留在原包，没有迁移。原GPU ZIP与其SHA256保持不变。

## 公开运行入口与执行证据

[在魔搭运行本章Notebook](https://modelscope.cn/gallery/pzc163/minicpm-v-inspection-part5)：点击“运行”，选择GPU实例和普通Python3内核，按顺序执行。分享快照先匿名下载固定SHA256的本包，再运行下方流程。

[下载复现包](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5/resolve/master/part5-reproduction-v2.zip?view=false)，433393字节，SHA256：`55fee5d70e416e310573c08a3a2739ad4482a4f590b298b7ca307d91d15670b5`。

[下载新环境执行证据](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5/resolve/master/part5-clean-room-results.zip?view=false)，SHA256：`4ed5d740452afe068f14cebe7f08d187728e433f0230e7796c0c13a899c1cd5b`。2026-10-15新目录、新虚拟环境、默认Python3内核中，5个代码单元全部执行无错误；16x/4x各20/20严格结构合格，40条回答与首次v2逐条一致。复用官方基础CUDA栈与权重缓存，模型文件逐个重新校验，并未另建云实例或重新下载权重。两份公开ZIP均已匿名取回核对。

## 从零运行

1. 选择带可用 NVIDIA GPU 和CUDA PyTorch的魔搭Notebook实例。实测基础镜像为Python3.12.13、PyTorch2.13.0+cu130、torchvision0.28.0、A10；预留约4GB显存和至少5GB磁盘空间。其它基础镜像需要重新核对兼容性。
2. 下载本仓库的 `part5-reproduction-v2.zip`，解压到工作目录，打开 `part5-release/notebooks/part5_reproduce.ipynb`。选择普通Python3内核，依次运行所有单元。
3. Notebook先校验本包文件，再在本目录新建`.venv-part5`并安装固定推理依赖；沿用基础镜像匹配的CUDA PyTorch/torchvision。它不依赖作者原实例中的虚拟环境或专用内核。
4. 从OpenBMB官方仓库固定提交 `fd02313ad21ac485c595cb01231a3bded449cff5` 下载9个模型文件，并逐文件校验SHA256。权重约2.5GiB。若已经缓存，可在Notebook第二单元执行前设置 `os.environ['PART5_MODEL_DIR']='/你的模型缓存目录'`；仍须通过官方清单校验。
5. 单图结果、40条新回答、耗时及环境记录写入 `results/reproduction/`；发布时原始结果保留在 `results/published/`，新结果不会覆盖旧证据。

命令行等效步骤（在解压后的part5-release目录）：

```bash
python examples/verify_part5_release.py
python examples/bootstrap_part5.py
.venv-part5/bin/python examples/download_vision_model.py --revision fd02313ad21ac485c595cb01231a3bded449cff5 --out models/minicpm-v-4.6
.venv-part5/bin/python examples/vision_batch.py --model models/minicpm-v-4.6 --manifest data/inspection-validation/public-cracks/manifest.json --downsample 16x --out results/reproduction/benchmark-gpu-v2-16x.json
.venv-part5/bin/python examples/vision_batch.py --model models/minicpm-v-4.6 --manifest data/inspection-validation/public-cracks/manifest.json --downsample 4x --out results/reproduction/benchmark-gpu-v2-4x.json
.venv-part5/bin/python examples/analyze_gpu_v2.py --results results/reproduction --manifest data/inspection-validation/public-cracks/manifest.json --out results/reproduction
```

## 实测结果与边界

2026-10-15，A10，切片1、思考关闭、确定性生成、384token上限。每种模式加载一次模型；每图使用独立消息。提示v2哈希 `0c3fed70240a1639d25d0f6057972c46f9d21abf0925ce1fd19e038d51040fdb`。

| 指标 | 16x | 4x |
| --- | --- | --- |
| 严格四字段JSON | 20/20 | 20/20 |
| 完整推理平均 | 1044.2 ms | 1055.1 ms |
| 完整推理中位数 | 998.9 ms | 997.2 ms |
| P95，线性插值 | 1118.6 ms | 1167.8 ms |
| PyTorch显存分配峰值 | 2645.7 MiB | 2739.4 MiB |
| 宽泛“表面/surface”对象 | 19/20 | 16/20 |

完整时间包含图像预处理、视觉编码、生成和解码，不含模型加载。首token指token ID到达，不是UI首个文字；显存统计是PyTorch分配器，不是整卡占用。一次运行不能证明稳定性能。

源正类/负类各10张227×227裁剪图；没有可靠原场景映射，不能称20个独立现场。01、02、11曾参与提示诊断，本次是开发回归，不是独立盲测。结构合格不等于描述准确：第5、6张没有明确提出裂缝，第19张与源负类标签有分歧，部分输出还包含具体空间/材质猜测或英文。完整核对见 `results/published/semantic-review.md`。旧v1两模式均0/20契约通过，原始失败回答完整保留。

Android v23仍使用v1提示，GPU v2与手机不是相同提示的量化对照。v23恢复原首页、模型下载、聊天/语音页面和巡检往返，保留照片与正式记录。旧v20公开20图连续推理19/20结构合法、平均21.57秒，仅为历史配置。固定签名Release已补齐三项预处理测试；自然低质量场景和独立语义评审仍待验收；本包不声称第五章全部场景都已通过。

## Android与教学台账

按 `ANDROID.md` 固定上游工程并应用原创接入模块和增量补丁。桌面入口保留原MiniCPM-V主界面，巡检通过内部按钮进入；新用户从原模型管理下载4.6语言和视觉组件。

本地业务示例：一个终端执行 `python examples/ledger.py`，另一个终端执行 `python examples/offline_queue.py add data/inspection_confirmed_example.json`、`python examples/offline_queue.py sync`。该JSON是占位教学夹具，不代表真实图片推理；照片和确认人不上传。默认HTTP台账仅监听127.0.0.1，正式系统需自行实现账号和TLS。

数据作者：Çağlar Fırat Özgenel，Concrete Crack Images for Classification v2（2019），DOI [10.17632/5y9wdsg2zt.2](https://doi.org/10.17632/5y9wdsg2zt.2)，[原始数据](https://data.mendeley.com/datasets/5y9wdsg2zt/2)。仅抽样，原图片像素未修改；联系图为本包排版衍生物。
