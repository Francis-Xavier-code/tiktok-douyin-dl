import AppKit
import Foundation

// MARK: - Update result

struct AppUpdateResult {
    let currentVersion: String
    let latestVersion: String
    let releaseURL: URL
    let dmgURL: URL?

    var isUpdateAvailable: Bool {
        latestVersion.compare(currentVersion, options: .numeric) == .orderedDescending
    }
}

// MARK: - Errors

enum AppUpdateError: LocalizedError {
    case invalidResponse
    case noMacOSRelease
    case downloadFailed(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "GitHub 没有返回有效的版本信息。"
        case .noMacOSRelease:
            return "暂未找到 macOS 版本。"
        case .downloadFailed(let reason):
            return "下载更新包失败：\(reason)"
        }
    }
}

// MARK: - App update service

enum AppUpdateService {
    private struct GitHubRelease: Decodable {
        let tagName: String
        let htmlURL: URL
        let isDraft: Bool
        let isPrerelease: Bool
        let assets: [GitHubAsset]

        enum CodingKeys: String, CodingKey {
            case tagName = "tag_name"
            case htmlURL = "html_url"
            case isDraft = "draft"
            case isPrerelease = "prerelease"
            case assets
        }
    }

    private struct GitHubAsset: Decodable {
        let name: String
        let browserDownloadURL: URL

        enum CodingKeys: String, CodingKey {
            case name
            case browserDownloadURL = "browser_download_url"
        }
    }

    static func checkForUpdates() async throws -> AppUpdateResult {
        let endpoints = [
            "https://api.github.com/repos/Francis-Xavier-code/tiktok-douyin-dl/releases?per_page=10",
            "https://gh-proxy.com/https://api.github.com/repos/Francis-Xavier-code/tiktok-douyin-dl/releases?per_page=10"
        ].compactMap(URL.init(string:))

        var receivedValidReleaseList = false
        for endpoint in endpoints {
            var request = URLRequest(url: endpoint)
            request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
            request.setValue("MediaDownloader-macOS", forHTTPHeaderField: "User-Agent")
            request.timeoutInterval = 15

            guard let (data, response) = try? await URLSession.shared.data(for: request),
                  let httpResponse = response as? HTTPURLResponse,
                  (200...299).contains(httpResponse.statusCode),
                  let releases = try? JSONDecoder().decode([GitHubRelease].self, from: data) else {
                continue
            }

            receivedValidReleaseList = true
            guard let release = releases.first(where: {
                !$0.isDraft && !$0.isPrerelease && $0.tagName.hasPrefix("v")
            }) else {
                continue
            }

            return makeResult(for: release)
        }

        throw receivedValidReleaseList ? AppUpdateError.noMacOSRelease : AppUpdateError.invalidResponse
    }

    private static func makeResult(for release: GitHubRelease) -> AppUpdateResult {
        let currentVersion = Bundle.main.object(
            forInfoDictionaryKey: "CFBundleShortVersionString"
        ) as? String ?? "1.8.1"
        let latestVersion = release.tagName.hasPrefix("v") ? String(release.tagName.dropFirst(1)) : release.tagName

        // Find the unsigned DMG asset.
        let dmgURL = release.assets.first(where: { $0.name.contains("macOS") && $0.name.hasSuffix(".dmg") })?.browserDownloadURL

        return AppUpdateResult(
            currentVersion: currentVersion,
            latestVersion: latestVersion,
            releaseURL: release.htmlURL,
            dmgURL: dmgURL
        )
    }

    /// Download the DMG to a temp directory and open it so the user can install.
    static func downloadAndOpenDMG(from url: URL) async throws {
        let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent("MediaDownloader-update")
        try? FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        let dmgPath = tempDir.appendingPathComponent(url.lastPathComponent)

        // Try multiple download sources (mirror fallback).
        let rawURLString = url.absoluteString
        let mirrorPrefixes = [
            "",
            "https://gh-proxy.com/",
            "https://ghproxy.net/",
        ]

        var downloaded = false
        var lastError: Error?

        for prefix in mirrorPrefixes {
            let urlString: String
            if prefix.isEmpty {
                urlString = rawURLString
            } else if rawURLString.hasPrefix("https://github.com/") {
                urlString = prefix + rawURLString
            } else {
                continue
            }

            guard let mirrorURL = URL(string: urlString) else { continue }

            do {
                var request = URLRequest(url: mirrorURL)
                request.setValue("MediaDownloader-macOS", forHTTPHeaderField: "User-Agent")
                request.timeoutInterval = 120
                let (data, response) = try await URLSession.shared.data(for: request)
                if let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) {
                    try data.write(to: dmgPath)
                    downloaded = true
                    break
                }
            } catch {
                lastError = error
                continue
            }
        }

        guard downloaded else {
            throw AppUpdateError.downloadFailed(lastError?.localizedDescription ?? "所有下载源均失败")
        }

        // Open the DMG; macOS will mount it and show a Finder window.
        await MainActor.run {
            NSWorkspace.shared.open(dmgPath)
        }
    }
}
