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
                Text("此模式只保存服务器直接提供的视频、图片或音频。抖音和 TikTok 分享链接的完整解析，请使用已部署的 Docker WebUI。")
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
