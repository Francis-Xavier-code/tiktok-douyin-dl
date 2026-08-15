# 下载功能策略文件（download-policy.json）

用于控制**下载功能本身是否可用**，与 `version-policy.json`（控制客户端版本是否过期）相互独立。

每次客户端执行下载前，都会依次从以下地址拉取本文件，只要有一个源成功就采用；**全部源都无法读取时，默认禁止下载**（fail-closed），并提示用户前往仓库提 issue。

> **Ed25519 签名（所有客户端强制）**：本文件必须携带由作者私钥生成的 `signature` 字段（见下），所有客户端（CLI / Windows GUI / WebUI / iOS / macOS / Android）在采纳策略前都会用内置公钥验签。**未签名、签名无效或内容被篡改的策略一律视为不可信（fail-closed）**，与网络不可达同等处理。修改本文件后必须重新签名：`python3 scripts/sign-policy.py download-policy.json`（`scripts/toggle-download.sh` 与 `scripts/release.sh` 会自动完成）。

## 源顺序（直连永远第一位）

1. `https://raw.githubusercontent.com/.../main/download-policy.json`（直连 GitHub）
2. 其余 9 个为国内镜像加速源，依次尝试（见各端实现中的 `_SOURCES` / `sources`）。
   直连不可用时自动顺延到下一个可用镜像；某个镜像超时/失败则跳过，不阻塞整体。

> 镜像域名是**可配置的**：把实测可用的加速域名加入列表即可，无需改逻辑。本仓库默认内置一组通用加速前缀（gh-proxy / ghproxy / jsDelivr 等），部分域名在当前网络环境下可能不通，属正常——它们只在直连失败时作为兜底。

## 字段说明

```jsonc
{
  // --- 顶层字段 ---
  "schema": 1,
  // 策略文件格式版本号。当前固定为 1，未来如果格式不兼容可递增；
  // 旧客户端遇到不认识的 schema 版本会忽略整个文件（fail-closed → 阻断下载）。

  "updated_at": "2026-08-04T08:51:58Z",
  // 最后一次修改本文件的 UTC 时间戳。由 scripts/release.sh 自动刷新，
  // 也可手动更新。纯记录用途，客户端不依赖此字段做逻辑判断。

  "issue_url": "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/issues",
  // 当下载被阻断时，展示给用户的反馈链接。客户端会尝试用浏览器打开此 URL。
  // 如果 platforms 下的条目也定义了 issue_url，条目级优先。

  "signature": "BASE64-ED25519-...",
  // Ed25519 签名（base64）。由 scripts/sign-policy.py 用 secrets/ 下的私钥生成，
  // 覆盖的规范化内容仅包含四个字段（顺序固定，各端实现必须一致）：
  //   updated_at
  //   enabled        // "true" / "false"
  //   message
  //   min_version
  // 其余字段（schema / issue_url / platforms 等）不参与签名，可自由增减。
  // 公钥内置于各端：core/policy_verifier.py / PolicyServices.swift / PolicyVerifier.kt
  // （三处必须保持一致）。验签失败或缺失 → 策略视为不可信，阻断下载。

  // --- download 对象：下载功能的核心控制 ---
  "download": {
    "enabled": true,
    // 全局下载总开关。
    //   true  → 正常放行（仍需通过 min_version 检查）
    //   false → 立即阻断所有下载，展示 message 作为原因

    "message": "下载功能已开放。",
    // 当下载被阻断（enabled=false 或版本过低）时展示给用户的提示文案。
    // 留空则客户端使用内置默认文案。
    // 可用于说明维护原因、预计恢复时间等。

    "min_version": "0.0.0",
    // 允许下载的最低客户端版本号（语义化版本，如 "1.7.0"）。
    // 当前版本 < min_version → 阻断下载，提示用户升级。
    // 设为 "0.0.0" 表示不限制版本。

    "platforms": {
      // 按平台粒度的覆盖配置（可选）。
      // 平台键："cli"、"windows"、"macos"、"ios"。
      // 如果某个平台在此有条目，则该平台使用条目中的值；
      // 未列出的平台回退到外层 download 的全局值。
      //
      // 示例：单独关闭 iOS 的下载
      // "ios": {
      //   "enabled": false,
      //   "min_version": "0.0.0",
      //   "message": "iOS 版本正在修复中，请稍后再试。"
      // }
      //
      // 示例：要求 Windows 至少 2.0.0 才能下载
      // "windows": {
      //   "enabled": true,
      //   "min_version": "2.0.0",
      //   "message": "请升级到 2.0.0 以上版本。"
      // }
      //
      // 条目内可选字段：
      //   enabled     - 覆盖全局开关（省略则继承全局值）
      //   min_version - 覆盖版本下限（省略则继承全局值）
      //   message     - 覆盖提示文案（省略则继承全局值）
    }
  }
}
```

## 拦截判定流程（每次下载前，按优先级）

1. 所有源（直连 + 9 镜像）均无法读取**验签通过**的 JSON → **拦截**（fail-closed），原因 `unreachable`。
2. `download` 字段缺失或非 dict → **拦截**（视为格式异常），原因 `unreachable`。
3. 若当前平台在 `download.platforms` 中有条目，使用条目值；否则回退到全局值。
4. `enabled == false` → **拦截**，原因 `disabled`，展示 `message`。
5. 当前版本 < `min_version` → **拦截**，原因 `version`，展示 `message`。
6. 以上均通过 → **放行**。

## 如何临时关闭下载

推荐方式：`./scripts/toggle-download.sh off "说明文案"`（会自动更新字段并重新 Ed25519 签名）。手动编辑本文件：`"enabled": false` 并填好 `message` 后，必须运行 `python3 scripts/sign-policy.py download-policy.json` 重新签名，再提交到默认分支（main）并随 release 上传——**未签名的策略会让所有客户端停止下载**。下一次用户点下载时即生效。

## 何处生效

| 端 | 实现文件 | 调用点 |
|---|---|---|
| CLI / Linux | `python/src/media_downloader/core/download_policy.py` | `douyin.download_urls()` / `tiktok.download_urls()` 入口（Ed25519 验签：`core/policy_verifier.py`） |
| Windows GUI | `apps/windows/gui/auto_updater.py` → `check_download_policy()` | `gui_downloader.py` 下载按钮回调（复用核心验签） |
| WebUI | `apps/web/webui.py` | `start_download()` 第一步（复用核心验签） |
| iOS | `apps/ios/MediaDownloader/Services/DownloadPolicyService.swift`（薄封装） | `DownloadStore.downloadDirectMedia()` 第一步（共享引擎 `PolicyServices.swift` 验签） |
| macOS 菜单栏 | `apps/macos/MediaDownloader/DownloadPolicyService.swift`（薄封装） | `DownloadController.startDownload()` Task 第一步（共享引擎 `PolicyServices.swift` 验签） |
| Android | `apps/android/app/src/main/java/com/douyindownload/DownloadPolicyService.kt` | `MainActivity` 下载前 `DownloadPolicyService.evaluate()`（`PolicyVerifier.kt` Ed25519 验签） |
