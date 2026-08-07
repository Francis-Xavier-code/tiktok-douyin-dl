import SwiftUI
import UniformTypeIdentifiers

@MainActor
struct SettingsView: View {
    @Environment(\.openURL) private var openURL
    @AppStorage("automaticallyChecksForUpdates") private var automaticallyChecksForUpdates = true
    @AppStorage("saveDownloadsToPhotos") private var saveDownloadsToPhotos = false
    @AppStorage("mirrorDownloadsToCloudFolder") private var mirrorDownloadsToCloudFolder = false

    @State private var isCheckingForUpdates = false
    @State private var updateMessage: String?
    @State private var availableUpdateURL: URL?
    @State private var isSelectingCloudFolder = false
    @State private var cloudFolderName = DownloadPostProcessingService.selectedCloudFolderDisplayName ?? "未选择"
    @State private var storageMessage: String?

    private let avatarURL = URL(
        string: "https://gh-proxy.org/https://avatars.githubusercontent.com/u/203426472?v=4&size=64"
    )!
    private let authorURL = URL(string: "https://github.com/Xynrin")!
    private let repositoryURL = URL(string: "https://github.com/Francis-Xavier-code/tiktok-douyin-dl")!

    var body: some View {
        Form {
            Section("关于作者 & 项目") {
                HStack(spacing: 14) {
                    AsyncImage(url: avatarURL) { phase in
                        switch phase {
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFill()
                        case .empty:
                            ProgressView()
                        case .failure:
                            Image(systemName: "person.crop.circle.fill")
                                .resizable()
                                .foregroundStyle(.blue.gradient)
                        @unknown default:
                            Image(systemName: "person.crop.circle.fill")
                                .resizable()
                                .foregroundStyle(.blue.gradient)
                        }
                    }
                    .frame(width: 56, height: 56)
                    .background(Color(uiColor: .secondarySystemGroupedBackground))
                    .clipShape(Circle())
                    .overlay {
                        Circle()
                            .strokeBorder(.white.opacity(0.75), lineWidth: 2)
                    }
                    .shadow(color: .black.opacity(0.12), radius: 5, y: 2)

                    VStack(alignment: .leading, spacing: 5) {
                        Link(destination: authorURL) {
                            HStack(spacing: 5) {
                                Text("Xynrin")
                                    .font(.headline)
                                Image(systemName: "arrow.up.right")
                                    .font(.caption.weight(.semibold))
                            }
                        }

                        Text("开源项目作者")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()
                }
                .padding(.vertical, 5)

                Link(destination: repositoryURL) {
                    SettingsInfoRow(
                        title: "GitHub 仓库",
                        systemImage: "chevron.left.forwardslash.chevron.right",
                        value: "查看",
                        showsExternalLink: true
                    )
                }
                .foregroundStyle(.primary)

                SettingsInfoRow(
                    title: "最低系统版本",
                    systemImage: "iphone",
                    value: "iOS 17.0"
                )
            }

            Section {
                Toggle("同时保存到照片", isOn: $saveDownloadsToPhotos)

                Toggle("镜像到 iCloud Drive", isOn: cloudFolderMirrorBinding)

                Button {
                    isSelectingCloudFolder = true
                } label: {
                    HStack {
                        Label("同步文件夹", systemImage: "icloud.and.arrow.up")
                        Spacer()
                        Text(cloudFolderName)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                        Image(systemName: "chevron.right")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.tertiary)
                    }
                }
                .foregroundStyle(.primary)
            } header: {
                Text("保存位置")
            } footer: {
                Text("默认仍只保存在 App 的本地文件目录。开启照片后会额外复制图片和视频；开启 iCloud 后，请在系统文件选择器中选择一个 iCloud Drive 文件夹。")
            }
            .onChange(of: saveDownloadsToPhotos) { _, isEnabled in
                guard isEnabled else { return }
                Task {
                    guard await DownloadPostProcessingService.ensurePhotoLibraryAccess() else {
                        saveDownloadsToPhotos = false
                        storageMessage = "照片权限未开启，下载仍会保存在本地文件中。可前往系统设置允许此 App 添加照片。"
                        return
                    }
                }
            }
            .alert("保存位置", isPresented: storageAlertBinding) {
                Button("好", role: .cancel) {
                    storageMessage = nil
                }
            } message: {
                Text(storageMessage ?? "")
            }

            Section("软件更新") {
                LabeledContent("当前版本", value: versionDescription)

                Toggle("进入设置时检查更新", isOn: $automaticallyChecksForUpdates)

                Button {
                    Task {
                        await checkForUpdates(showUpToDateMessage: true)
                    }
                } label: {
                    HStack {
                        Label("检查 GitHub 更新", systemImage: "arrow.triangle.2.circlepath")
                        Spacer()
                        if isCheckingForUpdates {
                            ProgressView()
                                .controlSize(.small)
                        }
                    }
                }
                .disabled(isCheckingForUpdates)

                Text("仅检测 ios-v* GitHub Release 并打开发布页，不会静默安装；自签版本更新时仍需重新签名。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section("功能声明") {
                Text("本软件仅用于个人合规的学习与测试，请尊重原作者版权和平台规则。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section("后续规划") {
                Text("更多功能（如批量下载、历史同步、网络连接优化等）将在后续版本陆续加入，敬请期待！")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .fileImporter(
            isPresented: $isSelectingCloudFolder,
            allowedContentTypes: [.folder],
            allowsMultipleSelection: false
        ) { result in
            handleCloudFolderSelection(result)
        }
        .task {
            if automaticallyChecksForUpdates {
                await checkForUpdates(showUpToDateMessage: false)
            }
        }
        .alert("软件更新", isPresented: updateAlertBinding) {
            if let availableUpdateURL {
                Button("查看发布页") {
                    openURL(availableUpdateURL)
                    clearUpdateAlert()
                }
            }
            Button("好", role: .cancel) {
                clearUpdateAlert()
            }
        } message: {
            Text(updateMessage ?? "")
        }
    }

    private var versionDescription: String {
        let version = Bundle.main.object(
            forInfoDictionaryKey: "CFBundleShortVersionString"
        ) as? String ?? "2.0.1"
        let build = Bundle.main.object(
            forInfoDictionaryKey: "CFBundleVersion"
        ) as? String ?? "1"
        return "\(version) (\(build))"
    }

    private var updateAlertBinding: Binding<Bool> {
        Binding(
            get: { updateMessage != nil },
            set: { isPresented in
                if !isPresented {
                    clearUpdateAlert()
                }
            }
        )
    }

    private var cloudFolderMirrorBinding: Binding<Bool> {
        Binding(
            get: { mirrorDownloadsToCloudFolder },
            set: { isEnabled in
                if isEnabled && !DownloadPostProcessingService.hasSelectedCloudFolder {
                    isSelectingCloudFolder = true
                } else {
                    mirrorDownloadsToCloudFolder = isEnabled
                    if isEnabled {
                        syncExistingFilesToCloudFolder()
                    }
                }
            }
        )
    }

    private var storageAlertBinding: Binding<Bool> {
        Binding(
            get: { storageMessage != nil },
            set: { isPresented in
                if !isPresented {
                    storageMessage = nil
                }
            }
        )
    }

    private func checkForUpdates(showUpToDateMessage: Bool) async {
        guard !isCheckingForUpdates else { return }
        isCheckingForUpdates = true
        defer { isCheckingForUpdates = false }

        do {
            let result = try await AppUpdateService.checkForUpdates()
            if result.isUpdateAvailable {
                availableUpdateURL = result.releaseURL
                var msg = "发现 iOS \(result.latestVersion)；当前版本为 \(result.currentVersion)。请前往发布页获取新版并重新签名安装。"
                if !result.changelog.isEmpty {
                    msg += "\n\n【更新日志】\n\(result.changelog)"
                }
                updateMessage = msg
            } else if showUpToDateMessage {
                availableUpdateURL = nil
                updateMessage = "当前已是最新的 iOS \(result.currentVersion) 版本。"
            }
        } catch {
            if showUpToDateMessage {
                availableUpdateURL = nil
                updateMessage = error.localizedDescription
            }
        }
    }

    private func clearUpdateAlert() {
        updateMessage = nil
        availableUpdateURL = nil
    }

    private func handleCloudFolderSelection(_ result: Result<[URL], Error>) {
        do {
            guard let folderURL = try result.get().first else { return }
            try DownloadPostProcessingService.saveCloudFolder(folderURL)
            cloudFolderName = folderURL.lastPathComponent
            mirrorDownloadsToCloudFolder = true
            syncExistingFilesToCloudFolder()
        } catch {
            mirrorDownloadsToCloudFolder = false
            storageMessage = "无法保存所选文件夹的访问权限：\(error.localizedDescription)"
        }
    }

    private func syncExistingFilesToCloudFolder() {
        Task {
            do {
                try await DownloadPostProcessingService.mirrorExistingLocalDownloads()
            } catch {
                storageMessage = "同步已有文件失败：\(error.localizedDescription)"
            }
        }
    }
}

private struct SettingsInfoRow: View {
    let title: String
    let systemImage: String
    let value: String
    var showsExternalLink = false

    var body: some View {
        HStack(spacing: 12) {
            Label(title, systemImage: systemImage)

            Spacer(minLength: 12)

            Text(value)
                .foregroundStyle(.secondary)

            if showsExternalLink {
                Image(systemName: "arrow.up.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
        }
        .frame(minHeight: 24)
        .contentShape(Rectangle())
    }
}

#Preview {
    NavigationStack {
        SettingsView()
            .navigationTitle("设置")
    }
}
