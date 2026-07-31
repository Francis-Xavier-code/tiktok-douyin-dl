import Foundation

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
