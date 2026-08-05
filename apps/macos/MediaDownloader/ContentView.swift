import SwiftUI

struct ContentView: View {
    @Bindable var controller: DownloadController

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
        .frame(minWidth: 600, minHeight: 320)
    }

    private var mainContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("MediaDownloader")
                .font(.largeTitle.bold())

            TextEditor(text: $controller.shareText)
                .font(.body)
                .frame(width: 560, height: 150)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(.separator))
                .accessibilityLabel("分享文本或链接")

            HStack {
                Button(controller.isDownloading ? "下载中…" : "开始下载") {
                    controller.startDownload()
                }
                .buttonStyle(.borderedProminent)
                .disabled(!controller.canDownload)

                Button("打开下载目录") {
                    controller.revealDownloads()
                }

                Text(controller.status)
                    .foregroundStyle(.secondary)
            }

            Text("免责声明：本软件仅作为网络自动化测试与编程学习的技术演示项目。严禁用于商业盈利或违法违规行为。所有媒体资源版权归原创作者及平台所有，用户须在24小时内销毁下载数据。因使用本软件导致的一切后果由用户自行承担。继续使用即表示您同意上述全部条款。")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(24)
    }
}
