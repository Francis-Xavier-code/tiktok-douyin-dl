import Foundation

// MARK: - Download gate result

/// Outcome of checking the remote download-policy before a download.
enum DownloadGate: Equatable {
    case allow
    case block(reason: String, message: String, issueURL: URL?)
}

// MARK: - Remote download-policy service (fail-closed)

/// Thin macOS wrapper over the shared MediaDownloaderCore policy engine.
/// The shared engine enforces the Ed25519 signature gate (same public key as
/// Android / CLI / Windows GUI): unsigned or tampered policies are rejected.
struct DownloadPolicyService {
    static let platform = "macos"

    static func evaluate() async -> DownloadGate {
        let engine = MediaPolicyService(platform: platform, userAgent: "MediaDownloader-macOS")
        switch await engine.downloadGate() {
        case .allow:
            return .allow
        case .block(let reason, let message, let url):
            return .block(reason: reason, message: message, issueURL: url)
        }
    }

    /// 1 if a > b, 0 if equal, -1 if a < b.
    static func compareVersions(_ a: String, _ b: String) -> Int {
        MediaPolicyService.compareVersions(a, b)
    }
}
