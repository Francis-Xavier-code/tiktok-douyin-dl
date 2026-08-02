# 发布 macOS App 到 Homebrew（免 Apple 签名方案）

> 本方案**不需要 Apple Developer Program（$99/年）**，用免费的 ad-hoc 签名 + 自建 tap 发布，
> 用户 `brew install --cask` 后首启**不会**被 Gatekeeper 拦截。

## 方案对比

| 方案 | 费用 | 用户首启体验 | 发布渠道 |
|---|---|---|---|
| **ad-hoc 签名 + 自建 tap（本方案）** | 免费 | 无弹窗（cask 自动清 quarantine） | 自己的 tap 仓库 |
| Developer ID 签名 + 公证 | $99/年 | 无弹窗 | 官方 homebrew-cask |

**官方 homebrew-cask 不接受未签名 App**（审核要求 Developer ID 签名 + 公证），
所以免签名方案只能走自建 tap。想要 `brew install --cask tiktok-douyin-dl` 直接命中官方仓库，
必须配 `APPLE_SIGNING_IDENTITY` 等环境变量（见第 6 节），脚本已支持随时切换。

## 原理（实测结论）

1. 新版 Homebrew（6.x）安装 cask 时**强制**给 App 打 `com.apple.quarantine` 属性，
   且已移除 `--no-quarantine` 参数，无法在 cask 里直接关闭。
2. Gatekeeper 只拦截**带 quarantine 属性**的文件；未签名 / ad-hoc 签名都会被 `spctl` 判为 `rejected`，
   但只要没有 quarantine 属性，首次打开就不会弹「无法验证开发者」。
3. 因此方案 = **ad-hoc 签名**（免费，且 Apple Silicon 上所有 arm64 代码必须有签名，否则直接跑不起来）
   + **cask 的 `postflight` 在安装后清除 quarantine 属性** → 用户首启零弹窗。
4. 已实测验证：安装后 `xattr` 只剩无害的 `com.apple.provenance`，`com.apple.quarantine` 已被清除。

## 1. 构建（无需任何证书/环境变量）

```bash
./scripts/build-apple.sh macos
# 产物: dist/apple/macos/MediaDownloader-macOS-1.7.0-unsigned.dmg
# 自动完成 ad-hoc 签名（免费），App 可正常安装运行
```

## 2. 发布到 GitHub Releases

```bash
./scripts/release.sh
```

> 只想发布 macOS DMG（Linux/Windows 已由 CI 发布）可跳过 Linux 构建：
> `SKIP_LINUX=1 ./scripts/release.sh`

`release.sh` 会自动：

1. 构建 Linux CLI + macOS DMG（ad-hoc 签名）
2. 生成 `Casks/tiktok-douyin-dl.rb`：填入真实 version/sha256，带 `postflight` 清除 quarantine，并提交
3. 打 tag、推送（触发 CI 追加 Windows/Linux 产物）、把 DMG 上传到 GitHub Release

## 3. 自建 tap（让用户能 `brew install --cask`）

1. 在 GitHub 新建仓库，名字必须是 **`homebrew-` 开头**，例如 `homebrew-tap`
2. 把 `Casks/tiktok-douyin-dl.rb` 放进该仓库根目录的 `Casks/` 目录并推送
3. 用户安装：

```bash
brew tap Francis-Xavier-code/tap
brew install --cask tiktok-douyin-dl
```

本地测试 cask（无需先推 tap）：

```bash
brew install --cask ./Casks/tiktok-douyin-dl.rb   # 注意：需先放到一个 tap 里
# 或建临时 tap: brew tap-new <you>/<name> && cp Casks/*.rb <tap路径>/Casks/
```

## 4. 常见问题

| 现象 | 原因 / 解决 |
|---|---|
| 用户首启仍提示「无法验证开发者」 | 多为用户**直接下载 DMG** 而非通过 brew 安装（brew 会清 quarantine）。让用户右键 → 打开，或系统设置 → 隐私与安全性 → 仍要打开 |
| `spctl -a` 报 `rejected` | **正常**。未签名 App 的预期状态；只要无 quarantine 属性就不会拦截首启 |
| 为什么要 ad-hoc 签名 | Apple Silicon 上所有代码必须有签名才能运行；ad-hoc 免费，且避免「App 已损坏」类报错 |
| 每次发版要手改 cask？ | 不需要，`./scripts/release.sh` 自动更新 version 和 sha256 |
| 想换成官方签名发布 | 见第 6 节，配好环境变量重跑 `release.sh` 即可自动切成标准 cask |

## 5. 以后想上官方 homebrew-cask（可选，需要 $99）

1. 注册 Apple Developer Program，创建 **Developer ID Application** 证书
2. 在 [appleid.apple.com](https://appleid.apple.com) 生成 **App 专用密码**
3. 配置环境变量后重新发布：

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export APPLE_ID="you@example.com"
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export APPLE_TEAM_ID="TEAMID"
./scripts/release.sh
```

4. 产物变为 `MediaDownloader-macOS-1.7.0.dmg`（已签名 + 公证 + staple），
   `release.sh` 会自动把 cask 重写为**标准版**（无 postflight 清理，Gatekeeper 直接信任）
5. Fork [Homebrew/homebrew-cask](https://github.com/Homebrew/homebrew-cask)，把生成的 cask 放进 `Casks/`，
   `brew audit --cask --new tiktok-douyin-dl` 通过后提交 PR
