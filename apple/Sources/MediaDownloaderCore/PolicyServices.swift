import CryptoKit
import Foundation

// MARK: - Shared result types

/// Result of evaluating this client against the remote version-policy.json.
/// Fail-open: any network/parse problem resolves to `.allow`.
public enum MediaPolicyStatus: Equatable {
    case allow
    case nag(message: String, updateURL: URL?)
    case block(message: String, updateURL: URL?)

    public var isBlock: Bool {
        if case .block = self { return true }
        return false
    }
}

/// Outcome of checking the remote download-policy before a download.
/// Fail-closed: any network/parse/signature problem resolves to `.block`.
public enum MediaDownloadGate: Equatable {
    case allow
    case block(reason: String, message: String, issueURL: URL?)
}

// MARK: - Ed25519 policy verification

/// Ed25519 signature verification for download-policy.json.

/// The canonical payload must stay byte-identical with the Android client
/// (PolicyVerifier.kt) and the Python core (core/policy_verifier.py):
///
///     updated_at
///     enabled      # "true" / "false"
///     message
///     min_version
///
/// Fail-closed: a missing or invalid signature means the policy is untrusted.
enum PolicySignatureVerifier {
    /// Public key (base64, 32 bytes) -- keep in sync with
    /// apps/android/app/src/main/java/com/douyindownload/PolicyVerifier.kt and
    /// python/src/media_downloader/core/policy_verifier.py
    private static let publicKeyB64 = "TfI3/szbWh13QZr/FunFipeal2vb+vkrYoazGJHf6iw="

    static func canonicalPayload(_ policy: [String: Any]) -> String {
        let download = policy["download"] as? [String: Any] ?? [:]
        let enabled: Bool
        if let value = download["enabled"] as? Bool {
            enabled = value
        } else if let value = download["enabled"] as? String {
            enabled = (value as NSString).boolValue
        } else {
            enabled = true
        }
        let updatedAt = policy["updated_at"] as? String ?? ""
        let message = download["message"] as? String ?? ""
        let minVersion = download["min_version"] as? String ?? "0.0.0"
        return [updatedAt, enabled ? "true" : "false", message, minVersion]
            .joined(separator: "\n")
    }

    /// Return true only when the policy carries a valid Ed25519 signature.
    static func verify(_ policy: [String: Any]) -> Bool {
        guard let signatureB64 = policy["signature"] as? String,
              !signatureB64.isEmpty,
              let keyData = Data(base64Encoded: publicKeyB64),
              let signatureData = Data(base64Encoded: signatureB64),
              let publicKey = try? Curve25519.Signing.PublicKey(rawRepresentation: keyData)
        else { return false }
        let payload = Data(canonicalPayload(policy).utf8)
        return publicKey.isValidSignature(signatureData, for: payload)
    }
}

// MARK: - Shared policy engine (one implementation for iOS + macOS)

/// Single remote-policy engine shared by the iOS and macOS apps.
///
/// Previously this logic was duplicated line-for-line in both Xcode projects;
/// platform-specific behavior is reduced to the `platform` key and the
/// `userAgent` string.
public struct MediaPolicyService {
    public let platform: String
    public let userAgent: String

    public init(platform: String, userAgent: String) {
        self.platform = platform
        self.userAgent = userAgent
    }

    private static let owner = "Francis-Xavier-code"
    private static let repo = "tiktok-douyin-dl"
    private static let defaultIssueURL = URL(string: "https://github.com/\(owner)/\(repo)/issues")!

    private var versionPolicyEndpoints: [String] {
        [
            "https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/version-policy.json",
            "https://gh-proxy.com/https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/version-policy.json",
            "https://ghproxy.net/https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/version-policy.json",
        ]
    }

    private var downloadPolicySources: [String] {
        [
            "https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/download-policy.json",
            "https://gh-proxy.com/https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/download-policy.json",
            "https://ghproxy.net/https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/download-policy.json",
            "https://raw.gitmirror.com/\(Self.owner)/\(Self.repo)/main/download-policy.json",
            "https://kgithub.com/\(Self.owner)/\(Self.repo)/raw/main/download-policy.json",
            "https://mirror.ghproxy.com/https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/download-policy.json",
            "https://github.moeyy.xyz/https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/download-policy.json",
            "https://ghproxy.1888866.xyz/https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/download-policy.json",
            "https://gh.api.99988866.xyz/https://raw.githubusercontent.com/\(Self.owner)/\(Self.repo)/main/download-policy.json",
            "https://fastly.jsdelivr.net/gh/\(Self.owner)/\(Self.repo)@main/download-policy.json",
        ]
    }

    // MARK: Version policy (fail-open + offline cache)

    private var cacheURL: URL? {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?
            .appendingPathComponent("tiktok-douyin-dl")
            .appendingPathComponent("version-policy.json")
    }

    private func writeCache(_ policy: [String: Any]) {
        guard let url = cacheURL else { return }
        do {
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(),
                                                    withIntermediateDirectories: true)
            let data = try JSONSerialization.data(withJSONObject: policy)
            try data.write(to: url)
        } catch {
            // Non-fatal: the cache is a best-effort enhancement.
        }
    }

    private func readCache() -> [String: Any]? {
        guard let url = cacheURL else { return nil }
        do {
            let data = try Data(contentsOf: url)
            return try JSONSerialization.jsonObject(with: data) as? [String: Any]
        } catch {
            return nil
        }
    }

    private func fetchJSON(_ urlString: String, timeout: TimeInterval) async -> [String: Any]? {
        guard let url = URL(string: urlString) else { return nil }
        var request = URLRequest(url: url)
        request.timeoutInterval = timeout
        request.setValue(userAgent, forHTTPHeaderField: "User-Agent")
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
                return nil
            }
            return try JSONSerialization.jsonObject(with: data) as? [String: Any]
        } catch {
            return nil
        }
    }

    private func fetchVersionPolicy() async -> [String: Any]? {
        for urlString in versionPolicyEndpoints {
            if let policy = await fetchJSON(urlString, timeout: 6) {
                writeCache(policy)
                return policy
            }
        }
        return readCache()
    }

    public func versionPolicyStatus() async -> MediaPolicyStatus {
        // Fail-open: any problem -> allow.
        guard let policy = await fetchVersionPolicy() else { return .allow }
        guard let platforms = policy["platforms"] as? [String: Any],
              let entry = platforms[platform] as? [String: Any] else { return .allow }
        let minVersion = (entry["min_version"] as? String) ?? "0.0.0"
        let hardBlock = (entry["hard_block"] as? Bool) ?? false
        guard let current = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String else {
            return .allow
        }
        if Self.compareVersions(current, minVersion) >= 0 { return .allow }

        let fallback = "你的版本已过时，请升级到最新版本。"
        let rawMessage = (policy["message"] as? String)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let message = rawMessage.isEmpty ? fallback : rawMessage
        let updateURL = (policy["update_url"] as? String).flatMap { URL(string: $0) }
        return hardBlock
            ? .block(message: message, updateURL: updateURL)
            : .nag(message: message, updateURL: updateURL)
    }

    // MARK: Download gate (fail-closed + Ed25519 signature)

    private func fetchDownloadPolicy() async -> [String: Any]? {
        for urlString in downloadPolicySources {
            if let policy = await fetchJSON(urlString, timeout: 4),
               PolicySignatureVerifier.verify(policy) {
                return policy
            }
        }
        return nil
    }

    public func downloadGate() async -> MediaDownloadGate {
        guard let policy = await fetchDownloadPolicy() else {
            // Every source failed or the signature was invalid -> fail-closed.
            return .block(reason: "unreachable",
                          message: "无法连接下载策略服务（所有镜像均不可用或策略校验失败），已暂停下载。如确认网络正常请前往仓库反馈。",
                          issueURL: Self.defaultIssueURL)
        }
        guard let download = policy["download"] as? [String: Any] else {
            return .block(reason: "unreachable",
                          message: "下载策略文件格式异常，已暂停下载。",
                          issueURL: Self.defaultIssueURL)
        }

        let enabled = (download["enabled"] as? Bool) ?? true
        let minVersion = (download["min_version"] as? String) ?? "0.0.0"
        let message = (download["message"] as? String)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let issue = (policy["issue_url"] as? String).flatMap { URL(string: $0) } ?? Self.defaultIssueURL
        guard let current = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String else {
            return .block(reason: "version", message: "无法读取当前版本，已暂停下载。", issueURL: issue)
        }

        if !enabled {
            return .block(reason: "disabled",
                          message: message.isEmpty ? "维护者已临时关闭下载功能，请关注项目主页了解恢复时间。" : message,
                          issueURL: issue)
        }
        if Self.compareVersions(current, minVersion) < 0 {
            return .block(reason: "version",
                          message: message.isEmpty ? "当前版本过低，下载功能已限制，请升级到最新版本。" : message,
                          issueURL: issue)
        }
        return .allow
    }

    // MARK: Version comparison (1 if a > b, 0 if equal, -1 if a < b)

    public static func compareVersions(_ a: String, _ b: String) -> Int {
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
