import SwiftUI

@main
struct MediaDownloaderApp: App {
    @State private var controller = DownloadController()

    var body: some Scene {
        WindowGroup(id: "main") {
            ContentView(controller: controller)
        }
        .windowResizability(.contentSize)
        .commands {
            DownloadCommands(controller: controller)
        }

        MenuBarExtra {
            MenuBarView(controller: controller)
        } label: {
            Label(
                "MediaDownloader",
                systemImage: controller.isDownloading ? "arrow.down.circle.fill" : "arrow.down.circle"
            )
        }
        .menuBarExtraStyle(.window)
    }
}
