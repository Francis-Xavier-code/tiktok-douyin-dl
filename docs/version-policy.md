# 版本策略文件（version-policy.json）

用于在**不重新编译/重新发布各端安装包**的前提下，远程控制"哪些旧版本应被提示升级甚至拒绝运行"。

## 设计约束

- 这是一个**纯客户端**项目（直接爬 TikTok/抖音，无后端）。
- 已经发布出去且不含本机制的旧版本**无法被远程杀掉**——本机制只对"包含版本检查的未来构建"生效。
- 加载策略失败时一律**放行**（fail-open），绝不影响正常使用。
- 拉取带镜像/CDN 兜底与短超时；网络不可达只会被忽略。
- **本地缓存**：每次成功拉取都会把策略持久化到 `~/.cache/tiktok-douyin-dl/version-policy.json`（Windows 为 `%LOCALAPPDATA%/tiktok-douyin-dl/version-policy.json`，iOS/macOS 为 caches 目录）。**离线时**若本地已有缓存，则沿用缓存评估——这样设置 `hard_block: true` 的旧版在断网状态下仍会被挡住。仅当「从未成功拉取过任何策略」时才放行（首次离线不误杀）。

## 字段说明

```jsonc
{
  // --- 顶层字段 ---
  "schema": 1,
  // 策略文件格式版本号。当前固定为 1，未来如果格式不兼容可递增；
  // 旧客户端遇到不认识的 schema 版本会忽略整个文件（fail-open → 放行）。

  "updated_at": "2026-08-04T08:51:58Z",
  // 最后一次修改本文件的 UTC 时间戳。由 scripts/release.sh 自动刷新，
  // 也可手动更新。纯记录用途，客户端不依赖此字段做逻辑判断。

  "message": "当前版本仍可正常使用。如有升级提示，建议前往更新以获得最新修复。",
  // 当客户端版本低于 min_version 时展示给用户的提示文案。
  // 可说明弃用原因、新版本亮点等。留空则客户端使用内置默认文案。
  // 所有平台共享同一条 message（不支持 per-platform 覆盖）。

  "update_url": "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/latest",
  // 提示用户升级时的目标链接。客户端会尝试用浏览器打开此 URL。
  // 留空则使用内置默认的 releases/latest 链接。

  // --- platforms 对象：按平台分别配置 ---
  "platforms": {
    // 平台键：cli / windows / macos / ios。
    // 每个平台独立配置，未列出的平台不受版本策略约束（视为放行）。

    "cli": {
      "min_version": "1.8.0",
      // 低于此版本的客户端视为过期。
      // 语义化版本格式（如 "1.7.0"），逐段数值比较。
      // 设为 "0.0.0" 则所有版本均通过。

      "hard_block": false
      // true  → 硬阻挡：低于 min_version 直接拒绝运行，展示 message + update_url
      // false → 软提示：横幅/弹窗提醒升级，但旧版本仍可正常使用
    },

    "windows": {
      "min_version": "1.8.0",
      "hard_block": false
    },

    "macos": {
      "min_version": "1.8.0",
      "hard_block": false
    },

    "ios": {
      "min_version": "1.8.0",
      "hard_block": false
    }
  }
}
```

## 分级处置

| hard_block | 行为 |
|---|---|
| `false` | **软提示**（NAG）：横幅/弹窗提醒升级，但旧版本仍可使用 |
| `true`  | **硬阻挡**（BLOCK）：低于 `min_version` 直接拒绝运行，仅显示升级提示与链接 |

## 判定流程（客户端启动时）

1. 依次尝试拉取策略文件（直连 → 镜像）。
2. 若所有源均失败，检查本地缓存：
   - 有缓存 → 使用缓存评估（离线硬阻断仍生效）。
   - 无缓存（首次启动从未成功拉取）→ **放行**（fail-open）。
3. 查找 `platforms` 中当前平台的条目：
   - 无条目 → **放行**。
   - 有条目 → 比较当前版本与 `min_version`。
4. 当前版本 >= `min_version` → **放行**。
5. 当前版本 < `min_version`：
   - `hard_block: false` → **软提示**（NAG），继续运行。
   - `hard_block: true` → **硬阻挡**（BLOCK），退出程序。

## 如何停用某个旧版本

1. 编辑本文件：把对应平台的 `min_version` 提高到要保留的最低版本；若该版本有严重安全问题，设 `hard_block: true`。
2. 更新 `updated_at`。
3. 提交到仓库默认分支（main），并随下一次 release 作为产物上传（见 `scripts/release.sh`）。

各端启动时会从以下地址拉取（按顺序兜底）：

- `https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json`
- `https://gh-proxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json`
- `https://ghproxy.net/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json`

## 何处生效

| 端 | 实现文件 | 调用点 |
|---|---|---|
| CLI / Linux | `python/src/media_downloader/core/version_policy.py` | `douyin.main()` / `tiktok.main()` 入口 |
| Windows GUI | `apps/windows/gui/auto_updater.py` | 启动时调用 |
| iOS | `apps/ios/MediaDownloader/Services/VersionPolicyService.swift` | `MediaDownloaderApp.swift` `.task` 启动时 |
| macOS 菜单栏 | `apps/macos/MediaDownloader/VersionPolicyService.swift` | `DownloadController.refreshPolicy()` 启动时 |
