import Foundation

struct AppUpdateResult {
    let currentVersion: String
    let latestVersion: String
    let releaseURL: URL

    var isUpdateAvailable: Bool {
        latestVersion.compare(currentVersion, options: .numeric) == .orderedDescending
    }
}

enum AppUpdateError: LocalizedError {
    case invalidResponse
    case noIOSRelease

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "GitHub 没有返回有效的版本信息。"
        case .noIOSRelease:
            return "暂未找到 iOS 版本。发布时请使用 ios-v1.8.1 这样的标签。"
        }
    }
}

enum AppUpdateService {
    private struct GitHubRelease: Decodable {
        let tagName: String
        let htmlURL: URL
        let isDraft: Bool
        let isPrerelease: Bool

        enum CodingKeys: String, CodingKey {
            case tagName = "tag_name"
            case htmlURL = "html_url"
            case isDraft = "draft"
            case isPrerelease = "prerelease"
        }
    }

    static func checkForUpdates() async throws -> AppUpdateResult {
        let endpoints = [
            "https://api.github.com/repos/Francis-Xavier-code/tiktok-douyin-dl/releases?per_page=30",
            "https://gh-proxy.org/https://api.github.com/repos/Francis-Xavier-code/tiktok-douyin-dl/releases?per_page=30"
        ].compactMap(URL.init(string:))

        var receivedValidReleaseList = false
        for endpoint in endpoints {
            var request = URLRequest(url: endpoint)
            request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
            request.setValue("MediaDownloader-iOS", forHTTPHeaderField: "User-Agent")
            request.timeoutInterval = 15

            guard let (data, response) = try? await URLSession.shared.data(for: request),
                  let response = response as? HTTPURLResponse,
                  (200...299).contains(response.statusCode),
                  let releases = try? JSONDecoder().decode([GitHubRelease].self, from: data) else {
                continue
            }

            receivedValidReleaseList = true
            guard let release = releases.first(where: {
                !$0.isDraft && !$0.isPrerelease && $0.tagName.lowercased().hasPrefix("ios-v")
            }) else {
                continue
            }

            return makeResult(for: release)
        }

        throw receivedValidReleaseList ? AppUpdateError.noIOSRelease : AppUpdateError.invalidResponse
    }

    private static func makeResult(for release: GitHubRelease) -> AppUpdateResult {
        let currentVersion = Bundle.main.object(
            forInfoDictionaryKey: "CFBundleShortVersionString"
        ) as? String ?? "1.8.2"
        let latestVersion = String(release.tagName.dropFirst("ios-v".count))

        return AppUpdateResult(
            currentVersion: currentVersion,
            latestVersion: latestVersion,
            releaseURL: release.htmlURL
        )
    }
}
