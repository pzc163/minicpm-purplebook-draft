# 将巡检加入原 MiniCPM-V App

Android部分对应已完成真机验收的v23模块：原首页、媒体输入、模型管理/下载均保留；巡检为内部Activity和独立模型进程。测试包名后缀.inspection，可与官方App共存。

```bash
git clone https://github.com/OpenBMB/MiniCPM-V-Apps.git vendor/MiniCPM-V-Apps
git -C vendor/MiniCPM-V-Apps checkout d1aac05eecaac64b7fc35f1cc93a06b726ce10e3
git -C vendor/MiniCPM-V-Apps submodule update --init --recursive
python examples/integrate_inspection_android.py --upstream vendor/MiniCPM-V-Apps
```

核对子模块HEAD为13401aa8480d68a725e131cc4dbe5eda1f996a7f。在Android Studio打开上游MiniCPM-V-demo-Android目录，按官方README配置本地SDK，不复制作者local.properties或签名文件。实测使用SDK36.1、Build Tools36.0.0、NDK27.0.12077973、CMake4.1.2、Gradle9.3.1、AGP9.1.1和Java17。

在该Android工程目录执行 `./gradlew :app:assembleDebug :app:assembleDebugAndroidTest`。自行在测试机安装生成的Debug APK；覆盖升级必须保持同包名、同签名，异签名卸载会丢失私有数据。下载入口在原主界面模型管理，选择4.6并准备语言GGUF和mmproj视觉文件；巡检页可跳转原下载入口。

手机相机/相册照片压缩、方向修正后在本地推理。object/visible_issue必须人工核对，填写位置与确认人后才能本地保存。同步是显式操作。电脑启动 `python examples/ledger.py` 后可用ADB回环映射做教学测试：`adb reverse tcp:8787 tcp:8787`，完成后 `adb reverse --remove tcp:8787`。

严格契约与记录存储测试源码为InspectionContractInstrumentedTest。InspectionVisionInstrumentedTest、InspectionBenchmarkInstrumentedTest和InspectionImageInstrumentedTest用于模型、20图和预处理验证，需要对应模型/数据准备。不要把构建成功计作设备测试通过。旧v20的全面预处理3项实测与20图性能是历史证据；固定签名v23 Release已在荣耀真机补跑相同预处理组件的三项测试并全部通过。

Android v23提示SHA256：5cb203d55db7c862f7479ed64a7843c6beeef5a4cfb897ea1edbfa76efb5a4e1。本包GPU v2短提示SHA256：0c3fed70240a1639d25d0f6057972c46f9d21abf0925ce1fd19e038d51040fdb。因此GPU和手机结果不能作纯量化或统一倍率比较。固定签名APK仍保留此v23提示；安装和Release构建见APK-INSTALL.md，详细实测范围见APK-VALIDATION.md。
