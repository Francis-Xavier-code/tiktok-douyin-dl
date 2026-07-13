import Foundation

enum MediaDownloadError: LocalizedError {
    case noURLFound
    case notDirectMedia(URL)
    case invalidResponse

    var errorDescription: String? {
        switch self {
        case .noURLFound:
            "没有在分享文本中找到链接。"
        case .notDirectMedia:
            "这不是可直接下载的媒体链接。请在“Web 下载”中配置并使用本仓库的 Docker WebUI。"
        case .invalidResponse:
            "服务器没有返回可下载的媒体文件。"
        }
    }
}

enum ShareTextParser {
    static func urls(in text: String) -> [URL] {
        let pattern = #"https?://[^\s<>\"']+"#
        guard let expression = try? NSRegularExpression(pattern: pattern) else { return [] }
        let range = NSRange(text.startIndex..., in: text)
        return expression.matches(in: text, range: range).compactMap { match in
            guard let range = Range(match.range, in: text) else { return nil }
            return URL(string: String(text[range]))
        }
    }
}

enum MediaDownloadService {
    static func downloadDirectMedia(from sourceURL: URL) async throws -> URL {
        let session = URLSession(configuration: .ephemeral)
        var probe = URLRequest(url: sourceURL)
        probe.httpMethod = "GET"
        probe.setValue("bytes=0-1", forHTTPHeaderField: "Range")
        probe.setValue("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)", forHTTPHeaderField: "User-Agent")

        let (_, response) = try await session.data(for: probe)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw MediaDownloadError.invalidResponse
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            throw MediaDownloadError.invalidResponse
        }

        let resolvedURL = httpResponse.url ?? sourceURL
        let mimeType = httpResponse.mimeType?.lowercased() ?? ""
        guard isMedia(url: resolvedURL, mimeType: mimeType) else {
            throw MediaDownloadError.notDirectMedia(resolvedURL)
        }

        var request = URLRequest(url: resolvedURL)
        request.setValue("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)", forHTTPHeaderField: "User-Agent")
        let (temporaryURL, downloadResponse) = try await session.download(for: request)
        guard let downloadResponse = downloadResponse as? HTTPURLResponse,
              (200...299).contains(downloadResponse.statusCode) else {
            throw MediaDownloadError.invalidResponse
        }

        let destinationDirectory = try documentsDirectory()
        let filename = uniqueFilename(for: resolvedURL, mimeType: downloadResponse.mimeType)
        let destinationURL = destinationDirectory.appendingPathComponent(filename)
        try FileManager.default.moveItem(at: temporaryURL, to: destinationURL)
        return destinationURL
    }

    private static func isMedia(url: URL, mimeType: String) -> Bool {
        if mimeType.hasPrefix("video/") || mimeType.hasPrefix("image/") || mimeType.hasPrefix("audio/") {
            return true
        }
        let mediaExtensions = ["mp4", "mov", "m4v", "webm", "jpg", "jpeg", "png", "heic", "gif", "mp3", "m4a"]
        return mediaExtensions.contains(url.pathExtension.lowercased())
    }

    private static func documentsDirectory() throws -> URL {
        let documents = try FileManager.default.url(
            for: .documentDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let directory = documents.appendingPathComponent("MediaDownloader", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return directory
    }

    private static func uniqueFilename(for url: URL, mimeType: String?) -> String {
        let originalName = url.lastPathComponent
        let base = originalName.isEmpty || originalName == "/" ? "media" : originalName
        let cleanName = base.components(separatedBy: "?").first ?? "media"
        let hasExtension = !URL(fileURLWithPath: cleanName).pathExtension.isEmpty
        let extensionFromType: String
        switch mimeType?.lowercased() {
        case "video/mp4": extensionFromType = "mp4"
        case "image/jpeg": extensionFromType = "jpg"
        case "image/png": extensionFromType = "png"
        default: extensionFromType = "bin"
        }
        let stem = hasExtension ? URL(fileURLWithPath: cleanName).deletingPathExtension().lastPathComponent : cleanName
        let fileExtension = hasExtension ? URL(fileURLWithPath: cleanName).pathExtension : extensionFromType
        return "\(stem)-\(Int(Date().timeIntervalSince1970)).\(fileExtension)"
    }
}
