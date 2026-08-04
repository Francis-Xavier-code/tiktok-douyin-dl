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
