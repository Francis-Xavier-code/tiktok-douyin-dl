# 维护指南（MAINTENANCE）

> 这份文档写给**项目维护者**和**后续接手的 AI**。动手改任何一个端之前，先读这一份。
> 本仓库是"一个核心、六个客户端"的联动项目，最常踩的坑不是代码写错，而是**改了一端、忘了另一端的版本号 / 更新日志 / 远程策略联动**。
>
> 相关文档：`docs/architecture.md`（架构）、`docs/version-policy.md`、`docs/download-policy.md`、`AGENTS.md`（仓库总览）。

---

## 1. 客户端全景

| 客户端 | 代码位置 | 技术栈 | 打包 / 产物 | 版本号来源 | 更新检查入口 |
|---|---|---|---|---|---|
| **CLI**（Windows/Linux/macOS） | `python/src/media_downloader/` | Python，PyInstaller 单文件 | `MediaDownloader-Windows-x64-CLI-<v>.zip`、`MediaDownloader-Linux-x86_64-<v>.tar.gz`、`MediaDownloader-macOS-arm64-CLI-<v>.zip` | `core/updater.py VERSION`（sync） | 启动时 `cli.py` → `check_for_updates(silent=True)`；`douyin`/`tiktok` 入口另走交互模式 |
| **Windows GUI** | `apps/windows/gui/`（tkinter + sv-ttk），安装包 `apps/windows/installer/` | Python + Inno Setup | `MediaDownloader-Windows-x64-Setup-<v>.exe` | `gui/auto_updater.py CURRENT_VERSION`（sync） | 启动/手动「检查更新」，读 changelog.json 镜像 |
| **macOS app** | `apps/macos/`（SwiftUI）+ `apple/MediaDownloaderCore` | Swift / SPM | `MediaDownloader-macOS-<v>-unsigned.dmg` | `AppUpdateService.swift` Bundle fallback（sync）+ Xcode `MARKETING_VERSION` | `AppUpdateService.swift`，主窗口/菜单栏「检查更新」 |
| **iOS app** | `apps/ios/`（SwiftUI）+ 同一 `apple/` 库 | Swift / SPM | `MediaDownloader-iOS-<v>-unsigned.ipa` | `SettingsView.swift` fallback（sync）+ Xcode `MARKETING_VERSION` | `AppUpdateService.swift`，启动时检查 |
| **Android** | `apps/android/`（Kotlin + Gradle） | Kotlin | `douyin-download-Android-<v>.apk`（debug 变体） | `build.gradle.kts versionName/versionCode`（sync）——**独立版本线** | 启动时自动检查更新 |
| **WebUI** | `apps/web/webui.py`（单文件 Gradio） | Python | 不打包、不上 Release，直接 `python webui.py` 跑 | 跟随 python 包 | 无独立更新逻辑 |

联动关系：

- `python/` 是逻辑核心，CLI / Windows GUI / WebUI 共用；改 `python/` 会影响这三个。
- `apple/` 是 iOS + macOS 共享的 Swift 库；改它**两端都要回归**。
- 所有端的更新日志来自同一个 `changelog.json`（根目录），按平台标签过滤。

---

## 2. 版本号体系（version.json 是唯一事实来源）

`version.json`（仓库根目录）只有这一个入口，改版本**只允许改这里**：

```json
{
  "main": "2.0.0",                          // CLI / Windows / macOS / iOS 共享
  "android": { "versionName": "2.0.0", "versionCode": 4 },  // Android 独立线
  "apple": { "buildNumber": 1 }             // APPLE_BUILD_NUMBER（CI 硬编码为 1）
}
```

改完运行 `python3 scripts/sync-versions.py`，自动同步到 **12 处硬编码位置**：

1. `python/src/media_downloader/__init__.py` → `__version__`
2. `python/pyproject.toml` → `version`
3. `python/src/media_downloader/core/updater.py` → `VERSION`（**CLI 检测更新靠它**）
4. `apps/windows/gui/auto_updater.py` → `CURRENT_VERSION`
5. `install.sh` → `RELEASE_TAG`
6. `install.ps1` → `RELEASE_TAG`
7. `Casks/tiktok-douyin-dl.rb` → `version`
8. `apps/macos/MediaDownloader.xcodeproj/project.pbxproj` → `MARKETING_VERSION`（Debug + Release）
9. `apps/ios/MediaDownloader.xcodeproj/project.pbxproj` → `MARKETING_VERSION`
10. `apps/macos/MediaDownloader/AppUpdateService.swift` → Bundle fallback
11. `apps/ios/MediaDownloader/Views/SettingsView.swift` → Bundle fallback
12. `apps/android/app/build.gradle.kts` → `versionName` + `versionCode`

注意：

- **Android 独立版本线**：`versionName/versionCode` 可以单独升、也可以长期不动，不影响 main 线。
- **apple.buildNumber**：只在本地 Xcode 构建时用；CI 的 `release.yml` 里硬编码 `APPLE_BUILD_NUMBER=1`，所以不用为每次发版去 bump 它。
- 如果 `sync-versions.py` 报"某文件找不到"，说明有人重构了对应位置——**不要绕过，去修脚本**。

### 判断当前版本状态（给 AI 的快速命令）

```bash
git tag -l "v*" | sort -V | tail -3          # 线上已发布的版本
python3 -c "import json;print(json.load(open('version.json'))['main'])"   # 代码里要发的版本
python3 -c "import json;print(json.load(open('changelog.json'))['versions'][0]['version'])"  # 更新日志最新条目
git log --oneline -5                          # 最近提交
```

- `version.json` 的 main **高于**最新 tag → 处于「攒更新」状态（见 §4）。
- 两者相等且 tag 已 push → 已发布，工作区应干净。

---

## 3. 更新日志体系（CHANGELOG.md → changelog.json）

- **单一事实来源是 `CHANGELOG.md`**；`changelog.json` 由 `scripts/update-changelog-json.py` 自动生成（最多保留 10 个版本，`## [Unreleased]` 段落会被跳过）。
- 客户端（CLI/Windows/macOS/iOS/Android）通过 4 个镜像拉取 changelog.json：
  `raw.githubusercontent.com` → `gh-proxy.com` → `ghproxy.net` → `jsdelivr`，按平台过滤后显示。
- **条目标签约定**（必须写对，写错会进错桶）：

| 标签 | 平台 key | 客户端 |
|---|---|---|
| `**[全平台]**` | `all` | 所有端 |
| `**[CLI]**`（别名 `Linux`） | `cli` | CLI |
| `**[Windows]**` | `windows` | Windows GUI |
| `**[macOS]**`（别名 `Mac`） | `macos` | macOS app |
| `**[iOS]**` | `ios` | iOS app |
| `**[Android]**` | `android` | Android |

- 没写标签的条目默认进 `all`；多行 bullet 会折叠成一条。
- **任何增删条目后都要重新生成**：`python3 scripts/update-changelog-json.py`，否则客户端拉到的还是旧内容。

---

## 4. 攒更新工作流（日常开发，今天这种）

这个项目"多个客户端、改动零散"，不适合改一点发一版。约定做法是**攒够一个版本再发布**：

### 步骤

1. **改代码** → 跑测试（`cd python && uv run pytest`，61 个用例，无网络无浏览器）。
2. **加 CHANGELOG 条目**：写进当前攒的版本 section（如 `## [2.1.0]`），标签写对该端。
3. **版本号**：
   - 若还没为这批改动 bump 过 → 改 `version.json` 的 `main` 到下个版本 → `python3 scripts/sync-versions.py`。
   - 若已经 bump 过（版本 section 已存在）→ 跳过。
4. **重新生成** `changelog.json`。
5. **本地 commit，不 push、不打 tag**。
6. 攒够后走 §5 发版。

### 关键约定

- **`version-policy.json` 的 `min_version` 保持已发布版本不变**（比如现在线上是 2.0.0，那么攒 2.1.0 期间它一直是 `2.0.0`），等真正要强制升级旧版时再用 `--policies` 升。`release.sh` 只会刷 `updated_at`，不会动 `min_version`。
- 攒更新期间，各端「检查更新」看到的"最新版本"来自 changelog.json——所以只要 `changelog.json` 已经含 2.1.0，**已发布版用户就会看到 2.1.0 的更新提示**。想低调攒着不惊动用户，就先**不要**把 2.1.0 条目写进 `CHANGELOG.md`/生成 `changelog.json`，攒够再一次性加。
- 当前状态（2026-08-08）：最新发布 `v2.0.0`；全仓版本统一 `2.0.0`（曾 bump 的 2.0.1 已全部回滚、从未发布）；`v2.1.0` 计划攒在 `plan.md`（未 bump 版本、未写 CHANGELOG）。

---

## 5. 发版流程（release.sh）

前置条件：`gh` CLI 已装、工作区干净、`version.json` 已是目标版本、`docs/releases/v<版本>.md` 已创建（见下）。

```bash
./scripts/release.sh            # 正常发布
SKIP_POLICY_BUMP=1 ./scripts/release.sh   # 小版本不想刷新策略 updated_at 时
```

`release.sh` 自动做：

1. 读 `version.json` 的 main，校验 tag 不存在、工作区干净。
2. 跑 `sync-versions.py` 同步全部版本常量并 commit（`release: sync version constants to <v>`）。
3. bump `version-policy.json` / `download-policy.json` 的 `updated_at` 并分别 commit。
4. 重新生成 `changelog.json` 并 commit。
5. push main → 打 `v<版本>` tag → push tag → CI（`.github/workflows/release.yml`）开始全平台构建。

CI 产出的 Release 资产（命名必须记住，别改错）：

| 平台 | 资产 |
|---|---|
| Windows | `MediaDownloader-Windows-x64-Setup-<v>.exe`、`MediaDownloader-Windows-x64-CLI-<v>.zip` |
| Linux | `MediaDownloader-Linux-x86_64-<v>.tar.gz` |
| macOS CLI | `MediaDownloader-macOS-arm64-CLI-<v>.zip` |
| macOS app | `MediaDownloader-macOS-<v>-unsigned.dmg` |
| iOS | `MediaDownloader-iOS-<v>-unsigned.ipa` |
| Android | `douyin-download-Android-<v>.apk` |

### 发版必做但脚本不自动做的事

- **创建 `docs/releases/v<版本>.md`**（发布说明）。CI 用这个文件当 Release notes；**如果缺失，会静默 fallback 到 `v1.7.0.md`**——发布说明就全错了。参照 `docs/releases/v2.0.0.md` 的模板写。
- **核对 cask sha256**：CI 会自动更新 `Casks/tiktok-douyin-dl.rb` 的 sha256 并 push 回 main，发完去确认一下。
- **确认 Release 资产齐全**（6 类产物都在）。
- 若本次要**强制旧版升级**：发版前跑 `python3 scripts/sync-versions.py --policies`（把 `min_version` 同步成新版本），再发。

---

## 6. 远程策略维护（两个 JSON，语义相反，别记反）

| 文件 | 语义 | 不可达时 | 用途 |
|---|---|---|---|
| `version-policy.json` | **fail-open** | 放行，不打扰用户 | 版本提示/硬阻挡：低于 `min_version` 且 `hard_block: true` 的旧版被拦住 |
| `download-policy.json` | **fail-closed** | 阻止下载 | 远程开关下载功能（`download.enabled`），支持 `platforms.android` 等 per-platform 覆盖 |

维护规则：

- 平时**只动** `updated_at`（release.sh 自动刷）。`message` 是给用户看的文案，可改。
- 想强制升级旧版时：`version.json` bump 后跑 `python3 scripts/sync-versions.py --policies`，会把 `platforms.*.min_version`（cli/windows/macos/ios + android）同步成新版本，然后照常发版。
- `download-policy.json` 的全局 `min_version` 是 1.7.0（历史遗留），per-platform 的 android 是 2.0.0——`--policies` 只同步 android 的 per-platform 字段，全局字段保持不动。
- 有 `scripts/toggle-download.sh` 可快速开/关下载策略。

### 紧急停服流程（收到律师函 / 平台投诉 / 账号警告时）

**目标**：几分钟内让所有客户端停止下载，避免法律风险扩大。核心是改一个 JSON 推送到 main，客户端下次启动即生效。

**1. 一键关闭下载**（本地执行）：

```bash
./scripts/toggle-download.sh off "根据相关法律法规要求，下载功能已暂停。如有问题请联系项目作者。"
```

该脚本自动更新 `download-policy.json` 的 `enabled=false` + `message` + `updated_at`；若 `secrets/policy-private-key.pem` 存在还会重新 Ed25519 签名（Android 验签必需，没签名时 Android 会因验签失败而拦截，属于安全默认）。

**2. 推送生效**：

```bash
git add download-policy.json && git commit -m "policy: 紧急停服（下载功能暂停）" && git push origin main
```

**3. 生效机制（无需用户升级）**：
- 各端（CLI / Windows / macOS / iOS / Android）在启动/检查时**网络优先**拉取策略；`download-policy` 是 **fail-closed**——即使所有镜像都不可达，客户端默认也阻止下载，安全兜底。
- Android 额外要求 Ed25519 验签，验签失败同样拦截（更严格）。
- 已在线用户在下一次策略检查后生效；理论上最长不超过一次启动周期。

**4. 验证**（可选）：

```bash
curl -s https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json
# 确认 "enabled": false 且 message 正确
```

**5. 可选：强制旧版升级**：若只想拦旧版本（而非全停），bump `version.json` 后 `python3 scripts/sync-versions.py --policies` 同步 `min_version` + `hard_block: true`（`version-policy.json` 已默认全部 hard_block），按正常流程发版。

**6. 恢复下载**：

```bash
./scripts/toggle-download.sh on "下载功能已恢复。"
# git add download-policy.json && git commit && git push origin main
```

---

## 7. 测试与质量门禁

- `cd python && uv run pytest`（本机是 `.venv/bin/python -m pytest`）——**61 个纯单元测试**：无网络、无浏览器、无外部服务。
- 解析器 fixture 放 `python/tests/fixtures/`，**必须脱敏**（不含 cookie / 私人数据）。
- Playwright 浏览器只在实际下载时用，测试不触发。
- 改 `apple/` 共享库后，iOS 和 macOS 两个 Xcode 工程都要能编译（本机无 Xcode 时至少保证语法/API 一致）。

---

## 8. 各端改动 Checklist（给 AI）

### 通用（改任何端都查一遍）

- [ ] `cd python && uv run pytest` 全绿
- [ ] 涉及版本 → 只改 `version.json` 后跑 `sync-versions.py`（不要手改那 11 处）
- [ ] 涉及用户可见变更 → `CHANGELOG.md` 加条目，标签写对该端，然后重新生成 `changelog.json`
- [ ] 涉及强制升级 → 追加 `--policies` 同步 `min_version`
- [ ] 涉及文档（architecture / version-policy / download-policy / 本文件）→ 同步更新

### 按端

- **改 CLI 核心（`python/`）**：影响 CLI + Windows GUI + WebUI 三端。检查 `cli.py` 入口、`platforms/{douyin,tiktok}.py`、i18n（`i18n/catalogs.py` 有中英两套文案，新增文案必须两套都加）。
- **改共享 Swift 库（`apple/`）**：iOS + macOS 都要回归；两个 `project.pbxproj` 和两个 Swift fallback 版本号由 sync 覆盖。
- **改 Windows GUI（`apps/windows/`）**：`auto_updater.py` 版本号由 sync 覆盖；打包走 `build-windows.ps1`（PowerShell + Inno Setup）。
- **改 Android（`apps/android/`）**：独立版本线，`versionName/versionCode` 单独管理；打包 `./gradlew assembleDebug`。
- **改 WebUI（`apps/web/webui.py`）**：单文件，跟随 python 包，无独立发布。

---

## 9. 预发布 / 特殊场景

- **攒更新期 = 事实上的预发布**：版本号已 bump、改动已 commit，但未打 tag。用户端看不到（只要 changelog.json 没提前生成），代码可随时发布。
- **紧急 hotfix**：直接 bump patch（如 2.0.1 → 2.0.2），走同一条攒/发流程，不必等大版本。
- **真·pre-release（GitHub 上标 prerelease）**：CI 的 `release.yml` 创建的是正式 Release，项目目前**没有**预发布机制。如果需要，只能手动 `gh release edit <tag> --prerelease`，且要与 CI 自动创建/覆盖的流程协调（CI 用 `gh release create/edit`，可能覆盖手动标记）。
- **只想本地构建不发版**：用 `scripts/build-*.sh` / `build-windows.ps1` 直接构建，`version.json` 不 bump 即可。
