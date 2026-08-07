# Android 客户端（douyin-download）

抖音无水印视频与图文下载的 Android 客户端，与 iOS/macOS 端共享相同的下载策略与验签机制。

## 功能

- 解析抖音分享文本 / 分享链接（自动跟随 `v.douyin.com` 短链重定向）；
- 提取 RENDER_DATA / _ROUTER_DATA 页面 JSON，定位作品并构造无水印播放地址；
- **下载后直接在手机相册可见**：视频保存到「DCIM / douyin-download」，图文保存到「Pictures / douyin-download」，低版本系统自动触发媒体扫描；
- 支持从其他 App 分享抖音分享文本到本应用一键下载；
- **下载前强制校验远程策略**：`enabled: false`、签名无效、版本过低、所有源不可达，任一情形都拒绝下载（fail-closed + Ed25519 验签，见 `docs/download-policy.md`）。

## 项目结构

```
apps/android/
├── settings.gradle.kts / build.gradle.kts / gradle.properties
└── app/
    ├── build.gradle.kts
    └── src/main/
        ├── AndroidManifest.xml
        ├── java/com/douyindownload/
        │   ├── MainActivity.kt          # 主界面与下载编排
        │   ├── DownloadPolicyService.kt # 远程策略拉取 + 评估（fail-closed）
        │   ├── PolicyVerifier.kt        # Ed25519 验签（BouncyCastle）
        │   ├── DouyinParser.kt          # 页面解析 + 无水印 URL 构造
        │   └── MediaSaver.kt            # 下载并保存到 MediaStore
        └── res/                         # 布局 / 主题 / 图标
```

## 构建

要求：JDK 17+、Android SDK（API 34）。

```bash
# Android Studio：File → Open → 选择 apps/android 目录，同步后 Run。

# 或命令行：
cd apps/android
gradle assembleDebug        # 产物：app/build/outputs/apk/debug/app-debug.apk
```

### 远程构建（Gitee CI）

推送 `apps/android/**` 改动到 master，或手动运行 `.gitee/workflows/build-android.yml`，
CI 会自动安装 JDK 17 / Android SDK 34 / Gradle 并构建 APK，产物在 Actions 页面的
`android-apk` Artifact 中下载（无需本机配置 Android 环境）。

## 发布

打包 release APK 后，在 `docs/releases/<tag>.md` 对应版本说明中补充 APK 下载链接。
