package com.douyindownload

import android.net.Uri
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * TikTok 页面解析引擎。
 */
object TikTokParser {

    private const val TAG = "TikTokParser"
    private val urlPattern = Regex("""https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+""")
    private val tiktokHostPattern = Regex("""(^|\.)tiktok\.com$""")
    private val rehydrationDataPattern = Regex("""<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">([^<]+)</script>""", RegexOption.DOT_MATCHES_ALL)

    private val client by lazy {
        OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .followRedirects(true)
            .build()
    }

    private const val DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    fun extractUrls(text: String): List<String> =
        urlPattern.findAll(text).map { it.value }.filter { isTikTokUrl(it) }.distinct().toList()

    fun isTikTokUrl(url: String): Boolean {
        val host = runCatching { Uri.parse(url).host }.getOrNull() ?: return false
        return tiktokHostPattern.containsMatchIn(host.lowercase())
    }

    /** 极速引擎解析（兜底）。 */
    suspend fun resolveDirectMedia(url: String): List<DirectMedia> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder().url(url).header("User-Agent", DESKTOP_UA).build()
            val response = client.newCall(request).execute()
            val html = response.body?.string() ?: ""
            
            rehydrationDataPattern.find(html)?.let { m ->
                val content = m.groupValues[1].trim()
                return@withContext extractMedia(JSONObject(content))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Quick parse error", e)
        }
        emptyList()
    }

    /** 从 JSON 数据中提取媒体列表。 */
    fun extractMedia(data: JSONObject): List<DirectMedia> {
        val media = mutableListOf<DirectMedia>()
        
        // 尝试提取 itemStruct 节点
        var item = data.optJSONObject("__DEFAULT_SCOPE__")
            ?.optJSONObject("webapp.video-detail")
            ?.optJSONObject("itemInfo")
            ?.optJSONObject("itemStruct")

        if (item == null) {
            // 备用路径寻找
            val defaultScope = data.optJSONObject("__DEFAULT_SCOPE__")
            if (defaultScope != null) {
                val keys = defaultScope.keys()
                while (keys.hasNext()) {
                    val k = keys.next()
                    val v = defaultScope.optJSONObject(k)
                    if (v != null && v.has("itemInfo")) {
                        item = v.optJSONObject("itemInfo")?.optJSONObject("itemStruct")
                        if (item != null) break
                    }
                }
            }
        }

        if (item == null) return emptyList()

        // 1. 图文相册检测
        val imagePostInfo = item.optJSONObject("imagePostInfo")
        val images = imagePostInfo?.optJSONArray("images")
        if (images != null && images.length() > 0) {
            for (i in 0 until images.length()) {
                val img = images.optJSONObject(i) ?: continue
                val displayAddr = img.optJSONObject("displayAddr")
                val urlList = displayAddr?.optJSONArray("urlList")
                if (urlList != null && urlList.length() > 0) {
                    val first = urlList.optString(0)
                    if (first.isNotBlank()) media.add(DirectMedia(isVideo = false, url = first))
                }
            }
            if (media.isNotEmpty()) return media
        }

        // 2. 视频检测
        val video = item.optJSONObject("video")
        if (video != null) {
            val playAddr = video.optString("playAddr")
            if (playAddr.isNotBlank()) {
                media.add(DirectMedia(isVideo = true, url = playAddr))
            }
        }
        
        return media
    }
}
