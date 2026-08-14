cask "tiktok-douyin-dl" do
  version "2.0.1"
  sha256 "ad66a27ed1f362dc71b844c134a9848270d948b14f444dadd97576ede27f1f4e"

  url "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/download/v#{version}/MediaDownloader-macOS-#{version}-unsigned.dmg"
  name "MediaDownloader"
  desc "TikTok & Douyin no-watermark downloader for macOS"
  homepage "https://github.com/Francis-Xavier-code/tiktok-douyin-dl"

  livecheck do
    url :url
    strategy :github_latest
  end

  postflight do
    system_command "xattr",
                   args: ["-dr", "com.apple.quarantine", "#{appdir}/MediaDownloader.app"]
  end

  app "MediaDownloader.app"

  caveats do
    <<~EOS
      This build is ad-hoc signed and NOT notarized by Apple.
      Distributed through the custom tap only (official homebrew-cask
      requires Apple Developer ID signing). The Gatekeeper quarantine
      attribute is removed automatically after install, so the app
      opens without approval prompts.
    EOS
  end

  zap trash: [
    "~/Documents/MediaDownloader",
  ]
end
