import SwiftUI
import QuickLook

struct ContentView: View {
    @Environment(DownloadStore.self) private var downloadStore

    var body: some View {
        TabView {
            NavigationStack {
                DownloadsView(records: downloadStore.records)
                    .navigationTitle("下载")
                    .toolbar {
                        NavigationLink {
                            DownloadFormView()
                        } label: {
                            Label("新建下载", systemImage: "plus")
                        }
                    }
            }
            .tabItem { Label("下载", systemImage: "arrow.down.circle") }

            NavigationStack {
                LocalFilesView()
            }
            .tabItem { Label("本地文件", systemImage: "folder.fill") }

            NavigationStack {
                SettingsView()
                    .navigationTitle("设置")
            }
            .tabItem { Label("设置", systemImage: "gearshape") }
        }
        .background {
            Color(uiColor: .systemGroupedBackground)
                .ignoresSafeArea()
        }
    }
}

private struct DownloadsView: View {
    let records: [DownloadRecord]
    @State private var selectedFileForPreview: URL?

    var body: some View {
        Group {
            if records.isEmpty {
                ContentUnavailableView(
                    "还没有下载",
                    systemImage: "tray",
                    description: Text("点右上角加号，粘贴直链或分享文本。")
                )
            } else {
                List(records) { record in
                    DownloadRecordCard(record: record)
                        .contentShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                        .onTapGesture {
                            selectedFileForPreview = record.savedFileURL
                        }
                        .listRowInsets(EdgeInsets(top: 7, leading: 16, bottom: 7, trailing: 16))
                        .listRowSeparator(.hidden)
                        .listRowBackground(Color.clear)
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
                .background(Color(uiColor: .systemGroupedBackground))
            }
        }
        .quickLookPreview($selectedFileForPreview)
    }
}

private struct DownloadRecordCard: View {
    let record: DownloadRecord

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(platformGradient)
                    Image(systemName: platformSymbol)
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.white)
                }
                .frame(width: 48, height: 48)

                VStack(alignment: .leading, spacing: 4) {
                    Text(platformTitle)
                        .font(.headline)
                    Text(detailText)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                Spacer(minLength: 8)
                DownloadStatusBadge(state: record.state)
            }

            if case .failed(let reason) = record.state {
                Label(reason, systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .lineLimit(2)
            }

            Divider()

            HStack(spacing: 6) {
                Image(systemName: "clock")
                Text(record.createdAt.formatted(date: .abbreviated, time: .shortened))

                Spacer()

                if record.savedFileURL != nil {
                    Label("轻点预览", systemImage: "eye")
                        .foregroundStyle(Color.accentColor)
                } else if case .downloading = record.state {
                    ProgressView()
                        .controlSize(.small)
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color(uiColor: .secondarySystemGroupedBackground))
        )
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(platformAccent.opacity(0.14), lineWidth: 1)
        }
        .shadow(color: .black.opacity(0.04), radius: 8, y: 3)
        .accessibilityElement(children: .combine)
        .accessibilityHint(record.savedFileURL == nil ? "" : "轻点预览已下载文件")
    }

    private var platformTitle: String {
        switch record.platform {
        case .douyin:
            return "抖音媒体"
        case .tiktok:
            return "TikTok 媒体"
        }
    }

    private var detailText: String {
        if let savedFileURL = record.savedFileURL {
            return savedFileURL.lastPathComponent
        }
        switch record.state {
        case .downloading:
            return "正在解析并保存无水印媒体"
        case .completed:
            return "本地文件已删除"
        case .failed:
            return "下载未完成"
        }
    }

    private var platformSymbol: String {
        switch record.platform {
        case .douyin:
            return "music.note"
        case .tiktok:
            return "play.fill"
        }
    }

    private var platformAccent: Color {
        switch record.platform {
        case .douyin:
            return .pink
        case .tiktok:
            return .indigo
        }
    }

    private var platformGradient: LinearGradient {
        switch record.platform {
        case .douyin:
            return LinearGradient(colors: [.pink, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
        case .tiktok:
            return LinearGradient(colors: [.indigo, .pink], startPoint: .topLeading, endPoint: .bottomTrailing)
        }
    }
}

private struct DownloadStatusBadge: View {
    let state: DownloadState

    var body: some View {
        Label(title, systemImage: symbol)
            .font(.caption2.weight(.semibold))
            .foregroundStyle(color)
            .padding(.horizontal, 9)
            .padding(.vertical, 6)
            .background(color.opacity(0.12), in: Capsule())
    }

    private var title: String {
        switch state {
        case .downloading:
            return "下载中"
        case .completed:
            return "已保存"
        case .failed:
            return "未完成"
        }
    }

    private var symbol: String {
        switch state {
        case .downloading:
            return "arrow.down"
        case .completed:
            return "checkmark"
        case .failed:
            return "exclamationmark"
        }
    }

    private var color: Color {
        switch state {
        case .downloading:
            return .blue
        case .completed:
            return .green
        case .failed:
            return .orange
        }
    }
}

#Preview {
    ContentView()
        .environment(DownloadStore())
}

#Preview("下载记录卡片") {
    NavigationStack {
        DownloadsView(records: [
            DownloadRecord(
                platform: .douyin,
                sourceURL: URL(string: "https://v.douyin.com/example")!,
                savedFileURL: URL(fileURLWithPath: "/tmp/[1]video.mp4"),
                state: .completed
            ),
            DownloadRecord(
                platform: .tiktok,
                sourceURL: URL(string: "https://www.tiktok.com/example")!,
                state: .downloading
            )
        ])
        .navigationTitle("下载")
    }
}
