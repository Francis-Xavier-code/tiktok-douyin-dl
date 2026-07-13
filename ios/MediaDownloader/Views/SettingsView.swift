import SwiftUI
import WebKit

struct SettingsView: View {
    @AppStorage("backendURL") private var backendURL = ""

    var body: some View {
        Form {
            Section("Docker WebUI") {
                TextField("http://服务器地址:7860", text: $backendURL)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                    .autocorrectionDisabled()
                Text("部署本仓库的 Docker WebUI 后，在此填写局域网地址。例如：http://192.168.1.20:7860")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section("关于") {
                LabeledContent("最低系统版本", value: "iOS 17")
                Text("仅用于个人、合规的学习与测试。请尊重原作者版权和平台规则。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

struct BackendView: View {
    @AppStorage("backendURL") private var backendURL = ""

    var body: some View {
        Group {
            if let url = normalizedURL {
                BackendWebView(url: url)
                    .ignoresSafeArea(edges: .bottom)
            } else {
                ContentUnavailableView(
                    "尚未配置 WebUI",
                    systemImage: "server.rack",
                    description: Text("请在“设置”中填写运行本仓库 Docker WebUI 的服务器地址。")
                )
            }
        }
    }

    private var normalizedURL: URL? {
        let trimmed = backendURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        return URL(string: trimmed.hasPrefix("http") ? trimmed : "http://\(trimmed)")
    }
}

struct BackendWebView: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> WKWebView {
        let webView = WKWebView()
        webView.allowsBackForwardNavigationGestures = true
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        guard webView.url != url else { return }
        webView.load(URLRequest(url: url))
    }
}

#Preview {
    SettingsView()
}
