package com.douyindownload

import android.annotation.SuppressLint
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.withTimeoutOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * 终极解析引擎：结合 WebView 获取鉴权环境与官方 API 深度解析。
 */
object DouyinWebViewParser {

    private const val TAG = "DouyinWebViewParser"
    private const val UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    private val client by lazy {
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .build()
    }

    @SuppressLint("SetJavaScriptEnabled")
    suspend fun resolve(context: Context, url: String): List<DirectMedia> {
        val deferred = CompletableDeferred<List<DirectMedia>>()
        
        Handler(Looper.getMainLooper()).post {
            val webView = WebView(context)
            webView.settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                databaseEnabled = true
                userAgentString = UA
            }
            
            webView.webViewClient = object : WebViewClient() {
                private var apiCalled = false

                override fun onPageFinished(view: WebView?, currentUrl: String?) {
                    super.onPageFinished(view, currentUrl)
                    if (currentUrl == null || apiCalled) return
                    
                    val awemeId = extractId(currentUrl)
                    if (awemeId != null) {
                        apiCalled = true
                        val cookies = CookieManager.getInstance().getCookie(currentUrl) ?: ""
                        Log.d(TAG, "Auth obtained, fetching metadata for $awemeId")
                        
                        Thread {
                            try {
                                val media = fetchFromApi(awemeId, currentUrl, cookies)
                                if (media.isNotEmpty()) {
                                    deferred.complete(media)
                                }
                            } catch (e: Exception) {
                                Log.e(TAG, "API fetch failed", e)
                            }
                        }.start()
                    }
                }

                private fun extractId(url: String): String? {
                    val patterns = listOf(
                        Regex("""video/(\d+)"""),
                        Regex("""note/(\d+)"""),
                        Regex("""modal_id=(\d+)""")
                    )
                    for (p in patterns) {
                        p.find(url)?.let { return it.groupValues[1] }
                    }
                    return null
                }
            }
            
            webView.loadUrl(url)
            
            Handler(Looper.getMainLooper()).postDelayed({
                if (!deferred.isCompleted) {
                    webView.destroy()
                    deferred.complete(emptyList())
                }
            }, 15000)
        }
        
        return withTimeoutOrNull(18000) { deferred.await() } ?: emptyList()
    }

    private fun fetchFromApi(id: String, referer: String, cookies: String): List<DirectMedia> {
        // 使用官方 Web 详情 API，配合 WebView 拿到的实时 Cookie
        val apiUrl = "https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=$id&device_platform=webapp&aid=6383"
        val request = Request.Builder()
            .url(apiUrl)
            .header("User-Agent", UA)
            .header("Referer", referer)
            .header("Cookie", cookies)
            .build()
            
        return try {
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    val json = JSONObject(response.body?.string() ?: "")
                    val aweme = DouyinParser.findAweme(json)
                    if (aweme != null) {
                        return DouyinParser.extractMedia(aweme)
                    }
                }
                emptyList()
            }
        } catch (_: Exception) {
            emptyList()
        }
    }
}
