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

/// Thin iOS wrapper over the shared MediaDownloaderCore policy engine
/// (fetching, caching, evaluation and version comparison live there so the
/// iOS and macOS apps cannot drift).
struct VersionPolicyService {
    static let platform = "ios"

    static func evaluate() async -> PolicyStatus {
        let engine = MediaPolicyService(platform: platform, userAgent: "MediaDownloader-iOS")
        switch await engine.versionPolicyStatus() {
        case .allow:
            return .allow
        case .nag(let message, let url):
            return .nag(message: message, updateURL: url)
        case .block(let message, let url):
            return .block(message: message, updateURL: url)
        }
    }

    /// 1 if a > b, 0 if equal, -1 if a < b.
    static func compareVersions(_ a: String, _ b: String) -> Int {
        MediaPolicyService.compareVersions(a, b)
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

/// Full-screen replacement shown when the version is hard-blocked.
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
