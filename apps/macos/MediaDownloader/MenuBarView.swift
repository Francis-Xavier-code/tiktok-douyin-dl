import AppKit
import SwiftUI

struct MenuBarView: View {
    let controller: DownloadController

    @Environment(\.openWindow) private var openWindow

    var body: some View {
        Group {
            switch controller.policyStatus {
            case .allow:
                mainContent
            case .nag(let message, let url):
                VStack(spacing: 0) {
                    PolicyBanner(message: message, url: url)
                    mainContent
                }
            case .block(let message, let url):
                PolicyBlockView(message: message, url: url, updateState: controller.updateState)
            }
        }
        .frame(width: 360)
        .background(.ultraThinMaterial)
        .task {
            while !Task.isCancelled {
                controller.refreshClipboard()
                try? await Task.sleep(nanoseconds: 750_000_000)
            }
        }
    }

    private var mainContent: some View {
        VStack(spacing: 0) {
            header

            Divider()

            VStack(spacing: 12) {
                ClipboardDownloadCard(controller: controller)
                DownloadStatusRow(controller: controller)
            }
            .padding(14)

            Divider()

            footer
        }
    }


    private var header: some View {
        HStack(spacing: 11) {
            ZStack {
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [.blue, .purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                Image(systemName: "arrow.down")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(.white)
            }
            .frame(width: 38, height: 38)
            .shadow(color: .blue.opacity(0.22), radius: 5, y: 2)

            VStack(alignment: .leading, spacing: 2) {
                Text("MediaDownloader")
                    .font(.headline)
                Text("复制分享链接，一键保存")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            HStack(spacing: 5) {
                Circle()
                    .fill(controller.isDownloading ? Color.orange : Color.green)
                    .frame(width: 7, height: 7)
                Text(controller.isDownloading ? "下载中" : "就绪")
                    .font(.caption.weight(.medium))
            }
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .background(.quaternary, in: Capsule())
        }
        .padding(14)
    }

    private var footer: some View {
        HStack(spacing: 4) {
            Button {
                showMainWindow()
            } label: {
                Label("主窗口", systemImage: "macwindow")
            }
            .help("打开主窗口")

            Button {
                controller.revealDownloads()
            } label: {
                Label("下载目录", systemImage: "folder")
            }
            .help("打开下载目录")

            Spacer()

            Menu {
                Button("重新读取剪贴板", systemImage: "arrow.clockwise") {
                    controller.refreshClipboard(force: true)
                }

                Divider()

                Button("退出 MediaDownloader", systemImage: "power") {
                    NSApp.terminate(nil)
                }
            } label: {
                Image(systemName: "ellipsis.circle")
                    .font(.system(size: 14, weight: .medium))
            }
            .menuStyle(.borderlessButton)
            .fixedSize()
            .help("更多")
        }
        .buttonStyle(.borderless)
        .controlSize(.small)
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
    }

    private func showMainWindow() {
        openWindow(id: "main")
        NSApp.activate(ignoringOtherApps: true)
    }
}

private struct ClipboardDownloadCard: View {
    let controller: DownloadController

    var body: some View {
        Group {
            if let url = controller.clipboardURL {
                readyCard(url: url)
            } else {
                emptyCard
            }
        }
        .padding(14)
        .background(.background.opacity(0.72), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(.separator.opacity(0.65), lineWidth: 0.5)
        }
    }

    private func readyCard(url: URL) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 9) {
                Image(systemName: platformSymbol)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundStyle(platformColor)
                    .frame(width: 32, height: 32)
                    .background(platformColor.opacity(0.12), in: RoundedRectangle(cornerRadius: 8))

                VStack(alignment: .leading, spacing: 2) {
                    Text("已识别剪贴板中的\(platformName)链接")
                        .font(.subheadline.weight(.semibold))
                    Text(displayText(for: url))
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                }

                Spacer(minLength: 4)

                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
            }

            Button {
                controller.downloadFromClipboard()
            } label: {
                HStack {
                    if controller.isDownloading {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Image(systemName: "arrow.down.circle.fill")
                    }
                    Text(controller.isDownloading ? "正在下载…" : "立即下载")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(controller.isDownloading)
            .keyboardShortcut(.defaultAction)
        }
    }

    private var emptyCard: some View {
        VStack(spacing: 10) {
            Image(systemName: "doc.on.clipboard")
                .font(.system(size: 26, weight: .medium))
                .foregroundStyle(.secondary)

            Text("等待分享链接")
                .font(.subheadline.weight(.semibold))

            Text("复制抖音或 TikTok 的分享文字/链接，\n这里会自动识别，无需手动粘贴。")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            Button("重新读取剪贴板", systemImage: "arrow.clockwise") {
                controller.refreshClipboard(force: true)
            }
            .controlSize(.small)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 4)
    }

    private var platformName: String {
        switch controller.clipboardPlatform {
        case .douyin: "抖音"
        case .tiktok: "TikTok"
        case nil: "媒体"
        }
    }

    private var platformSymbol: String {
        switch controller.clipboardPlatform {
        case .douyin: "music.note"
        case .tiktok: "play.rectangle.fill"
        case nil: "link"
        }
    }

    private var platformColor: Color {
        switch controller.clipboardPlatform {
        case .douyin: .pink
        case .tiktok: .cyan
        case nil: .blue
        }
    }

    private func displayText(for url: URL) -> String {
        let host = url.host ?? url.absoluteString
        let path = url.path == "/" ? "" : url.path
        return host + path
    }
}

private struct DownloadStatusRow: View {
    let controller: DownloadController

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: statusSymbol)
                .foregroundStyle(statusColor)
                .symbolEffect(.pulse, isActive: controller.isDownloading)

            Text(controller.status)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(2)

            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 4)
    }

    private var statusSymbol: String {
        if controller.isDownloading {
            return "arrow.down.circle"
        }
        if controller.status.hasPrefix("已保存") {
            return "checkmark.circle.fill"
        }
        if controller.status.contains("没有") || controller.status.contains("无法") || controller.status.contains("失败") {
            return "exclamationmark.triangle.fill"
        }
        return "info.circle"
    }

    private var statusColor: Color {
        if controller.isDownloading {
            return .orange
        }
        if controller.status.hasPrefix("已保存") {
            return .green
        }
        if controller.status.contains("没有") || controller.status.contains("无法") || controller.status.contains("失败") {
            return .red
        }
        return .secondary
    }
}

struct DownloadCommands: Commands {
    let controller: DownloadController

    var body: some Commands {
        CommandMenu("下载") {
            Button("从剪贴板下载") {
                controller.downloadFromClipboard()
            }
            .keyboardShortcut("d", modifiers: [.command, .shift])

            Button("打开下载目录") {
                controller.revealDownloads()
            }
        }
    }
}
