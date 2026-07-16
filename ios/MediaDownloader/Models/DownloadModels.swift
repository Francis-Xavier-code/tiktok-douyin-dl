import Foundation
import Observation

enum DownloadPlatform: String, CaseIterable, Identifiable {
    case douyin
    case tiktok

    var id: String { rawValue }

    var title: String {
        switch self {
        case .douyin: "抖音 / Douyin"
        case .tiktok: "TikTok"
        }
    }
}

enum DownloadState: Equatable {
    case downloading
    case completed
    case failed(String)

    var title: String {
        switch self {
        case .downloading: "下载中"
        case .completed: "已保存"
        case .failed: "未完成"
        }
    }
}

struct DownloadRecord: Identifiable {
    let id: UUID
    let platform: DownloadPlatform
    let sourceURL: URL
    let createdAt = Date()
    var savedFileURL: URL?
    var state: DownloadState

    init(id: UUID = UUID(), platform: DownloadPlatform, sourceURL: URL, savedFileURL: URL? = nil, state: DownloadState) {
        self.id = id
        self.platform = platform
        self.sourceURL = sourceURL
        self.savedFileURL = savedFileURL
        self.state = state
    }
}

@MainActor
@Observable
final class DownloadStore {
    private(set) var records: [DownloadRecord] = []
    private(set) var isDownloading = false

    func downloadDirectMedia(from text: String, platform: DownloadPlatform) async throws {
        let urls = ShareTextParser.urls(in: text)
        guard !urls.isEmpty else {
            throw MediaDownloadError.noURLFound
        }

        isDownloading = true
        defer { isDownloading = false }

        for sourceURL in urls {
            let recordID = UUID()
            records.insert(
                DownloadRecord(
                    id: recordID,
                    platform: platform,
                    sourceURL: sourceURL,
                    state: .downloading
                ),
                at: 0
            )

            do {
                let savedFileURLs = try await MediaDownloadService.downloadDirectMedia(from: sourceURL)
                update(id: recordID, state: .completed, savedFileURL: savedFileURLs.first)
                await DownloadPostProcessingService.processDownloadedFiles(savedFileURLs)
            } catch {
                update(id: recordID, state: .failed(error.localizedDescription), savedFileURL: nil)
            }
        }
    }

    func removeLocalFileReference(to fileURL: URL) {
        for index in records.indices where records[index].savedFileURL == fileURL {
            records[index].savedFileURL = nil
        }
    }

    private func update(id: UUID, state: DownloadState, savedFileURL: URL?) {
        guard let index = records.firstIndex(where: { $0.id == id }) else { return }
        records[index].state = state
        records[index].savedFileURL = savedFileURL
    }
}
