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
                Text("欢迎使用 MediaDownloader。本软件仅作为网络自动化测试与编程学习的技术演示项目，不提供、不存储、不分发任何目标平台数据。严禁用于商业盈利、代下载服务或任何违法违规行为。所有媒体资源版权归原创作者及平台所有，用户须在24小时内销毁下载数据。因使用本软件导致的账号风险及一切后果由用户自行承担。继续使用即表示您同意上述全部条款。")
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
