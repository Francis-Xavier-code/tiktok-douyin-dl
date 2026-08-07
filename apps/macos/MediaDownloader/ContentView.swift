import SwiftUI

struct ContentView: View {
    @Bindable var controller: DownloadController
    @State private var showDisclaimer = false

    private var updateAlertBinding: Binding<Bool> {
        Binding(
            get: { controller.updateAlert != nil },
            set: { if !$0 { controller.updateAlert = nil } }
        )
    }

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
        .onAppear {
            if !UserDefaults.standard.bool(forKey: "disclaimer_agreed") {
                showDisclaimer = true
            }
        }
        .sheet(isPresented: $showDisclaimer) {
            DisclaimerSheet(isPresented: $showDisclaimer)
        }
        .alert(controller.updateAlert?.title ?? "软件更新", isPresented: updateAlertBinding) {
            if let dmgURL = controller.updateAlert?.dmgURL {
                Button("打开更新包") {
                    Task { try? await AppUpdateService.downloadAndOpenDMG(from: dmgURL) }
                }
            }
            if let releaseURL = controller.updateAlert?.releaseURL {
                Button("前往发布页") {
                    NSWorkspace.shared.open(releaseURL)
                }
            }
            Button("知道了", role: .cancel) {}
        } message: {
            Text(controller.updateAlert?.message ?? "")
        }
    }

    private var mainContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text("MediaDownloader")
                    .font(.largeTitle.bold())
                Text("v\(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "")")
                    .font(.callout)
                    .foregroundStyle(.tertiary)
            }

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

                Button("检查更新") {
                    Task { await controller.checkForUpdatesManually() }
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

// MARK: - Disclaimer sheet

struct DisclaimerSheet: View {
    @Binding var isPresented: Bool
    @State private var agreed = false
    @State private var dontShowAgain = false

    private let disclaimerText = """
    欢迎使用 MediaDownloader。本软件仅作为网络自动化测试与编程学习的技术演示项目，不提供、不存储、不分发任何目标平台数据。严禁用于商业盈利、代下载服务或任何违法违规行为。所有媒体资源版权归原创作者及平台所有，用户须在24小时内销毁下载数据。因使用本软件导致的账号风险及一切后果由用户自行承担。

    1. 【核心定位】本软件仅作为纯技术演示项目，模拟用户浏览器行为。
    2. 【禁止商用】严禁商业盈利、代下载服务、黑灰产引流、批量刷量。
    3. 【版权免责】所有媒体资源版权归原创作者及平台，用户须24小时内销毁。
    4. 【风控免责】因使用本软件导致的账号封禁、IP限制等后果由用户自行承担。
    5. 【免责条款】本软件按「原样」提供，不附带任何担保。
    6. 【开发者权利】开发者保留本协议最终解释权。
    """

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("免责声明")
                .font(.title2.bold())

            ScrollView {
                Text(disclaimerText)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            }
            .frame(maxHeight: 300)

            Divider()

            Toggle("我已阅读并同意上述全部条款", isOn: $agreed)
                .font(.body.weight(.medium))

            Toggle("下次不再提示（默认同意）", isOn: $dontShowAgain)
                .font(.caption)
                .foregroundStyle(.secondary)
                .disabled(!agreed)

            HStack {
                Spacer()
                Button("退出") {
                    NSApplication.shared.terminate(nil)
                }
                .keyboardShortcut(.cancelAction)
                Button("继续") {
                    if dontShowAgain {
                        UserDefaults.standard.set(true, forKey: "disclaimer_agreed")
                    }
                    isPresented = false
                }
                .keyboardShortcut(.defaultAction)
                .disabled(!agreed)
            }
        }
        .padding(24)
        .frame(width: 480)
    }
}
