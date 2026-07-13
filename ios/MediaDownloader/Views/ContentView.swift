import SwiftUI

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
                BackendView()
                    .navigationTitle("Web 下载")
            }
            .tabItem { Label("Web 下载", systemImage: "globe") }

            NavigationStack {
                SettingsView()
                    .navigationTitle("设置")
            }
            .tabItem { Label("设置", systemImage: "gearshape") }
        }
    }
}

private struct DownloadsView: View {
    let records: [DownloadRecord]

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
                    VStack(alignment: .leading, spacing: 6) {
                        Text(record.sourceURL.host ?? record.platform.title)
                            .font(.headline)
                        Text(record.sourceURL.absoluteString)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                        HStack {
                            Label(record.platform.title, systemImage: "play.rectangle")
                            Spacer()
                            statusLabel(record.state)
                        }
                        .font(.caption)
                    }
                    .padding(.vertical, 4)
                }
            }
        }
    }

    @ViewBuilder
    private func statusLabel(_ state: DownloadState) -> some View {
        switch state {
        case .downloading:
            Label("下载中", systemImage: "arrow.down.circle")
                .foregroundStyle(.blue)
        case .completed:
            Label("已保存到“文件”", systemImage: "checkmark.circle.fill")
                .foregroundStyle(.green)
        case .failed(let reason):
            Label(reason, systemImage: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
                .lineLimit(1)
        }
    }
}

#Preview {
    ContentView()
        .environment(DownloadStore())
}
