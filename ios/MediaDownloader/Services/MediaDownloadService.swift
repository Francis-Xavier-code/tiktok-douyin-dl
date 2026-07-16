import Foundation

enum MediaDownloadError: LocalizedError {
    case noURLFound
    case notDirectMedia(URL)
    case invalidResponse
    case httpStatus(Int)
    case unexpectedContentType(String)

    var errorDescription: String? {
        switch self {
        case .noURLFound:
            "没有在分享文本中找到链接。"
        case .notDirectMedia:
            "这不是可直接下载的媒体链接。请在“Web 下载”中配置并使用本仓库的 Docker WebUI。"
        case .invalidResponse:
            "服务器没有返回可下载的媒体文件。"
        case .httpStatus(let statusCode):
            "媒体服务器拒绝了下载请求（HTTP \(statusCode)）。"
        case .unexpectedContentType(let mimeType):
            "服务器返回的不是媒体文件（\(mimeType)）。"
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
    static func downloadDirectMedia(from sourceURL: URL) async throws -> [URL] {
        let host = sourceURL.host?.lowercased() ?? ""
        let isShareLink = host.contains("douyin.com") || host.contains("tiktok.com")

        if isShareLink {
            let directURLs = try await NativeMediaScraper.shared.scrape(url: sourceURL)
            guard !directURLs.isEmpty else {
                throw MediaDownloadError.invalidResponse
            }

            // WKWebView and URLSession do not share cookies automatically. Seed one
            // reusable session with the browser cookies and keep it for redirects
            // and every CDN request in this download.
            let browserCookies = await NativeMediaScraper.shared.browserCookies()
            let session = makeSession(cookies: browserCookies)
            var savedURLs: [URL] = []
            for directURL in directURLs {
                let savedURL = try await downloadAndSave(
                    directURL: directURL,
                    sourceURL: sourceURL,
                    session: session
                )
                savedURLs.append(savedURL)
            }
            guard !savedURLs.isEmpty else {
                throw MediaDownloadError.invalidResponse
            }
            return savedURLs
        } else {
            let session = makeSession(cookies: [])
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

            let savedURL = try await downloadAndSave(
                directURL: resolvedURL,
                sourceURL: sourceURL,
                session: session
            )
            return [savedURL]
        }
    }

    private static func makeSession(cookies: [HTTPCookie]) -> URLSession {
        let cookieStorage = HTTPCookieStorage.shared
        for cookie in cookies {
            cookieStorage.setCookie(cookie)
        }

        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpShouldSetCookies = true
        configuration.httpCookieAcceptPolicy = .always
        configuration.httpCookieStorage = cookieStorage
        configuration.timeoutIntervalForRequest = 60
        configuration.timeoutIntervalForResource = 180
        return URLSession(configuration: configuration)
    }

    private static func downloadAndSave(
        directURL: URL,
        sourceURL: URL,
        session: URLSession
    ) async throws -> URL {
        var request = URLRequest(url: directURL)
        request.setValue(MediaBrowserIdentity.mobileUserAgent, forHTTPHeaderField: "User-Agent")
        request.setValue("*/*", forHTTPHeaderField: "Accept")
        request.setValue("zh-CN,zh;q=0.9,en;q=0.8", forHTTPHeaderField: "Accept-Language")

        let sourceHost = sourceURL.host?.lowercased() ?? ""
        if sourceHost.contains("douyin.com") {
            request.setValue("https://www.douyin.com/", forHTTPHeaderField: "Referer")
        } else if sourceHost.contains("tiktok.com") {
            request.setValue("https://www.tiktok.com/", forHTTPHeaderField: "Referer")
        }

        print("[MediaDownloadService] requesting \(directURL.host ?? "unknown host")\(directURL.path)")
        let (temporaryURL, downloadResponse) = try await session.download(for: request)
        guard let downloadResponse = downloadResponse as? HTTPURLResponse else {
            throw MediaDownloadError.invalidResponse
        }
        guard (200...299).contains(downloadResponse.statusCode) else {
            print("[MediaDownloadService] download HTTP \(downloadResponse.statusCode)")
            throw MediaDownloadError.httpStatus(downloadResponse.statusCode)
        }

        let finalURL = downloadResponse.url ?? directURL
        let mimeType = downloadResponse.mimeType?.lowercased() ?? "unknown"
        guard isMedia(url: finalURL, mimeType: mimeType) else {
            print("[MediaDownloadService] unexpected MIME \(mimeType), final URL: \(finalURL.host ?? "unknown")\(finalURL.path)")
            throw MediaDownloadError.unexpectedContentType(mimeType)
        }

        print("[MediaDownloadService] download resolved to \(finalURL.host ?? "unknown host")\(finalURL.path), MIME \(mimeType)")
        let destinationDirectory = try documentsDirectory()
        let filename = uniqueFilename(for: finalURL, mimeType: downloadResponse.mimeType)
        let destinationURL = destinationDirectory.appendingPathComponent(filename)

        if FileManager.default.fileExists(atPath: destinationURL.path) {
            try? FileManager.default.removeItem(at: destinationURL)
        }

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
        let extensionFromType: String
        switch mimeType?.lowercased() {
        case "video/mp4": extensionFromType = "mp4"
        case "image/jpeg": extensionFromType = "jpg"
        case "image/png": extensionFromType = "png"
        default:
            let ext = url.pathExtension.lowercased()
            extensionFromType = ext.isEmpty ? "bin" : ext
        }

        let ext = extensionFromType
        let prefix = ["jpg", "jpeg", "png", "webp", "gif"].contains(ext) ? "image" : "video"

        let nextIdx = nextMediaIndex()
        return "[\(nextIdx)]\(prefix).\(ext)"
    }

    private static func nextMediaIndex() -> Int {
        do {
            let directory = try documentsDirectory()
            let files = try FileManager.default.contentsOfDirectory(
                at: directory,
                includingPropertiesForKeys: nil
            )
            let regex = try NSRegularExpression(
                pattern: #"^\[(\d+)\](?:image|video)\.\w+$"#,
                options: .caseInsensitive
            )

            let maxIndex = files.compactMap { fileURL -> Int? in
                let name = fileURL.lastPathComponent
                let range = NSRange(name.startIndex..., in: name)
                guard let match = regex.firstMatch(in: name, range: range),
                      let numberRange = Range(match.range(at: 1), in: name) else {
                    return nil
                }
                return Int(name[numberRange])
            }.max() ?? 0

            return maxIndex + 1
        } catch {
            print("Failed to scan directory for index: \(error)")
            return 1
        }
    }
}
