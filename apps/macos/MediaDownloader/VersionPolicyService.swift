import Foundation
import SwiftUI

// MARK: - Policy status

/// Result of evaluating this client against the remote version-policy.json.
/// Fail-open: any network/parse problem resolves to `.allow`.
enum PolicyStatus: Equatable {
    case allow
    case nag(message: String, updateURL: URL?)
    case block(message: String, updateURL: URL?)

    var isBlock: Bool {
        if case .block = self { return true }
        return false
    }
}

// MARK: - Remote version-policy service (fail-open)

/// Lets the maintainer retire old builds WITHOUT re-shipping every binary:
/// a single version-policy.json on the default branch declares the minimum
/// allowed version per platform and whether a violation is a hard block
/// (refuse to run) or a soft nag (warn, but keep working). See docs/version-policy.md.
struct VersionPolicyService {
    static let platform = "macos"
    static let currentVersion: String = {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0.0.0"
    }()

    private static let endpoints = [
        "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
        "https://gh-proxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
        "https://ghproxy.net/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json"
    ]

    static func fetchPolicy() async -> [String: Any]? {
        for urlString in endpoints {
            guard let url = URL(string: urlString) else { continue }
            var request = URLRequest(url: url)
            request.timeoutInterval = 6
            request.setValue("MediaDownloader-macOS", forHTTPHeaderField: "User-Agent")
            do {
                let (data, response) = try await URLSession.shared.data(for: request)
                if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
                    continue
                }
                if let dict = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    writeCache(dict)
                    return dict
                }
            } catch {
                continue
            }
        }
        return readCache()
    }

    // MARK: Local cache (so a hard block still applies offline)

    private static var cacheURL: URL? {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?
            .appendingPathComponent("tiktok-douyin-dl")
            .appendingPathComponent("version-policy.json")
    }

    private static func writeCache(_ policy: [String: Any]) {
        guard let url = cacheURL else { return }
        do {
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(),
                                                    withIntermediateDirectories: true)
            let data = try JSONSerialization.data(withJSONObject: policy)
            try data.write(to: url)
        } catch {
            // Non-fatal: cache is a best-effort enhancement.
        }
    }

    private static func readCache() -> [String: Any]? {
        guard let url = cacheURL else { return nil }
        do {
            let data = try Data(contentsOf: url)
            return try JSONSerialization.jsonObject(with: data) as? [String: Any]
        } catch {
            return nil
        }
    }

    static func evaluate() async -> PolicyStatus {
        // Fail-open: any problem -> allow.
        guard let policy = await fetchPolicy() else { return .allow }
        guard let platforms = policy["platforms"] as? [String: Any],
              let entry = platforms[platform] as? [String: Any] else { return .allow }
        let minVersion = (entry["min_version"] as? String) ?? "0.0.0"
        let hardBlock = (entry["hard_block"] as? Bool) ?? false
        if compareVersions(currentVersion, minVersion) >= 0 { return .allow }

        let fallback = "你的版本已过时，请升级到最新版本。"
        let rawMessage = (policy["message"] as? String)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let message = rawMessage.isEmpty ? fallback : rawMessage
        let updateURL = (policy["update_url"] as? String).flatMap { URL(string: $0) }
        return hardBlock
            ? .block(message: message, updateURL: updateURL)
            : .nag(message: message, updateURL: updateURL)
    }

    /// 1 if a > b, 0 if equal, -1 if a < b.
    static func compareVersions(_ a: String, _ b: String) -> Int {
        let pa = a.components(separatedBy: ".").compactMap { Int($0) }
        let pb = b.components(separatedBy: ".").compactMap { Int($0) }
        let count = max(pa.count, pb.count)
        for i in 0..<count {
            let x = i < pa.count ? pa[i] : 0
            let y = i < pb.count ? pb[i] : 0
            if x != y { return x > y ? 1 : -1 }
        }
        return 0
    }
}

// MARK: - UI

/// Soft-nag banner. Tapping the X dismisses it for the session.
struct PolicyBanner: View {
    let message: String
    let url: URL?
    @State private var dismissed = false

    var body: some View {
        if !dismissed {
            HStack(spacing: 10) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                Text(message)
                    .font(.footnote)
                    .fixedSize(horizontal: false, vertical: true)
                if let url {
                    Link("更新", destination: url)
                        .font(.footnote.bold())
                }
                Spacer(minLength: 0)
                Button { dismissed = true } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(.orange.opacity(0.15))
        }
    }
}

/// Full replacement shown when the version is hard-blocked.
struct PolicyBlockView: View {
    let message: String
    let url: URL?

    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: "nosign")
                .font(.system(size: 48))
                .foregroundStyle(.red)
            Text("当前版本已停止支持")
                .font(.title2.bold())
            Text(message)
                .font(.body)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 320)
            if let url {
                Link("前往下载最新版本", destination: url)
                    .font(.headline)
            }
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
