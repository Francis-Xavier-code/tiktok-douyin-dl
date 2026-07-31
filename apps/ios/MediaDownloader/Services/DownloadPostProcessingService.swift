import Foundation
import Photos

enum DownloadPostProcessingError: LocalizedError {
    case photoAccessDenied
    case syncFolderUnavailable

    var errorDescription: String? {
        switch self {
        case .photoAccessDenied:
            return "没有获得向照片图库添加媒体的权限。"
        case .syncFolderUnavailable:
            return "无法访问已选择的 iCloud Drive 文件夹，请在设置中重新选择。"
        }
    }
}

enum DownloadPostProcessingService {
    static let saveToPhotosKey = "saveDownloadsToPhotos"
    static let mirrorToCloudFolderKey = "mirrorDownloadsToCloudFolder"

    private static let folderBookmarkKey = "cloudSyncFolderBookmark"
    private static let folderDisplayNameKey = "cloudSyncFolderDisplayName"

    static var hasSelectedCloudFolder: Bool {
        UserDefaults.standard.data(forKey: folderBookmarkKey) != nil
    }

    static var selectedCloudFolderDisplayName: String? {
        UserDefaults.standard.string(forKey: folderDisplayNameKey)
    }

    static func saveCloudFolder(_ folderURL: URL) throws {
        let didStartAccess = folderURL.startAccessingSecurityScopedResource()
        defer {
            if didStartAccess {
                folderURL.stopAccessingSecurityScopedResource()
            }
        }

        let bookmark = try folderURL.bookmarkData(
            options: [],
            includingResourceValuesForKeys: [.nameKey],
            relativeTo: nil
        )
        UserDefaults.standard.set(bookmark, forKey: folderBookmarkKey)
        UserDefaults.standard.set(folderURL.lastPathComponent, forKey: folderDisplayNameKey)
    }

    static func ensurePhotoLibraryAccess() async -> Bool {
        let currentStatus = PHPhotoLibrary.authorizationStatus(for: .addOnly)
        switch currentStatus {
        case .authorized, .limited:
            return true
        case .denied, .restricted:
            return false
        case .notDetermined:
            return await withCheckedContinuation { continuation in
                PHPhotoLibrary.requestAuthorization(for: .addOnly) { status in
                    continuation.resume(returning: status == .authorized || status == .limited)
                }
            }
        @unknown default:
            return false
        }
    }

    static func processDownloadedFiles(_ fileURLs: [URL]) async {
        let defaults = UserDefaults.standard

        if defaults.bool(forKey: saveToPhotosKey) {
            do {
                try await saveToPhotos(fileURLs)
            } catch {
                print("[DownloadPostProcessing] Photos copy failed: \(error.localizedDescription)")
            }
        }

        if defaults.bool(forKey: mirrorToCloudFolderKey) {
            do {
                try await mirrorToSelectedCloudFolder(fileURLs)
            } catch {
                print("[DownloadPostProcessing] Cloud folder copy failed: \(error.localizedDescription)")
            }
        }
    }

    static func mirrorExistingLocalDownloads() async throws {
        let documentsURL = try FileManager.default.url(
            for: .documentDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: false
        )
        let downloadsURL = documentsURL.appendingPathComponent("MediaDownloader", isDirectory: true)
        guard FileManager.default.fileExists(atPath: downloadsURL.path) else { return }

        let fileURLs = try FileManager.default.contentsOfDirectory(
            at: downloadsURL,
            includingPropertiesForKeys: [.fileSizeKey],
            options: .skipsHiddenFiles
        )
        guard !fileURLs.isEmpty else { return }
        try await mirrorToSelectedCloudFolder(fileURLs)
    }

    private static func saveToPhotos(_ fileURLs: [URL]) async throws {
        guard await ensurePhotoLibraryAccess() else {
            throw DownloadPostProcessingError.photoAccessDenied
        }

        for fileURL in fileURLs {
            guard let resourceType = photoResourceType(for: fileURL) else { continue }

            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                PHPhotoLibrary.shared().performChanges {
                    let request = PHAssetCreationRequest.forAsset()
                    let options = PHAssetResourceCreationOptions()
                    options.originalFilename = fileURL.lastPathComponent
                    request.addResource(with: resourceType, fileURL: fileURL, options: options)
                } completionHandler: { succeeded, error in
                    if let error {
                        continuation.resume(throwing: error)
                    } else if succeeded {
                        continuation.resume(returning: ())
                    } else {
                        continuation.resume(throwing: DownloadPostProcessingError.photoAccessDenied)
                    }
                }
            }
        }
    }

    private static func mirrorToSelectedCloudFolder(_ fileURLs: [URL]) async throws {
        guard let bookmark = UserDefaults.standard.data(forKey: folderBookmarkKey) else {
            throw DownloadPostProcessingError.syncFolderUnavailable
        }

        try await Task.detached(priority: .utility) {
            var isStale = false
            let folderURL = try URL(
                resolvingBookmarkData: bookmark,
                options: [],
                relativeTo: nil,
                bookmarkDataIsStale: &isStale
            )
            guard !isStale, folderURL.startAccessingSecurityScopedResource() else {
                throw DownloadPostProcessingError.syncFolderUnavailable
            }
            defer { folderURL.stopAccessingSecurityScopedResource() }

            var coordinationError: NSError?
            var copyError: Error?
            NSFileCoordinator().coordinate(
                writingItemAt: folderURL,
                options: .forMerging,
                error: &coordinationError
            ) { coordinatedFolderURL in
                do {
                    for fileURL in fileURLs {
                        guard let destinationURL = availableDestinationURL(
                            in: coordinatedFolderURL,
                            for: fileURL
                        ) else { continue }
                        try FileManager.default.copyItem(at: fileURL, to: destinationURL)
                    }
                } catch {
                    copyError = error
                }
            }

            if let copyError {
                throw copyError
            }
            if let coordinationError {
                throw coordinationError
            }
        }.value
    }

    private static func availableDestinationURL(in directory: URL, for sourceURL: URL) -> URL? {
        let filename = sourceURL.lastPathComponent
        let originalURL = directory.appendingPathComponent(filename)
        guard FileManager.default.fileExists(atPath: originalURL.path) else {
            return originalURL
        }

        let sourceSize = try? sourceURL.resourceValues(forKeys: [.fileSizeKey]).fileSize
        let existingSize = try? originalURL.resourceValues(forKeys: [.fileSizeKey]).fileSize
        if sourceSize != nil && sourceSize == existingSize {
            return nil
        }

        let filenameURL = URL(fileURLWithPath: filename)
        let baseName = filenameURL.deletingPathExtension().lastPathComponent
        let pathExtension = filenameURL.pathExtension
        var suffix = 2

        while true {
            let candidateName = pathExtension.isEmpty
                ? "\(baseName)-\(suffix)"
                : "\(baseName)-\(suffix).\(pathExtension)"
            let candidateURL = directory.appendingPathComponent(candidateName)
            if !FileManager.default.fileExists(atPath: candidateURL.path) {
                return candidateURL
            }
            suffix += 1
        }
    }

    private static func photoResourceType(for fileURL: URL) -> PHAssetResourceType? {
        switch fileURL.pathExtension.lowercased() {
        case "jpg", "jpeg", "png", "heic", "heif", "gif", "webp":
            return .photo
        case "mp4", "mov", "m4v":
            return .video
        default:
            return nil
        }
    }
}
