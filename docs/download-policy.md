# 下载功能策略文件（download-policy.json）

用于控制**下载功能本身是否可用**，与 `version-policy.json`（控制客户端版本是否过期）相互独立。

每次客户端执行一次下载前，都会依次从以下地址拉取本文件，只要有一个源成功就采用；**全部源都无法读取时，默认禁止下载**（fail-closed），并提示用户前往仓库提 issue。

## 源顺序（直连永远第一位）

1. `https://raw.githubusercontent.com/.../main/download-policy.json`（直连 GitHub）
2. 其余 9 个为国内镜像加速源，依次尝试（见各端实现中的 `DOWNLOAD_POLICY_SOURCES`）。
   直连不可用时自动顺延到下一个可用镜像；某个镜像超时/失败则跳过，不阻塞整体。

> 镜像域名是**可配置的**：把实测可用的加速域名加入列表即可，无需改逻辑。本仓库默认内置一组通用加速前缀（gh-proxy / ghproxy / jsDelivr 等），部分域名在当前网络环境下可能不通，属正常——它们只在直连失败时作为兜底。

## 字段说明

```json
{
  "schema": 1,
  "updated_at": "2026-08-04T00:00:00Z",
  "issue_url": "https://github.com/.../issues",
  "download": {
    "enabled": true,        // 全局下载总开关；false=禁止一切下载
    "message": "提示文案",
    "min_version": "0.0.0", // 低于此版本禁止下载（用于临时屏蔽有 bug 的版本）
    "platforms": {}         // 预留：未来可按 douyin/tiktok 分别设置
  }
}
```

## 拦截判定（每次下载前）

- `download.enabled == false` → 拦截，展示 `message`，并附 `issue_url`。
- 当前版本 `< download.min_version` → 拦截，提示升级。
- 所有源读取失败（直连 + 9 镜像全挂）→ **拦截**（fail-closed），提示去提 issue。
- 其余情况 → 放行。

## 如何临时关闭下载

编辑本文件：`"enabled": false` 并填好 `message`，提交到默认分支（main）并随 release 上传。下一次用户点下载时即生效。
