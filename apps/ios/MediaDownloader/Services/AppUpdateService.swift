import Foundation

struct AppUpdateResult {
    let currentVersion: String
    let latestVersion: String
    let releaseURL: URL
    let changelog: String

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
            return "暂未找到 iOS 版本。"
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

    private struct ChangelogDoc: Decodable {
        let versions: [ChangelogVersion]
    }

    private struct ChangelogVersion: Decodable {
        let version: String
        let date: String?
        let entries: [String: [String]]?
    }

    /// Fetch the shared changelog.json (one file for every client, generated from
    /// CHANGELOG.md) and return per-platform notes. Fail-open: (nil, "").
    static func fetchChangelog(platform: String, currentVersion: String, maxVersions: Int = 3) async -> (latest: String?, notes: String) {
        let sources = [
            "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/changelog.json",
            "https://gh-proxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/changelog.json",
            "https://ghproxy.net/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/changelog.json",
            "https://fastly.jsdelivr.net/gh/Francis-Xavier-code/tiktok-douyin-dl@main/changelog.json",
        ]

        for urlString in sources {
            guard let url = URL(string: urlString) else { continue }
            var request = URLRequest(url: url)
            request.setValue("MediaDownloader-iOS", forHTTPHeaderField: "User-Agent")
            request.timeoutInterval = 10
            guard let (data, response) = try? await URLSession.shared.data(for: request),
                  let http = response as? HTTPURLResponse,
                  (200...299).contains(http.statusCode),
                  let doc = try? JSONDecoder().decode(ChangelogDoc.self, from: data),
                  let first = doc.versions.first else { continue }

            var latest: String?
            var lines: [String] = []
            for v in doc.versions.prefix(maxVersions) {
                let version = v.version.hasPrefix("v") ? String(v.version.dropFirst()) : v.version
                if latest == nil { latest = version }
                if version.compare(currentVersion, options: .numeric) != .orderedDescending { continue }
                let entries = (v.entries?[platform] ?? []) + (v.entries?["all"] ?? [])
                guard !entries.isEmpty else { continue }
                var header = "v\(version)"
                if let date = v.date, !date.isEmpty { header += " (\(date))" }
                lines.append(header)
                for entry in entries { lines.append("  • \(entry)") }
                lines.append("")
            }
            return (latest, lines.joined(separator: "\n"))
        }
        return (nil, "")
    }

    static func checkForUpdates() async throws -> AppUpdateResult {
        let currentVersion = Bundle.main.object(
            forInfoDictionaryKey: "CFBundleShortVersionString"
        ) as? String ?? "0.0.0"

        // 1. Preferred: the shared changelog.json via raw-file mirrors. Works in
        //    China, no GitHub API rate limits, and gives the per-platform notes.
        //    Releases are tagged plain v* (e.g. v1.8.2), so the release URL is
        //    derived directly from the changelog's newest version.
        let (latestFromChangelog, notes) = await fetchChangelog(platform: "ios", currentVersion: currentVersion)
        if let latest = latestFromChangelog {
            let releaseURL = URL(
                string: "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/tag/v\(latest)"
            ) ?? URL(string: "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases")!
            return AppUpdateResult(
                currentVersion: currentVersion,
                latestVersion: latest,
                releaseURL: releaseURL,
                changelog: notes
            )
        }

        // 2. Fallback: GitHub API releases list (any v* tag).
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
                !$0.isDraft && !$0.isPrerelease && $0.tagName.hasPrefix("v")
            }) else {
                continue
            }

            let latestVersion = release.tagName.hasPrefix("v") ? String(release.tagName.dropFirst()) : release.tagName
            return AppUpdateResult(
                currentVersion: currentVersion,
                latestVersion: latestVersion,
                releaseURL: release.htmlURL,
                changelog: ""
            )
        }

        throw receivedValidReleaseList ? AppUpdateError.noIOSRelease : AppUpdateError.invalidResponse
    }
}
