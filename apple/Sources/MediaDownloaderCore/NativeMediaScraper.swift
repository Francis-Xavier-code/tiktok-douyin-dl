import Foundation
import WebKit

enum MediaBrowserIdentity {
    static let mobileUserAgent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    static let desktopUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@MainActor
class NativeMediaScraper: NSObject, WKNavigationDelegate {
    static let shared = NativeMediaScraper()

    private var webView: WKWebView?
    private var continuation: CheckedContinuation<[URL], Error>?
    private var timer: Timer?
    private var timeoutTask: Task<Void, Never>?
    private var processRestartCount = 0

    override init() {
        super.init()
    }

    func scrape(url: URL) async throws -> [URL] {
        cleanup()

        return try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            self.processRestartCount = 0

            let config = WKWebViewConfiguration()
            config.websiteDataStore = .default()
            config.preferences.javaScriptCanOpenWindowsAutomatically = false

            // applicationNameForUserAgent appends a token to the system UA. A full
            // UA there creates a malformed doubled value, so set it directly.
            let webView = WKWebView(frame: CGRect(x: 0, y: 0, width: 1, height: 1), configuration: config)
            webView.customUserAgent = MediaBrowserIdentity.mobileUserAgent
            webView.navigationDelegate = self
            webView.configuration.mediaTypesRequiringUserActionForPlayback = .all

            self.webView = webView

            self.timeoutTask = Task {
                try? await Task.sleep(nanoseconds: 20_000_000_000)
                guard !Task.isCancelled else { return }
                await MainActor.run {
                    if self.continuation != nil {
                        self.continuation?.resume(throwing: NSError(domain: "NativeMediaScraper", code: 408, userInfo: [NSLocalizedDescriptionKey: "解析超时，请重试。"]))
                        self.cleanup()
                    }
                }
            }

            var request = URLRequest(url: url)
            request.setValue(MediaBrowserIdentity.mobileUserAgent, forHTTPHeaderField: "User-Agent")
            request.setValue("zh-CN,zh;q=0.9,en;q=0.8", forHTTPHeaderField: "Accept-Language")
            print("[NativeMediaScraper] loading \(url.absoluteString)")
            webView.load(request)
        }
    }

    func browserCookies() async -> [HTTPCookie] {
        await withCheckedContinuation { continuation in
            WKWebsiteDataStore.default().httpCookieStore.getAllCookies { cookies in
                continuation.resume(returning: cookies)
            }
        }
    }

    private func cleanup() {
        timeoutTask?.cancel()
        timeoutTask = nil
        timer?.invalidate()
        timer = nil
        webView?.stopLoading()
        webView = nil
        continuation = nil
    }

    // WKNavigationDelegate
    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        guard let url = navigationAction.request.url,
              let scheme = url.scheme?.lowercased() else {
            decisionHandler(.cancel)
            return
        }

        switch scheme {
        case "http", "https", "about":
            decisionHandler(.allow)
        default:
            // Douyin's mobile page tries to launch the native app with schemes
            // such as snssdk1128:// or aweme://. A hidden scraper must never
            // hand those URLs to Launch Services on macOS.
            print("[NativeMediaScraper] blocked external navigation scheme: \(scheme)")
            decisionHandler(.cancel)
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        print("[NativeMediaScraper] navigation finished: \(webView.url?.absoluteString ?? "unknown")")
        timer?.invalidate()
        var attempts = 0
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] timer in
            guard let self = self else { return }
            Task { @MainActor in
                attempts += 1
                if attempts > 10 { // Max 10 seconds post-finish
                    self.timer?.invalidate()
                    self.timer = nil
                    self.extractResult()
                    return
                }

                let didSucceed = await self.tryExtract()
                if didSucceed {
                    self.timer?.invalidate()
                    self.timer = nil
                }
            }
        }
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        if isCancelledNavigation(error) {
            print("[NativeMediaScraper] ignored cancelled navigation")
            return
        }
        print("[NativeMediaScraper] navigation failed: \(error.localizedDescription)")
        continuation?.resume(throwing: error)
        cleanup()
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        if isCancelledNavigation(error) {
            print("[NativeMediaScraper] ignored cancelled provisional navigation")
            return
        }
        print("[NativeMediaScraper] provisional navigation failed: \(error.localizedDescription)")
        continuation?.resume(throwing: error)
        cleanup()
    }

    private func isCancelledNavigation(_ error: Error) -> Bool {
        let error = error as NSError
        return error.domain == NSURLErrorDomain && error.code == NSURLErrorCancelled
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        guard continuation != nil else { return }
        print("[NativeMediaScraper] WebContent process terminated")

        if processRestartCount == 0 {
            processRestartCount += 1
            webView.reload()
        } else {
            continuation?.resume(throwing: NSError(
                domain: "NativeMediaScraper",
                code: 503,
                userInfo: [NSLocalizedDescriptionKey: "网页解析进程已退出，请重新尝试。"]
            ))
            cleanup()
        }
    }

    private func tryExtract() async -> Bool {
        guard let webView = webView else { return false }

        let js = """
        (function() {
            var result = { platform: null, jsonText: null, directVideoSrc: null, pageURL: location.href };
            var douyinEl = document.getElementById('RENDER_DATA');
            var douyinText = douyinEl ? (douyinEl.textContent || douyinEl.innerText) : null;
            if (douyinText) {
                result.platform = 'douyin';
                result.jsonText = douyinText;
                return JSON.stringify(result);
            }
            var tiktokEl = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
            var tiktokText = tiktokEl ? (tiktokEl.textContent || tiktokEl.innerText) : null;
            if (tiktokText) {
                result.platform = 'tiktok';
                result.jsonText = tiktokText;
                return JSON.stringify(result);
            }
            var sigiEl = document.getElementById('SIGI_STATE');
            var sigiText = sigiEl ? (sigiEl.textContent || sigiEl.innerText) : null;
            if (sigiText) {
                result.platform = 'tiktok';
                result.jsonText = sigiText;
                return JSON.stringify(result);
            }
            var scripts = document.getElementsByTagName('script');
            for (var i = 0; i < scripts.length; i++) {
                var text = scripts[i].textContent || scripts[i].innerText || "";
                if (text.indexOf('_ROUTER_DATA') !== -1) {
                    var match = text.match(/_ROUTER_DATA\\s*=\\s*([\\s\\S]*?)\\s*;?\\s*$/);
                    if (match && match[1]) {
                        result.platform = 'douyin';
                        result.jsonText = match[1];
                        return JSON.stringify(result);
                    }
                }
            }
            var videoEl = document.querySelector('video');
            if (videoEl && videoEl.src && videoEl.src.indexOf('blob:') === -1) {
                result.platform = 'direct';
                result.directVideoSrc = videoEl.src;
                return JSON.stringify(result);
            }
            return null;
        })()
        """

        do {
            if let jsResult = try await webView.evaluateJavaScript(js) as? String,
               let data = jsResult.data(using: .utf8),
               let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {

                let platform = json["platform"] as? String
                let jsonText = json["jsonText"] as? String
                let directVideoSrc = json["directVideoSrc"] as? String
                let pageURL = (json["pageURL"] as? String).flatMap { URL(string: $0) }

                if let jsonText = jsonText, let parsedURLs = await parseJSONMetadata(jsonText, platform: platform) {
                    print("[NativeMediaScraper] extracted \(parsedURLs.count) structured media URL(s) for \(platform ?? "unknown")")
                    continuation?.resume(returning: parsedURLs)
                    cleanup()
                    return true
                }

                // The Douyin state schema changes frequently. If the page itself
                // has already redirected to a video/note URL, the aweme ID is a
                // sufficient no-watermark fallback even when JSON traversal fails.
                if let pageURL,
                   isDouyinURL(pageURL),
                   let awemeID = douyinAwemeID(from: pageURL),
                   let mediaURL = await douyinNoWatermarkURL(awemeID: awemeID) {
                    print("[NativeMediaScraper] resolved Douyin no-watermark URL from final page URL")
                    continuation?.resume(returning: [mediaURL])
                    cleanup()
                    return true
                }

                if platform == "direct", let pageURL {
                    // A platform page's <video> element is a playback stream and
                    // frequently points at the watermarked variant. For Douyin,
                    // resolve the post's actual video ID and rebuild its /play/
                    // endpoint. For TikTok, wait for structured page metadata
                    // instead of persisting the playback stream.
                    if !isPlatformURL(pageURL),
                       let directSrc = directVideoSrc,
                       let mediaURL = URL(string: directSrc) {
                        continuation?.resume(returning: [mediaURL])
                        cleanup()
                        return true
                    }
                }
            }
        } catch {
            // Ignore JS error and retry
        }
        return false
    }

    private func extractResult() {
        Task { @MainActor in
            let didSucceed = await tryExtract()
            if !didSucceed {
                continuation?.resume(throwing: NSError(domain: "NativeMediaScraper", code: 404, userInfo: [NSLocalizedDescriptionKey: "无法从页面中提取媒体链接。请确认链接有效。"]))
                cleanup()
            }
        }
    }

    private func parseJSONMetadata(_ jsonText: String, platform: String?) async -> [URL]? {
        let candidates = [jsonText, jsonText.removingPercentEncoding].compactMap { $0 }

        for candidate in candidates {
            guard let data = candidate.data(using: .utf8) else { continue }
            do {
                let decoded = try JSONSerialization.jsonObject(with: data)

                if platform == "douyin" {
                    if let dict = decoded as? [String: Any], let aweme = findDouyinAweme(dict) {
                        return await extractDouyinMediaURLs(aweme)
                    }
                } else if platform == "tiktok" {
                    if let dict = decoded as? [String: Any], let item = findTikTokItem(dict) {
                        return extractTikTokMediaURLs(item)
                    }
                }
            } catch {
                continue
            }
        }
        print("[NativeMediaScraper] structured metadata was present but could not be decoded")
        return nil
    }

    private func findDouyinAweme(_ dict: [String: Any]) -> [String: Any]? {
        if let aweme = dict["aweme"] as? [String: Any] { return aweme }
        if let awemeDetail = dict["awemeDetail"] as? [String: Any] { return awemeDetail }
        if let awemeDetail = dict["aweme_detail"] as? [String: Any] { return awemeDetail }
        if let detail = dict["detail"] as? [String: Any], detail["awemeId"] != nil { return detail }
        if let itemList = dict["item_list"] as? [[String: Any]], let first = itemList.first { return first }
        if let itemList = dict["itemList"] as? [[String: Any]], let first = itemList.first { return first }

        for (_, value) in dict {
            if let subDict = value as? [String: Any] {
                if let result = findDouyinAweme(subDict) { return result }
            } else if let array = value as? [[String: Any]] {
                for item in array {
                    if let result = findDouyinAweme(item) { return result }
                }
            }
        }
        return nil
    }

    private func getDouyinVidFromIes(awemeId: String) async -> String? {
        let apiUrl = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids=\(awemeId)"
        guard let url = URL(string: apiUrl) else { return nil }

        var request = URLRequest(url: url)
        request.setValue(MediaBrowserIdentity.desktopUserAgent, forHTTPHeaderField: "User-Agent")
        request.setValue("https://www.douyin.com/", forHTTPHeaderField: "Referer")
        request.setValue("application/json,text/plain,*/*", forHTTPHeaderField: "Accept")
        request.setValue("zh-CN,zh;q=0.9,en;q=0.8", forHTTPHeaderField: "Accept-Language")

        let cookies = await browserCookies()
        if let cookieHeader = cookieHeader(for: url, cookies: cookies) {
            request.setValue(cookieHeader, forHTTPHeaderField: "Cookie")
        }

        do {
            let configuration = URLSessionConfiguration.ephemeral
            configuration.timeoutIntervalForRequest = 15
            let session = URLSession(configuration: configuration)
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                print("[NativeMediaScraper] iesdouyin returned a non-HTTP response")
                return nil
            }
            guard (200...299).contains(httpResponse.statusCode) else {
                print("[NativeMediaScraper] iesdouyin HTTP \(httpResponse.statusCode)")
                return nil
            }
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let itemList = json["item_list"] as? [[String: Any]],
               let firstItem = itemList.first,
               let video = firstItem["video"] as? [String: Any],
               let playAddr = video["play_addr"] as? [String: Any],
               let uri = playAddr["uri"] as? String {
                return uri
            }
            print("[NativeMediaScraper] iesdouyin response did not contain play_addr.uri")
        } catch {
            print("[NativeMediaScraper] iesdouyin request failed: \(error.localizedDescription)")
        }
        return nil
    }

    private func cookieHeader(for url: URL, cookies: [HTTPCookie]) -> String? {
        guard let host = url.host?.lowercased() else { return nil }
        let matchingCookies = cookies.filter { cookie in
            let domain = cookie.domain.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "."))
            return host == domain || host.hasSuffix(".\(domain)")
        }
        guard !matchingCookies.isEmpty else { return nil }
        return HTTPCookie.requestHeaderFields(with: matchingCookies)["Cookie"]
    }

    private func douyinNoWatermarkURL(awemeID: String) async -> URL? {
        // Match the working desktop strategy: prefer the real video URI from
        // iesdouyin, but still try the no-watermark /play/ endpoint with the
        // aweme ID when that metadata endpoint is unavailable. Never use playwm.
        let resolvedID = await getDouyinVidFromIes(awemeId: awemeID)
        let videoID = resolvedID.flatMap { $0.isEmpty ? nil : $0 } ?? awemeID
        let encodedVideoID = videoID.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? videoID
        return URL(string: "https://aweme.snssdk.com/aweme/v1/play/?video_id=\(encodedVideoID)&ratio=1080p&line=0")
    }

    private func isPlatformURL(_ url: URL) -> Bool {
        let host = url.host?.lowercased() ?? ""
        return host.contains("douyin.com") || host.contains("tiktok.com")
    }

    private func isDouyinURL(_ url: URL) -> Bool {
        (url.host?.lowercased() ?? "").contains("douyin.com")
    }

    private func douyinAwemeID(from url: URL) -> String? {
        let pattern = #"/(?:video|note)/(\d+)"#
        guard let expression = try? NSRegularExpression(pattern: pattern),
              let match = expression.firstMatch(in: url.path, range: NSRange(url.path.startIndex..., in: url.path)),
              let range = Range(match.range(at: 1), in: url.path) else {
            return nil
        }
        return String(url.path[range])
    }

    private func extractDouyinMediaURLs(_ aweme: [String: Any]) async -> [URL]? {
        // 1. Try images if it is an image post
        if let images = aweme["images"] as? [[String: Any]], !images.isEmpty {
            var urls: [URL] = []
            for img in images {
                let urlList = img["urlList"] as? [String] ?? img["url_list"] as? [String]
                if let first = urlList?.first {
                    var urlStr = first
                    if urlStr.hasPrefix("//") { urlStr = "https:" + urlStr }
                    if let u = URL(string: urlStr) { urls.append(u) }
                }
            }
            if !urls.isEmpty { return urls }
        }

        // 2. Resolve a no-watermark playback endpoint. The `urlList` fallback is
        // deliberately not used here: it can be the page's `playwm` stream.
        if let video = aweme["video"] as? [String: Any] {
            var videoURI: String? = nil

            if let playAddrList = video["playAddr"] as? [[String: Any]], let first = playAddrList.first {
                videoURI = first["uri"] as? String
            } else if let playAddr = video["playAddr"] as? [String: Any] {
                videoURI = playAddr["uri"] as? String
            }

            if videoURI == nil {
                if let playAddr = video["play_addr"] as? [String: Any] {
                    videoURI = playAddr["uri"] as? String
                } else if let playAddrList = video["play_addr"] as? [[String: Any]], let first = playAddrList.first {
                    videoURI = first["uri"] as? String
                }
            }

            if videoURI == nil {
                if let playAddr = video["play_addr_low_quality"] as? [String: Any] {
                    videoURI = playAddr["uri"] as? String
                } else if let playAddrList = video["play_addr_low_quality"] as? [[String: Any]], let first = playAddrList.first {
                    videoURI = first["uri"] as? String
                }
            }

            let awemeId = aweme["awemeId"] as? String ?? aweme["aweme_id"] as? String

            if let awemeId = awemeId {
                if let resolvedVideoID = await getDouyinVidFromIes(awemeId: awemeId),
                   !resolvedVideoID.isEmpty {
                    videoURI = resolvedVideoID
                } else if videoURI == nil || videoURI?.isEmpty == true {
                    videoURI = awemeId
                }
            }

            if let targetVid = videoURI,
               !targetVid.isEmpty,
               !targetVid.lowercased().hasPrefix("http") {
                let encodedVideoID = targetVid.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? targetVid
                let noWmStr = "https://aweme.snssdk.com/aweme/v1/play/?video_id=\(encodedVideoID)&ratio=1080p&line=0"
                if let u = URL(string: noWmStr) { return [u] }
            }
        }
        return nil
    }

    private func findTikTokItem(_ dict: [String: Any]) -> [String: Any]? {
        if let defaultScope = dict["__DEFAULT_SCOPE__"] as? [String: Any] {
            if let videoDetail = defaultScope["webapp.video-detail"] as? [String: Any],
               let itemInfo = videoDetail["itemInfo"] as? [String: Any],
               let itemStruct = itemInfo["itemStruct"] as? [String: Any] {
                return itemStruct
            }

            for (_, value) in defaultScope {
                if let subDict = value as? [String: Any],
                   let itemInfo = subDict["itemInfo"] as? [String: Any],
                   let itemStruct = itemInfo["itemStruct"] as? [String: Any] {
                    return itemStruct
                }
            }
        }

        if let itemModule = dict["ItemModule"] as? [String: [String: Any]] {
            return itemModule.values.first(where: { $0["video"] != nil })
        }
        return nil
    }

    private func extractTikTokMediaURLs(_ item: [String: Any]) -> [URL]? {
        // 1. Try imagePostInfo
        if let imagePostInfo = item["imagePostInfo"] as? [String: Any],
           let images = imagePostInfo["images"] as? [[String: Any]], !images.isEmpty {
            var urls: [URL] = []
            for img in images {
                if let displayAddr = img["displayAddr"] as? [String: Any],
                   let urlList = displayAddr["urlList"] as? [String], let first = urlList.first {
                    if let u = URL(string: first) { urls.append(u) }
                } else if let imageURL = img["imageURL"] as? [String: Any],
                          let urlList = imageURL["urlList"] as? [String], let first = urlList.first {
                    if let u = URL(string: first) { urls.append(u) }
                }
            }
            if !urls.isEmpty { return urls }
        }

        // 2. Try video playAddr
        if let video = item["video"] as? [String: Any],
           let playAddr = video["playAddr"] as? String,
           let u = URL(string: playAddr) {
            return [u]
        }
        return nil
    }
}
