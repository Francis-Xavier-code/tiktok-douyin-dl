package com.douyindownload

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/** 版本策略结果。 */
sealed class VersionPolicyResult {
    object Allow : VersionPolicyResult()
    data class Block(
        val message: String, 
        val updateUrl: String, 
        val apkUrl: String,
        val changelog: String = ""
    ) : VersionPolicyResult()
}

/**
 * 远程版本策略（version-policy.json）。
 */
object VersionPolicyService {

    private const val CURRENT_VERSION = "0.1.3"
    private const val PLATFORM = "android"
    const val DEFAULT_UPDATE_URL = "https://gitee.com/Xynrin/douyin-download/releases"

    private val sources = listOf(
        "https://gitee.com/Xynrin/douyin-download/raw/master/version-policy.json",
        "https://raw.giteeusercontent.com/Xynrin/douyin-download/raw/master/version-policy.json",
        "https://gh-proxy.com/https://raw.giteeusercontent.com/Xynrin/douyin-download/raw/master/version-policy.json",
        "https://ghproxy.net/https://raw.giteeusercontent.com/Xynrin/douyin-download/raw/master/version-policy.json",
        "https://raw.gitmirror.com/Xynrin/douyin-download/raw/master/version-policy.json",
        "https://kgithub.com/Xynrin/douyin-download/raw/master/version-policy.json",
    )

    private val client by lazy {
        OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .build()
    }

    suspend fun evaluate(): VersionPolicyResult = withContext(Dispatchers.IO) {
        var policy: JSONObject? = null
        for (url in sources) {
            try {
                val request = Request.Builder()
                    .url(url)
                    .header("User-Agent", "douyin-download-Android/$CURRENT_VERSION")
                    .build()
                client.newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val text = response.body?.string()
                        if (!text.isNullOrBlank()) {
                            runCatching { JSONObject(text) }.getOrNull()?.let { policy = it }
                        }
                    }
                }
            } catch (_: Exception) {}
            if (policy != null) break
        }

        val p = policy ?: return@withContext VersionPolicyResult.Allow

        val entry = p.optJSONObject("platforms")?.optJSONObject(PLATFORM)
        if (entry == null) return@withContext VersionPolicyResult.Allow

        val minVersion = entry.optString("min_version", "0.0.0")
        if (compareVersions(CURRENT_VERSION, minVersion) >= 0) {
            return@withContext VersionPolicyResult.Allow
        }

        val message = p.optString("message", "").ifBlank {
            "发现新版本，请升级到最新版本以获得最佳体验。"
        }
        val updateUrl = p.optString("update_url", "").ifBlank { DEFAULT_UPDATE_URL }
        val apkUrl = p.optString("apk_url", "").ifBlank {
            updateUrl + "/download/douyin-download-Android-0.1.1.apk"
        }
        
        // 解析日志字段（如果存在）
        val changelog = entry.optString("changelog", "").ifBlank {
            p.optString("changelog", "")
        }
        
        VersionPolicyResult.Block(message, updateUrl, apkUrl, changelog)
    }

    private fun compareVersions(a: String, b: String): Int {
        val pa = a.split(".").mapNotNull { it.toIntOrNull() }
        val pb = b.split(".").mapNotNull { it.toIntOrNull() }
        val count = maxOf(pa.size, pb.size)
        for (i in 0 until count) {
            val x = if (i < pa.size) pa[i] else 0
            val y = if (i < pb.size) pb[i] else 0
            if (x != y) return if (x > y) 1 else -1
        }
        return 0
    }
}
