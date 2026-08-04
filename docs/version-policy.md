# 版本策略文件（version-policy.json）

用于在**不重新编译/重新发布各端安装包**的前提下，远程控制"哪些旧版本应被提示升级甚至拒绝运行"。

## 设计约束

- 这是一个**纯客户端**项目（直接爬 TikTok/抖音，无后端）。
- 已经发布出去且不含本机制的旧版本**无法被远程杀掉**——本机制只对"包含版本检查的未来构建"生效。
- 加载策略失败时一律**放行**（fail-open），绝不影响正常使用。
- 拉取带镜像/CDN 兜底与短超时；网络不可达只会被忽略。
- **本地缓存**：每次成功拉取都会把策略持久化到 `~/.cache/tiktok-douyin-dl/version-policy.json`（Windows 为 `%LOCALAPPDATA%/tiktok-douyin-dl/version-policy.json`，iOS/macOS 为 caches 目录）。**离线时**若本地已有缓存，则沿用缓存评估——这样设置 `hard_block: true` 的旧版在断网状态下仍会被挡住。仅当「从未成功拉取过任何策略」时才放行（首次离线不误杀）。

## 字段说明

```json
{
  "schema": 1,                       // 策略文件格式版本，客户端不兼容时忽略
  "updated_at": "2026-08-04T00:00:00Z",
  "message": "升级提示文案 / 弃用说明",
  "update_url": "https://github.com/.../releases/latest",
  "platforms": {
    "<platform>": {
      "min_version": "1.6.0",        // 低于此版本视为过期
      "hard_block": false            // true=硬阻挡(拒绝运行)，false=软提示(仍可用)
    }
  }
}
```

平台键：`cli` / `windows` / `macos` / `ios`。

## 分级处置

| hard_block | 行为 |
|---|---|
| `false` | **软提示**：横幅/弹窗提醒升级，但旧版本仍可使用 |
| `true`  | **硬阻挡**：低于 `min_version` 直接拒绝运行，仅显示升级提示与链接 |

## 如何停用某个旧版本

1. 编辑本文件：把对应平台的 `min_version` 提高到要保留的最低版本；若该版本有严重安全问题，设 `hard_block: true`。
2. 更新 `updated_at`。
3. 提交到仓库默认分支（main），并随下一次 release 作为产物上传（见 `scripts/release.sh`）。

各端启动时会从以下地址拉取（按顺序兜底）：

- `https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json`
- `https://gh-proxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json`
- `https://ghproxy.net/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json`

## 何处生效

| 端 | 实现 |
|---|---|
| CLI / macOS / Linux | `python/src/media_downloader/core/version_policy.py` |
| Windows GUI | `apps/windows/gui/auto_updater.py` 的 `enforce_version_policy` |
| iOS | `apps/ios/MediaDownloader/Services/VersionPolicyService.swift` |
| macOS 菜单栏 | `apps/macos/MediaDownloader/VersionPolicyService.swift` + `DownloadController` |
