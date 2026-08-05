import SwiftUI

struct DownloadFormView: View {
    @Environment(DownloadStore.self) private var downloadStore
    @Environment(\.dismiss) private var dismiss
    @State private var platform: DownloadPlatform = .douyin
    @State private var shareText = ""
    @State private var alertMessage: String?

    var body: some View {
        Form {
            Section("来源") {
                Picker("平台", selection: $platform) {
                    ForEach(DownloadPlatform.allCases) { platform in
                        Text(platform.title).tag(platform)
                    }
                }
                .pickerStyle(.segmented)

                TextEditor(text: $shareText)
                    .frame(minHeight: 160)
                    .accessibilityLabel("链接或分享文本")
            }

            Section {
                Button {
                    Task { await startDownload() }
                } label: {
                    HStack {
                        Spacer()
                        if downloadStore.isDownloading {
                            ProgressView()
                                .padding(.trailing, 8)
                            Text("下载中")
                        } else {
                            Label("下载可直连媒体", systemImage: "arrow.down.to.line")
                        }
                        Spacer()
                    }
                }
                .disabled(shareText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || downloadStore.isDownloading)
            } footer: {
                Text("免责声明：本工具仅供个人学习、研究和合法的内容备份使用。请仅下载你拥有权利或已获得授权的内容，遵守所在地法律、平台服务条款及著作权规定。严禁将本工具用于商业侵权、非法抓取、绕过访问控制或网络攻击。使用本工具产生的版权、账号和数据安全风险由使用者自行承担。")
            }
        }
        .navigationTitle("新建下载")
        .navigationBarTitleDisplayMode(.inline)
        .alert("无法下载", isPresented: alertBinding) {
            Button("好", role: .cancel) { alertMessage = nil }
        } message: {
            Text(alertMessage ?? "")
        }
    }

    private var alertBinding: Binding<Bool> {
        Binding(get: { alertMessage != nil }, set: { if !$0 { alertMessage = nil } })
    }

    private func startDownload() async {
        do {
            try await downloadStore.downloadDirectMedia(from: shareText, platform: platform)
            dismiss()
        } catch {
            alertMessage = error.localizedDescription
        }
    }
}

#Preview {
    NavigationStack {
        DownloadFormView()
            .environment(DownloadStore())
    }
}
