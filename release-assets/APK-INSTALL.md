# MiniCPM-V 巡检实践版 Android 安装说明

本章作者基于固定MiniCPM-V-Apps工程和v23原创巡检模块构建。安装包保留原MainActivity主入口、聊天/图片/视频入口、模型管理与下载、语音页面；巡检通过内部入口进入，不能代替原首页。

安装文件：[MiniCPM-V-demo-Android-v2.5.apk](https://modelscope.cn/datasets/pzc163/minicpm-v-inspection-part5/resolve/master/MiniCPM-V-demo-Android-v2.5.apk?view=false)。SHA256：`6615b7de73245a2dde9f45dae12da46298fe46bc97022a24329213afedba1283`，21137824字节。版本名2.5，versionCode23；包名`com.example.minicpm_v_demo.practice`，桌面标签“MiniCPM-V 巡检实践版”。独立包名用于与原官方App和此前.inspection验证版共存；已有验证版照片和记录保留在原包中，没有自动迁移到新包。

构建：Release、debuggable=false、唯一MainActivity Launcher，arm64-v8a、minSdk24（Android7+）、targetSdk36。实际支持情况以附带设备验收报告为准，未逐机型验收。4.6语言与视觉权重合计约1.53GiB，不包含在APK中；建议使用Wi-Fi、足够存储与内存的设备。

## 安装与首次下载

1. 下载APK，核对SHA256与附带签名证书摘要。通过手机文件管理打开，按系统提示允许当前文件管理器安装该包。
2. 启动“MiniCPM-V 巡检实践版”，从原主页的模型管理/下载入口选择MiniCPM-V4.6，下载语言GGUF与mmproj视觉组件。后台下载通知按系统权限设置显示。
3. 等待两份文件下载与校验完成，再加载模型。只有语言模型可用不等于图像推理已就绪。
4. 在原聊天页测试文字或图片；通过“巡检助手 · 拍照记录”进入巡检。拍摄或选择有权使用的照片，填写位置、核对对象与可见现象、填写确认人，主动确认后仅保存在手机。
5. 没有网络时使用已下载模型生成并保存。台账同步须主动点击；默认127.0.0.1:8787用于教学，可按ANDROID.md启动电脑本地服务并配置ADB回环映射。其它服务使用HTTPS及适当业务鉴权。

## 签名与更新

本作者发布的实践版使用固定专用RSA3072密钥，APK v2/v3签名验证通过。签名证书SHA256：`3eddc4d89ab27dc97302e839da128905e71779c276cd34c79e2aded29e230791`。证书供验证，私钥和口令仅在作者本机保留，不上传。

后续实践版更新必须保持此包名和签名、递增versionCode，才能保留新包中的照片和记录。重新用自己的密钥编译会生成不同签名，不能直接覆盖作者的已安装包。

## 本次验收

荣耀Magic9 Pro Max（Android17/API37、arm64、4KiB页）完成新包首次安装、App内实际下载两份权重及SHA256核对、原文字/图片聊天、巡检离线生成、人工核对、本地保存、同步失败保留、显式同步和状态刷新。同签名同版本覆盖更新后模型、照片草稿和正式记录保留。7项契约/SQLite和3项预处理设备测试通过。

本次公开图生成两次：首次非法JSON被拦截，第二次通过；宽泛英文对象仍需人工修改。不是一次生成必然成功的承诺，也不是语义准确率测量。详见APK-VALIDATION.md与源码包内acceptance-report.json。语音合成、完整视频处理、自然低质量现场和其它机型未全面验收。

## 从源码构建

下载并解压part5-apk-v23-source.zip，在part5-apk-source目录操作。它是原创模块、增量补丁和构建脚本，不是上游完整Android工程。公开源文件与补丁配合固定上游工程使用：先克隆MiniCPM-V-Apps并checkout `d1aac05eecaac64b7fc35f1cc93a06b726ce10e3`，初始化原生子模块 `13401aa8480d68a725e131cc4dbe5eda1f996a7f`，按官方说明准备SDK36.1/Build Tools36.0.0、NDK27.0.12077973、CMake4.1.2与Java17。

```bash
python examples/build_part5_release_apk.py --upstream vendor/MiniCPM-V-Apps --sdk /你的/Android/sdk --java /你的/JDK --key-dir /仅本机保留的/签名目录
```

第一次运行生成专用密钥，后续重复使用同一目录。自行妥善备份该目录及口令；不要加入公开源码包。原创代码MIT，上游代码、依赖与模型遵循各自许可，APK整体不以数据集CC BY4.0或原创代码MIT重新授权。

严格结构合格不等于观察准确。模型原始失败与语义问题保留；自然低质量场景及独立语义评审仍待验收。GPU v2短提示与Android v23长提示不同，不作为同提示量化比较。
