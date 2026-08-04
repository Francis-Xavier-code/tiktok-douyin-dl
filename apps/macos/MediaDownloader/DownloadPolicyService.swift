import Foundation

// MARK: - Download gate result

/// Outcome of checking the remote download-policy before a download.
enum DownloadGate: Equatable {
    case allow
    case block(reason: String, message: String, issueURL: URL?)
}

// MARK: - Remote download-policy service (fail-closed)

/// Governs whether the *download feature* is currently enabled (e.g. temporary
/// maintenance, or a bad version to quarantine). Independent of version-policy,
/// which governs whether the client build itself is retired.
///
/// Per the maintainer's rule this is **fail-closed**: if every source (direct
/// GitHub + all mirrors) is unreachable, downloads are blocked and the user is
/// told to file an issue. A stale/garbled policy must never green-light downloads.
struct DownloadPolicyService {
    static let platform = "macos"
    static let currentVersion: String = {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0.0.0"
    }()

    private static let sources = [
        "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://gh-proxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://ghproxy.net/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://raw.gitmirror.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://kgithub.com/Francis-Xavier-code/tiktok-douyin-dl/raw/main/download-policy.json",
        "https://mirror.ghproxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://github.moeyy.xyz/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://ghproxy.1888866.xyz/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://gh.api.99988866.xyz/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://fastly.jsdelivr.net/gh/Francis-Xavier-code/tiktok-douyin-dl@main/download-policy.json",
    ]

    private static let issueURL = URL(string: "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/issues")

    static func fetchPolicy() async -> [String: Any]? {
        for urlString in sources {
            guard let url = URL(string: urlString) else { continue }
            var request = URLRequest(url: url)
            request.timeoutInterval = 4
            request.setValue("MediaDownloader-macOS", forHTTPHeaderField: "User-Agent")
            do {
                let (data, response) = try await URLSession.shared.data(for: request)
                if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
                    continue
                }
                if let dict = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    return dict
                }
            } catch {
                continue
            }
        }
        return nil
    }

    static func evaluate() async -> DownloadGate {
        guard let policy = await fetchPolicy() else {
            // Every source failed -> fail-closed.
            return .block(reason: "unreachable",
                          message: "无法连接下载策略服务（所有镜像均不可用），已暂停下载。如确认网络正常请前往仓库反馈。",
                          issueURL: issueURL)
        }
        guard let download = policy["download"] as? [String: Any] else {
            return .block(reason: "unreachable",
                          message: "下载策略文件格式异常，已暂停下载。",
                          issueURL: issueURL)
        }

        let enabled = (download["enabled"] as? Bool) ?? true
        let minVersion = (download["min_version"] as? String) ?? "0.0.0"
        let message = (download["message"] as? String)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let issue = (policy["issue_url"] as? String).flatMap { URL(string: $0) } ?? issueURL

        if !enabled {
            return .block(reason: "disabled",
                          message: message.isEmpty ? "维护者已临时关闭下载功能，请关注项目主页了解恢复时间。" : message,
                          issueURL: issue)
        }
        if compareVersions(currentVersion, minVersion) < 0 {
            return .block(reason: "version",
                          message: message.isEmpty ? "当前版本过低，下载功能已限制，请升级到最新版本。" : message,
                          issueURL: issue)
        }
        return .allow
    }

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
