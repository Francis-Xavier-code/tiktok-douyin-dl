import AppKit
import Foundation
import Observation

@MainActor
@Observable
final class DownloadController {
    var shareText = ""
    private(set) var status = "粘贴抖音或 TikTok 分享链接。"
    private(set) var isDownloading = false

    var canDownload: Bool {
        !isDownloading && !ShareTextParser.urls(in: shareText).isEmpty
    }

    func downloadFromClipboard() {
        guard let clipboardText = NSPasteboard.general.string(forType: .string),
              !ShareTextParser.urls(in: clipboardText).isEmpty else {
            status = "剪贴板中没有可识别的抖音或 TikTok 链接。"
            return
        }

        shareText = clipboardText
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
}
