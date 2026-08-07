package com.douyindownload

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/** 下载策略结果。 */
sealed class PolicyResult {
    object Allow : PolicyResult()
    data class Block(val reason: String, val message: String, val issueUrl: String) : PolicyResult()
}

/**
 * 远程下载策略（fail-closed + Ed25519 验签）。
 *
 * 每次下载前必须通过本服务判定：所有源不可达、签名无效、enabled=false、
 * 版本过低，任一情形都拒绝下载。
 */
object DownloadPolicyService {

    private const val CURRENT_VERSION = "0.1.3"
    private const val PLATFORM = "android"
    private const val ISSUE_URL = "https://gitee.com/Xynrin/douyin-download/issues"

    private val sources = listOf(
        "https://gitee.com/Xynrin/douyin-download/raw/master/download-policy.json",
        "https://raw.giteeusercontent.com/Xynrin/douyin-download/raw/master/download-policy.json",
        "https://gh-proxy.com/https://raw.giteeusercontent.com/Xynrin/douyin-download/raw/master/download-policy.json",
        "https://ghproxy.net/https://raw.giteeusercontent.com/Xynrin/douyin-download/raw/master/download-policy.json",
        "https://raw.gitmirror.com/Xynrin/douyin-download/raw/master/download-policy.json",
        "https://kgithub.com/Xynrin/douyin-download/raw/master/download-policy.json",
    )

    private val client by lazy {
        OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .build()
    }

    suspend fun evaluate(): PolicyResult = withContext(Dispatchers.IO) {
        var validPolicy: JSONObject? = null
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
                            val parsed = JSONObject(text)
                            // 关键修复：获取到 JSON 后立即验签，只有验签通过才采纳
                            if (parsed.length() > 0 && PolicyVerifier.verify(parsed)) {
                                validPolicy = parsed
                            }
                        }
                    }
                }
            } catch (_: Exception) {
                // 尝试下一个源
            }
            if (validPolicy != null) break
        }

        val p = validPolicy
        if (p == null) {
            return@withContext PolicyResult.Block(
                reason = "unreachable",
                message = "无法连接下载策略服务或策略校验失败。在恢复连接前已暂停下载功能。",
                issueUrl = ISSUE_URL,
            )
        }

        // 移除外部重复验签
        val download = p.optJSONObject("download")
        if (download == null) {
            return@withContext PolicyResult.Block(
                reason = "unreachable",
                message = "下载策略文件格式异常，已暂停下载功能。",
                issueUrl = ISSUE_URL,
            )
        }

        val enabled = download.optBoolean("enabled", true)
        if (!enabled) {
            val message = download.optString("message", "").ifBlank {
                "维护者已临时关闭下载功能，请关注项目主页了解状态。"
            }
            return@withContext PolicyResult.Block("disabled", message, ISSUE_URL)
        }

        val minVersion = download.optString("min_version", "0.0.0")
        if (compareVersions(CURRENT_VERSION, minVersion) < 0) {
            return@withContext PolicyResult.Block(
                reason = "version",
                message = "当前版本过低，下载功能已限制，请升级到最新版本。",
                issueUrl = ISSUE_URL,
            )
        }

        PolicyResult.Allow
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
