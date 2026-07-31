import Observation
import SwiftUI

@main
struct MediaDownloaderApp: App {
    @State private var downloadStore = DownloadStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(downloadStore)
        }
    }
}
