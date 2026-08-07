package com.douyindownload

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

/**
 * 远程更新日志服务。
 * 直接从仓库拉取 CHANGELOG.md 并进行简单解析。
 */
object ChangelogService {

    private const val URL = "https://gitee.com/Xynrin/douyin-download/raw/master/CHANGELOG.md"
    
    private val client by lazy {
        OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .build()
    }

    private var cachedLogs: String? = null

    /** 获取格式化后的更新日志。 */
    suspend fun fetchLogs(): String = withContext(Dispatchers.IO) {
        cachedLogs?.let { return@withContext it }

        try {
            val request = Request.Builder().url(URL).build()
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    val raw = response.body?.string() ?: ""
                    val parsed = parseMarkdown(raw)
                    cachedLogs = parsed
                    return@withContext parsed
                }
            }
        } catch (e: Exception) {
            return@withContext "获取日志失败: ${e.message}"
        }
        
        "暂无日志数据"
    }

    /** 简单的 Markdown 解析：提取版本号和条目。 */
    private fun parseMarkdown(content: String): String {
        val lines = content.lines()
        val result = StringBuilder()
        var capturing = false
        
        for (line in lines) {
            val trimmed = line.trim()
            if (trimmed.startsWith("## [")) {
                // 提取版本号
                val version = trimmed.substringAfter("[").substringBefore("]")
                if (result.isNotEmpty()) result.append("\n\n")
                result.append("版本 ").append(version).append("：\n")
                capturing = true
            } else if (capturing && (trimmed.startsWith("-") || trimmed.startsWith("*"))) {
                result.append("  ").append(trimmed).append("\n")
            } else if (trimmed.isBlank() && capturing) {
                // 保持段落间隔
            } else if (trimmed.startsWith("#")) {
                // 忽略一级标题
            }
        }
        
        return result.toString().trim().ifBlank { "CHANGELOG.md 格式暂不支持解析" }
    }
}
