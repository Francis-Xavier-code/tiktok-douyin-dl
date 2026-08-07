package com.douyindownload

import android.content.ContentValues
import android.content.Context
import android.media.MediaScannerConnection
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import android.webkit.CookieManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.TimeUnit

/**
 * 增强型媒体保存器。
 * 支持同步 WebView Cookie 和 UA 以提高下载成功率。
 */
object MediaSaver {

    private const val TAG = "MediaSaver"
    private const val BROWSER_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"

    private val client by lazy {
        OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .followRedirects(true)
            .build()
    }

    suspend fun downloadAndSave(context: Context, media: DirectMedia): Uri? =
        withContext(Dispatchers.IO) {
            val cookies = CookieManager.getInstance().getCookie(media.url) ?: ""
            Log.d(TAG, "Downloading with cookies: ${cookies.take(20)}...")
            
            var lastError = ""
            for (attempt in 1..2) {
                try {
                    val builder = Request.Builder()
                        .url(media.url)
                        .header("User-Agent", BROWSER_UA)
                        .header("Referer", "https://www.douyin.com/")
                        .header("Cookie", cookies)
                    
                    if (attempt == 1) {
                        builder.header("Range", "bytes=0-")
                    }

                    val request = builder.build()
                    client.newCall(request).execute().use { response ->
                        if (response.isSuccessful) {
                            val bytes = response.body?.bytes()
                            if (bytes != null && bytes.isNotEmpty()) {
                                return@withContext saveBytes(context, bytes, media.isVideo)
                            }
                        } else if (response.code == 403 && cookies.isBlank()) {
                            // 如果 403 且没 Cookie，可能是因为 WebView 还没拿到 Cookie
                            lastError = "HTTP 403 (No Cookies)"
                        } else {
                            lastError = "HTTP ${response.code}"
                        }
                        Log.w(TAG, "Attempt $attempt failed: $lastError")
                    }
                } catch (e: Exception) {
                    lastError = e.message ?: e.toString()
                    Log.e(TAG, "Attempt $attempt exception", e)
                }
            }
            throw IllegalStateException("下载失败: $lastError")
        }

    private fun saveBytes(context: Context, bytes: ByteArray, isVideo: Boolean): Uri? {
        val ext = if (isVideo) "mp4" else "jpg"
        val mime = if (isVideo) "video/mp4" else "image/jpeg"
        val displayName = "douyin_${System.currentTimeMillis()}.$ext"

        try {
            if (Build.VERSION.SDK_INT >= 29) {
                val collection = if (isVideo) {
                    MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                } else {
                    MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                }
                val relativePath = if (isVideo) {
                    Environment.DIRECTORY_DCIM + "/douyin-download"
                } else {
                    Environment.DIRECTORY_PICTURES + "/douyin-download"
                }
                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
                    put(MediaStore.MediaColumns.MIME_TYPE, mime)
                    put(MediaStore.MediaColumns.RELATIVE_PATH, relativePath)
                }
                val resolver = context.contentResolver
                val uri = resolver.insert(collection, values) ?: return null
                resolver.openOutputStream(uri)?.use { it.write(bytes) } ?: return null
                return uri
            } else {
                val root = if (isVideo) {
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DCIM)
                } else {
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES)
                }
                val directory = File(root, "douyin-download")
                if (!directory.exists()) directory.mkdirs()
                val file = File(directory, displayName)
                FileOutputStream(file).use { it.write(bytes) }
                MediaScannerConnection.scanFile(context, arrayOf(file.absolutePath), arrayOf(mime), null)
                return Uri.fromFile(file)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Save failed", e)
            return null
        }
    }
}
