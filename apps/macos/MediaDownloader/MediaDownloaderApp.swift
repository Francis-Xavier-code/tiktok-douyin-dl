import SwiftUI

@main
struct MediaDownloaderApp: App {
    @State private var controller = DownloadController()

    var body: some Scene {
        WindowGroup(id: "main") {
            ContentView(controller: controller)
                .task { Task { await controller.refreshPolicy() } }
        }
        .windowResizability(.contentSize)
        .commands {
            DownloadCommands(controller: controller)
        }

        MenuBarExtra {
            MenuBarView(controller: controller)
                .task { Task { await controller.refreshPolicy() } }
        } label: {
            Label(
                "MediaDownloader",
                systemImage: controller.isDownloading ? "arrow.down.circle.fill" : "arrow.down.circle"
            )
        }
        .menuBarExtraStyle(.window)
    }
}
