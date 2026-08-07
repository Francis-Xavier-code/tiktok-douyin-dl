package com.douyindownload

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * 远程更新日志服务。
 * 适配全平台共享的 changelog.json。
 */
object ChangelogService {

    private const val URL = "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/changelog.json"
    
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
                    val parsed = parseJson(raw)
                    cachedLogs = parsed
                    return@withContext parsed
                }
            }
        } catch (e: Exception) {
            return@withContext "获取日志失败: ${e.message}"
        }
        
        "暂无日志数据"
    }

    /** 解析 changelog.json 并提取 [all] 和 [android] 相关条目。 */
    private fun parseJson(jsonStr: String): String {
        return try {
            val json = JSONObject(jsonStr)
            val versions = json.optJSONArray("versions") ?: return "暂无更新内容"
            val result = StringBuilder()
            
            for (i in 0 until versions.length()) {
                val v = versions.optJSONObject(i) ?: continue
                val verName = v.optString("version")
                val date = v.optString("date")
                val entries = v.optJSONObject("entries") ?: continue
                
                val allEntries = entries.optJSONArray("all")
                val androidEntries = entries.optJSONArray("android")
                
                val hasAll = allEntries != null && allEntries.length() > 0
                val hasAndroid = androidEntries != null && androidEntries.length() > 0
                
                if (!hasAll && !hasAndroid) continue
                    
                if (result.isNotEmpty()) result.append("\n\n")
                result.append("版本 ").append(verName).append(" (").append(date).append(")：\n")
                
                if (allEntries != null) {
                    for (j in 0 until allEntries.length()) {
                        result.append("  • ").append(allEntries.optString(j)).append("\n")
                    }
                }
                if (androidEntries != null) {
                    for (j in 0 until androidEntries.length()) {
                        result.append("  • ").append(androidEntries.optString(j)).append("\n")
                    }
                }
            }
            result.toString().trim().ifBlank { "未找到 Android 相关的更新条目" }
        } catch (e: Exception) {
            "日志解析失败"
        }
    }
}
