import AppKit
import Foundation
import Observation

@MainActor
@Observable
final class DownloadController {
    var shareText = ""
    private(set) var status = "粘贴抖音或 TikTok 分享链接。"
    private(set) var isDownloading = false
    private(set) var clipboardText = ""
    private(set) var clipboardURL: URL?

    /// Remote version-policy outcome, refreshed once at startup. Fail-open:
    /// defaults to `.allow`, so a missing/blocked policy never stops the app.
    private(set) var policyStatus: PolicyStatus = .allow
    private var policyChecked = false

    /// Auto-update state for hard-blocked versions.
    enum UpdateState: Equatable {
        case idle
        case checking
        case downloading
        case done(String)
        case failed(String)
    }
    private(set) var updateState: UpdateState = .idle

    /// Manual update check result (title/message/links) shown as an alert.
    struct UpdateAlert: Equatable {
        let title: String
        let message: String
        let releaseURL: URL?
        let dmgURL: URL?
    }
    var updateAlert: UpdateAlert?

    /// Manually check for a newer release and surface the per-platform
    /// changelog in an alert (no auto-download unless the user opts in).
    func checkForUpdatesManually() async {
        do {
            let result = try await AppUpdateService.checkForUpdates()
            var message: String
            if result.isUpdateAvailable {
                message = "发现新版本 v\(result.latestVersion)；当前版本为 v\(result.currentVersion)。"
            } else {
                message = "当前已是最新版本 v\(result.currentVersion)。"
            }
            if !result.changelog.isEmpty {
                message += "\n\n【更新日志】\n\(result.changelog)"
            }
            updateAlert = UpdateAlert(
                title: "软件更新",
                message: message,
                releaseURL: result.releaseURL,
                dmgURL: result.dmgURL
            )
        } catch {
            updateAlert = UpdateAlert(
                title: "软件更新",
                message: "检查更新失败：\(error.localizedDescription)",
                releaseURL: nil,
                dmgURL: nil
            )
        }
    }

    private var pasteboardChangeCount = -1

    var canDownload: Bool {
        !isDownloading && sourceURL != nil
    }

    var sourceURL: URL? {
        ShareTextParser.urls(in: shareText).first
    }

    var sourcePlatform: DownloadPlatform? {
        sourceURL.flatMap(Self.platform(for:))
    }

    var clipboardPlatform: DownloadPlatform? {
        clipboardURL.flatMap(Self.platform(for:))
    }

    func refreshClipboard(force: Bool = false) {
        let pasteboard = NSPasteboard.general
        guard force || pasteboard.changeCount != pasteboardChangeCount else { return }

        pasteboardChangeCount = pasteboard.changeCount
        clipboardText = pasteboard.string(forType: .string) ?? ""
        clipboardURL = ShareTextParser.urls(in: clipboardText).first
    }

    func pasteFromClipboard() {
        refreshClipboard(force: true)
        guard clipboardURL != nil else {
            status = "剪贴板中没有可识别的抖音或 TikTok 链接。"
            return
        }

        shareText = clipboardText
        status = "已从剪贴板识别链接，可以开始下载。"
    }

    func downloadFromClipboard() {
        pasteFromClipboard()
        guard sourceURL != nil else {
            status = "剪贴板中没有可识别的抖音或 TikTok 链接。"
            return
        }

        startDownload()
    }

    func startDownload() {
        guard !isDownloading,
              let sourceURL = ShareTextParser.urls(in: shareText).first else { return }

        isDownloading = true
        status = "正在解析并下载…"

        Task {
            defer { isDownloading = false }
            let gate = await DownloadPolicyService.evaluate()
            if case let .block(_, message, _) = gate {
                self.status = message
                return
            }
            do {
                let files = try await MediaDownloadService.downloadDirectMedia(from: sourceURL)
                status = "已保存 \(files.count) 个文件到“文稿/MediaDownloader”。"
            } catch {
                status = error.localizedDescription
            }
        }
    }

    func revealDownloads() {
        do {
            let documents = try FileManager.default.url(
                for: .documentDirectory,
                in: .userDomainMask,
                appropriateFor: nil,
                create: true
            )
            let downloads = documents.appendingPathComponent("MediaDownloader", isDirectory: true)
            try FileManager.default.createDirectory(at: downloads, withIntermediateDirectories: true)
            NSWorkspace.shared.open(downloads)
        } catch {
            status = "无法打开下载目录：\(error.localizedDescription)"
        }
    }

    func refreshPolicy() async {
        guard !policyChecked else { return }
        policyChecked = true
        policyStatus = await VersionPolicyService.evaluate()
        // Auto-download update when hard-blocked.
        if policyStatus.isBlock {
            await autoUpdate()
        }
    }

    private func autoUpdate() async {
        updateState = .checking
        do {
            let result = try await AppUpdateService.checkForUpdates()
            guard result.isUpdateAvailable, let dmgURL = result.dmgURL else {
                updateState = .failed("未找到可用的更新包。")
                return
            }
            updateState = .downloading
            try await AppUpdateService.downloadAndOpenDMG(from: dmgURL)
            var doneMsg = "安装包已打开，请将 MediaDownloader 拖入“应用程序”完成更新。"
            if !result.changelog.isEmpty {
                doneMsg += "\n\n【更新日志】\n\(result.changelog)"
            }
            updateState = .done(doneMsg)
        } catch {
            updateState = .failed(error.localizedDescription)
        }
    }

    private static func platform(for url: URL) -> DownloadPlatform? {
        let host = url.host?.lowercased() ?? ""
        if host.contains("douyin.com") || host.contains("iesdouyin.com") {
            return .douyin
        }
        if host.contains("tiktok.com") {
            return .tiktok
        }
        return nil
    }
}
