# 第三方材料

- 图片：Çağlar Fırat Özgenel，Concrete Crack Images for Classification v2，CC BY 4.0。归因与原文件路径见data目录。
- GPU模型：[OpenBMB/MiniCPM-V-4.6](https://modelscope.cn/models/OpenBMB/MiniCPM-V-4.6)，固定提交fd02313ad21ac485c595cb01231a3bded449cff5。模型从官方源另行下载；遵循该提交的模型卡与许可，不以本包MIT或数据许可重授权。
- Android上游：[OpenBMB/MiniCPM-V-Apps](https://github.com/OpenBMB/MiniCPM-V-Apps)，固定提交d1aac05eecaac64b7fc35f1cc93a06b726ce10e3；原生子模块固定13401aa8480d68a725e131cc4dbe5eda1f996a7f。GPU原复现ZIP未分发完整上游或APK；补充发布的实践版APK使用固定工程编译，保留上游权利与随附许可全文，不能将APK整体按原创组件MIT重新授权。当前固定Apps根目录未发现独立LICENSE，不能据此将上游当作MIT/Apache重授权。
- llama.cpp-omni中的MIT声明保留在上游，增量patch不改变原代码许可。
- Transformers、ModelScope、PyTorch、torchvision及其它依赖从官方软件包源另行安装，各自许可保留。
- 本包原创Python/Kotlin组件与新增复现说明采用MIT。patch仅新增部分适用此授权，上下文中的上游代码保留原权利。上游工程不因本包许可发生变更。
