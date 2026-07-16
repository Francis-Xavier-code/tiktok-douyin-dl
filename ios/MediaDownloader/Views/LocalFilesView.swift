import SwiftUI
import QuickLook
import AVKit

struct LocalFilesView: View {
    @Environment(DownloadStore.self) private var downloadStore
    @State private var files: [URL] = []
    @State private var selectedFileForPreview: URL?
    @State private var pendingDeletion: URL?

    var body: some View {
        List {
            if files.isEmpty {
                ContentUnavailableView(
                    "暂无本地文件",
                    systemImage: "folder.badge.minus",
                    description: Text("下载后的视频和图片会保存在这里。")
                )
            } else {
                ForEach(files, id: \.self) { fileURL in
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(fileURL.lastPathComponent)
                                .font(.subheadline)
                                .lineLimit(1)
                            Text(fileSizeAndDateString(for: fileURL))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()

                        // Share button to export/save to Photos
                        ShareLink(item: fileURL) {
                            Image(systemName: "square.and.arrow.up")
                                .font(.body)
                                .foregroundStyle(.blue)
                        }
                        .buttonStyle(.borderless)
                        .padding(.trailing, 8)

                        Button(role: .destructive) {
                            pendingDeletion = fileURL
                        } label: {
                            Image(systemName: "trash")
                                .font(.body)
                        }
                        .buttonStyle(.borderless)
                        .accessibilityLabel("删除 \(fileURL.lastPathComponent)")
                    }
                    .contentShape(Rectangle())
                    .onTapGesture {
                        selectedFileForPreview = fileURL
                    }
                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                        Button("删除", role: .destructive) {
                            pendingDeletion = fileURL
                        }
                    }
                }
            }
        }
        .navigationTitle("本地文件")
        .toolbar {
            Button {
                loadFiles()
            } label: {
                Image(systemName: "arrow.clockwise")
            }
        }
        .onAppear(perform: loadFiles)
        .quickLookPreview($selectedFileForPreview)
        .confirmationDialog(
            "删除本地文件？",
            isPresented: pendingDeletionBinding,
            titleVisibility: .visible,
            presenting: pendingDeletion
        ) { fileURL in
            Button("删除", role: .destructive) {
                deleteFile(fileURL)
            }
            Button("取消", role: .cancel) {}
        } message: { fileURL in
            Text("将删除 \(fileURL.lastPathComponent)。已经复制到照片或 iCloud Drive 的副本不会被删除。")
        }
    }

    private func loadFiles() {
        do {
            let documents = try FileManager.default.url(
                for: .documentDirectory,
                in: .userDomainMask,
                appropriateFor: nil,
                create: false
            )
            let directory = documents.appendingPathComponent("MediaDownloader", isDirectory: true)
            if FileManager.default.fileExists(atPath: directory.path) {
                let fileURLs = try FileManager.default.contentsOfDirectory(
                    at: directory,
                    includingPropertiesForKeys: [.contentModificationDateKey, .fileSizeKey],
                    options: .skipsHiddenFiles
                )

                // Sort by modification date descending
                files = fileURLs.sorted { url1, url2 in
                    let date1 = (try? url1.resourceValues(forKeys: [.contentModificationDateKey]))?.contentModificationDate ?? Date.distantPast
                    let date2 = (try? url2.resourceValues(forKeys: [.contentModificationDateKey]))?.contentModificationDate ?? Date.distantPast
                    return date1 > date2
                }
            } else {
                files = []
            }
        } catch {
            print("Failed to load files: \(error)")
        }
    }

    private var pendingDeletionBinding: Binding<Bool> {
        Binding(
            get: { pendingDeletion != nil },
            set: { isPresented in
                if !isPresented {
                    pendingDeletion = nil
                }
            }
        )
    }

    private func deleteFile(_ fileURL: URL) {
        do {
            try FileManager.default.removeItem(at: fileURL)
            files.removeAll { $0 == fileURL }
            downloadStore.removeLocalFileReference(to: fileURL)
            if selectedFileForPreview == fileURL {
                selectedFileForPreview = nil
            }
        } catch {
            print("Failed to delete file: \(error)")
        }
        pendingDeletion = nil
    }

    private func fileSizeAndDateString(for url: URL) -> String {
        let values = try? url.resourceValues(forKeys: [.fileSizeKey, .contentModificationDateKey])
        let size = values?.fileSize ?? 0
        let date = values?.contentModificationDate ?? Date()

        let sizeString = ByteCountFormatter.string(fromByteCount: Int64(size), countStyle: .file)

        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        let dateString = formatter.string(from: date)

        return "\(sizeString) • \(dateString)"
    }
}
