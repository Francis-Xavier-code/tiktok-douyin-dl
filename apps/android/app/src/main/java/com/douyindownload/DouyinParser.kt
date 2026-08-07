package com.douyindownload

import android.net.Uri
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLDecoder
import java.util.concurrent.TimeUnit

/** 单个可下载媒体。 */
data class DirectMedia(val isVideo: Boolean, val url: String)

/**
 * 抖音页面解析引擎。
 */
object DouyinParser {

    private const val TAG = "DouyinParser"
    private val urlPattern = Regex("""https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+""")
    private val douyinHostPattern = Regex("""(^|\.)(douyin|iesdouyin)\.com$""")
    private val renderDataPattern = Regex("""RENDER_DATA["\s][^>]*>([^<]+)</script>""", RegexOption.DOT_MATCHES_ALL)

    private val client by lazy {
        OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .followRedirects(true)
            .build()
    }

    private const val DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    fun extractUrls(text: String): List<String> =
        urlPattern.findAll(text).map { it.value }.filter { isDouyinUrl(it) }.distinct().toList()

    fun isDouyinUrl(url: String): Boolean {
        val host = runCatching { Uri.parse(url).host }.getOrNull() ?: return false
        return douyinHostPattern.containsMatchIn(host.lowercase())
    }

    /** 极速引擎解析（兜底）。 */
    suspend fun resolveDirectMedia(url: String): List<DirectMedia> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder().url(url).header("User-Agent", DESKTOP_UA).build()
            val response = client.newCall(request).execute()
            val html = response.body?.string() ?: ""
            
            renderDataPattern.find(html)?.let { m ->
                val content = m.groupValues[1].trim()
                val decoded = if (content.startsWith("%")) URLDecoder.decode(content, "UTF-8") else content
                findAweme(JSONObject(decoded))?.let { return@withContext extractMedia(it) }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Quick parse error", e)
        }
        emptyList()
    }

    /** 递归寻找作品详情节点。 */
    fun findAweme(node: Any?): JSONObject? {
        if (node is JSONObject) {
            // 常见核心字段
            for (key in listOf("aweme", "awemeDetail", "aweme_detail", "awemeInfo", "videoInfo", "videoInfoRes", "item_list", "aweme_list")) {
                val value = node.opt(key)
                if (value is JSONObject) return value
                if (value is JSONArray && value.length() > 0) return value.optJSONObject(0)
            }
            // 深度扫描
            val keys = node.keys()
            while (keys.hasNext()) {
                val key = keys.next()
                if (key == "author" || key == "music" || key == "stats" || key == "common_log" || key == "suggest_words") continue
                val child = findAweme(node.opt(key))
                if (child != null) return child
            }
        } else if (node is JSONArray) {
            for (i in 0 until node.length()) {
                val child = findAweme(node.opt(i))
                if (child != null) return child
            }
        }
        return null
    }

    /** 从作品详情中提取媒体列表。 */
    fun extractMedia(aweme: JSONObject): List<DirectMedia> {
        val media = mutableListOf<DirectMedia>()
        
        // 1. 图文/动图检测
        val images = aweme.optJSONArray("images") ?: aweme.optJSONArray("image_post")
        if (images != null && images.length() > 0) {
            for (i in 0 until images.length()) {
                val img = images.optJSONObject(i) ?: continue
                val urlList = img.optJSONArray("url_list") ?: img.optJSONArray("urlList") ?: 
                              img.optJSONObject("display_image")?.optJSONArray("url_list")
                if (urlList != null && urlList.length() > 0) {
                    val first = urlList.optString(0)
                    if (first.isNotBlank()) media.add(DirectMedia(isVideo = false, url = normalizeUrl(first)))
                }
            }
            if (media.isNotEmpty()) return media
        }

        // 2. 视频检测
        val video = aweme.optJSONObject("video")
        if (video != null) {
            val playAddr = video.opt("play_addr") ?: video.opt("playAddr") ?: video.opt("download_addr")
            var vid: String? = null
            var directUrl: String? = null
            
            if (playAddr is JSONObject) {
                vid = playAddr.optString("uri")
                val urlList = playAddr.optJSONArray("url_list") ?: playAddr.optJSONArray("urlList")
                if (urlList != null && urlList.length() > 0) directUrl = urlList.optString(0)
            } else if (playAddr is JSONArray && playAddr.length() > 0) {
                val first = playAddr.optJSONObject(0)
                vid = first?.optString("uri")
                directUrl = first?.optString("url_list") ?: first?.optString("urlList")
            }
            
            // 优先构造无水印地址
            if (!vid.isNullOrBlank() && !vid.startsWith("http")) {
                val encoded = Uri.encode(vid)
                media.add(DirectMedia(isVideo = true, url = "https://aweme.snssdk.com/aweme/v1/play/?video_id=$encoded&ratio=1080p&line=0"))
            } else if (!directUrl.isNullOrBlank() && directUrl.startsWith("http")) {
                media.add(DirectMedia(isVideo = true, url = normalizeUrl(directUrl)))
            }
        }
        return media
    }

    private fun normalizeUrl(url: String): String = if (url.startsWith("//")) "https:$url" else url
}
