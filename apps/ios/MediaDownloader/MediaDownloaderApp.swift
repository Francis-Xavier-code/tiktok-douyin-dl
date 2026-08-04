import Observation
import SwiftUI

@main
struct MediaDownloaderApp: App {
    @State private var downloadStore = DownloadStore()
    @State private var policy: PolicyStatus = .allow

    var body: some Scene {
        WindowGroup {
            Group {
                switch policy {
                case .allow:
                    ContentView()
                        .environment(downloadStore)
                case .nag(let message, let url):
                    ContentView()
                        .environment(downloadStore)
                        .overlay(alignment: .top) {
                            PolicyBanner(message: message, url: url)
                        }
                case .block(let message, let url):
                    PolicyBlockView(message: message, url: url)
                }
            }
            .task { policy = await VersionPolicyService.evaluate() }
        }
    }
}
