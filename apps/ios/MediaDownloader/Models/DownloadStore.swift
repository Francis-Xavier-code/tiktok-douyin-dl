import Foundation
import Observation

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
