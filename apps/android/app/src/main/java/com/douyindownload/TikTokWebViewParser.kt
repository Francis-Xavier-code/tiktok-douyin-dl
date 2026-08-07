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
import org.json.JSONObject

/**
 * TikTok 解析引擎：利用 WebView 加载页面并提取注入的 JSON 状态。
 */
object TikTokWebViewParser {

    private const val TAG = "TikTokWebViewParser"
    private const val UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

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
                override fun onPageFinished(view: WebView?, currentUrl: String?) {
                    super.onPageFinished(view, currentUrl)
                    if (currentUrl == null) return
                    
                    // TikTok 的数据通常直接注水在 HTML 的 <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"> 中
                    // 我们通过 JS 提取它
                    webView.evaluateJavascript(
                        "(function() { return document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__')?.innerText; })();"
                    ) { jsonStr ->
                        if (!jsonStr.isNullOrBlank() && jsonStr != "null") {
                            try {
                                // evaluateJavascript 返回的是 JSON 字符串的 JSON 转义版本，需要去掉前后的引号并反转义
                                val cleanJson = if (jsonStr.startsWith("\"") && jsonStr.endsWith("\"")) {
                                    // 简单处理转义：这可能不够严谨，但在 Android WebView 中通常有效
                                    jsonStr.substring(1, jsonStr.length - 1)
                                        .replace("\\\"", "\"")
                                        .replace("\\\\", "\\")
                                } else jsonStr
                                
                                val media = TikTokParser.extractMedia(JSONObject(cleanJson))
                                if (media.isNotEmpty()) {
                                    deferred.complete(media)
                                }
                            } catch (e: Exception) {
                                Log.e(TAG, "Failed to parse injected JSON", e)
                            }
                        }
                    }
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
}
