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
                Text("免责声明：本软件仅用于个人合规的学习与测试。因使用本软件下载媒体文件所引致的任何版权争议或法律责任，均由使用者本人承担。请尊重原作者的知识产权。")
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
