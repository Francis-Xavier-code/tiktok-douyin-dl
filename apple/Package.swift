// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "MediaDownloaderCore",
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .library(name: "MediaDownloaderCore", targets: ["MediaDownloaderCore"]),
    ],
    targets: [
        .target(name: "MediaDownloaderCore"),
    ]
)
