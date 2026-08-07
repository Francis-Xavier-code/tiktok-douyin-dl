package com.douyindownload

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * 应用内自动更新：下载新版 APK 到应用私有目录，再通过 FileProvider
 * 拉起系统安装界面。
 */
object UpdaterHelper {

    private val client by lazy {
        OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(300, TimeUnit.SECONDS)
            .build()
    }

    /**
     * 下载 APK 到 filesDir/downloads/，返回 FileProvider content Uri。
     * [onProgress] 接收 0-100 进度（可能只回调少数几次）。
     */
    suspend fun downloadApk(
        context: Context,
        url: String,
        onProgress: (Int) -> Unit = {},
    ): Uri = withContext(Dispatchers.IO) {
        val target = File(context.filesDir, "downloads").apply { mkdirs() }
        val apkFile = File(target, "douyin-download-update.apk")

        val request = Request.Builder()
            .url(url)
            .header("User-Agent", "douyin-download-Android/0.1.1")
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IllegalStateException("下载失败：HTTP ${response.code}")
            val body = response.body ?: throw IllegalStateException("下载内容为空。")
            val total = body.contentLength()
            apkFile.outputStream().use { output ->
                val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                var downloaded = 0L
                body.byteStream().use { input ->
                    while (true) {
                        val read = input.read(buffer)
                        if (read == -1) break
                        output.write(buffer, 0, read)
                        downloaded += read
                        if (total > 0) {
                            onProgress(((downloaded * 100) / total).toInt())
                        }
                    }
                }
            }
        }

        FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", apkFile)
    }

    /** 拉起系统安装界面（需已授权“安装未知应用”）。 */
    fun installApk(context: Context, uri: Uri) {
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(intent)
    }
}
