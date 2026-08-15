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
    /** 软提示（hard_block=false）：旧版本仍可用，仅提醒升级。 */
    data class Nag(
        val message: String,
        val updateUrl: String,
        val apkUrl: String,
        val changelog: String = ""
    ) : VersionPolicyResult()
    /** 硬阻挡（hard_block=true）：旧版本被强制拦截，必须更新。 */
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

    private val CURRENT_VERSION = BuildConfig.VERSION_NAME
    private const val PLATFORM = "android"
    const val DEFAULT_UPDATE_URL = "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases"

    private val sources = listOf(
        "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
        "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/raw/main/version-policy.json",
        "https://gh-proxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
        "https://ghproxy.net/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
        "https://raw.gitmirror.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
        "https://kgithub.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
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

        // 与 iOS/macOS/CLI 一致：hard_block=false 时只是软提示（Nag），不强制更新。
        val hardBlock = entry.optBoolean("hard_block", false)

        val message = p.optString("message", "").ifBlank {
            "发现新版本，请升级到最新版本以获得最佳体验。"
        }
        val updateUrl = p.optString("update_url", "").ifBlank { DEFAULT_UPDATE_URL }
        val apkUrl = p.optString("apk_url", "").ifBlank {
            updateUrl + "/download/douyin-download-Android-$minVersion.apk"
        }
        
        // 解析日志字段（如果存在）
        val changelog = entry.optString("changelog", "").ifBlank {
            p.optString("changelog", "")
        }
        
        return@withContext if (hardBlock) {
            VersionPolicyResult.Block(message, updateUrl, apkUrl, changelog)
        } else {
            VersionPolicyResult.Nag(message, updateUrl, apkUrl, changelog)
        }
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

    fun isNewer(a: String, b: String): Boolean = compareVersions(a, b) < 0

    /** 按发布资产命名规则构建指定版本的 APK 下载地址。 */
    fun apkUrlFor(version: String): String {
        val v = version.removePrefix("v")
        return "$DEFAULT_UPDATE_URL/download/v$v/douyin-download-Android-$v.apk"
    }
}
