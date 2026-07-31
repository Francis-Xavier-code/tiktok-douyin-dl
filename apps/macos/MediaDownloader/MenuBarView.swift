import AppKit
import SwiftUI

struct MenuBarView: View {
    let controller: DownloadController

    @Environment(\.openWindow) private var openWindow

    var body: some View {
        Button("打开 MediaDownloader") {
            openWindow(id: "main")
            NSApp.activate(ignoringOtherApps: true)
        }

        Divider()

        Button("从剪贴板下载") {
            controller.downloadFromClipboard()
        }
        .disabled(controller.isDownloading)

        Button("打开下载目录") {
            controller.revealDownloads()
        }

        if controller.isDownloading {
            Label("正在下载…", systemImage: "arrow.down.circle")
        } else {
            Text(controller.status)
        }

        Divider()

        Button("退出 MediaDownloader") {
            NSApp.terminate(nil)
        }
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
