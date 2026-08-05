import Observation
import SwiftUI

@main
struct MediaDownloaderApp: App {
    @State private var downloadStore = DownloadStore()
    @State private var policy: PolicyStatus = .allow
    @State private var showDisclaimer = false

    var body: some Scene {
        WindowGroup {
            Group {
                switch policy {
                case .allow:
                    ContentView()
                        .environment(downloadStore)
                case .nag(let message, let url):
                    ContentView()
                        .environment(downloadStore)
                        .overlay(alignment: .top) {
                            PolicyBanner(message: message, url: url)
                        }
                case .block(let message, let url):
                    PolicyBlockView(message: message, url: url)
                }
            }
            .task {
                policy = await VersionPolicyService.evaluate()
                if !UserDefaults.standard.bool(forKey: "disclaimer_agreed") {
                    showDisclaimer = true
                }
            }
            .fullScreenCover(isPresented: $showDisclaimer) {
                DisclaimerAgreementView(isPresented: $showDisclaimer)
            }
        }
    }
}

// MARK: - Disclaimer agreement view

struct DisclaimerAgreementView: View {
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
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("免责声明")
                        .font(.title2.bold())

                    Text(disclaimerText)
                        .font(.callout)
                        .foregroundStyle(.secondary)

                    Divider()

                    Toggle("我已阅读并同意上述全部条款", isOn: $agreed)
                        .font(.body.weight(.medium))

                    Toggle("下次不再提示（默认同意）", isOn: $dontShowAgain)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .disabled(!agreed)
                }
                .padding()
            }
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("继续") {
                        if dontShowAgain {
                            UserDefaults.standard.set(true, forKey: "disclaimer_agreed")
                        }
                        isPresented = false
                    }
                    .disabled(!agreed)
                }
                ToolbarItem(placement: .cancellationAction) {
                    Button("退出") {
                        exit(0)
                    }
                }
            }
            .interactiveDismissDisabled()
        }
    }
}
