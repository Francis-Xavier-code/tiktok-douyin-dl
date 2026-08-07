package com.douyindownload

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import com.bumptech.glide.Glide
import com.douyindownload.databinding.ActivityMainBinding
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import kotlinx.coroutines.launch

/**
 * douyin-download Android 客户端主界面。
 * 现代化 Material 3 风格 + 底部导航 + WebView 解析。
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var busy = false

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 适配沉浸式系统栏
        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, 0, systemBars.right, 0)
            
            // 为悬浮导航栏留出底部边距，防止遮挡内容
            val bottomMargin = systemBars.bottom + 32.dpToPx()
            val lp = binding.bottomNavCard.layoutParams as android.view.ViewGroup.MarginLayoutParams
            lp.bottomMargin = bottomMargin
            binding.bottomNavCard.layoutParams = lp
            
            insets
        }

        setupNavigation()
        setupListeners()
        setupSettingsPage()
        
        handleSharedText(intent)
        checkVersionAndUpdate(silent = true)
    }

    private fun setupNavigation() {
        binding.bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_download -> {
                    binding.downloadPage.visibility = View.VISIBLE
                    binding.settingsContainer.visibility = View.GONE
                    binding.toolbar.title = "Media Downloader"
                    true
                }
                R.id.nav_settings -> {
                    binding.downloadPage.visibility = View.GONE
                    binding.settingsContainer.visibility = View.VISIBLE
                    binding.toolbar.title = "设置与关于"
                    true
                }
                else -> false
            }
        }
    }

    private fun setupListeners() {
        binding.downloadButton.setOnClickListener { startDownload() }
    }

    private fun setupSettingsPage() {
        val s = binding.settings
        
        // 加载开发者头像
        Glide.with(this)
            .load("https://github.com/Francis-Xavier-code.png")
            .placeholder(android.R.drawable.ic_menu_myplaces)
            .circleCrop()
            .into(s.devAvatar)
            
        s.devName.text = "Francis Xavier"
        s.versionText.text = "v${BuildConfig.VERSION_NAME}"
        
        // 异步真实读取远程仓库的 changelog
        lifecycleScope.launch {
            s.changelogText.text = "正在同步远程日志…"
            val logs = ChangelogService.fetchLogs()
            s.changelogText.text = logs
        }
        
        s.checkUpdateButton.setOnClickListener {
            checkVersionAndUpdate(silent = false)
        }
        
        s.developerCard.setOnClickListener {
            openBrowser("https://github.com/Francis-Xavier-code/tiktok-douyin-dl")
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleSharedText(intent)
    }

    private fun handleSharedText(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        val text = intent.getStringExtra(Intent.EXTRA_TEXT)?.trim().orEmpty()
        if (text.isEmpty()) return
        
        binding.bottomNav.selectedItemId = R.id.nav_download
        binding.inputText.setText(text)
        log("已收到分享内容，开始解析…")
        startDownload()
    }

    private fun startDownload() {
        if (busy) return
        val text = binding.inputText.text.toString().trim()
        if (text.isEmpty()) {
            binding.logText.text = "请先粘贴抖音或 TikTok 分享文本或链接。"
            return
        }

        busy = true
        binding.downloadButton.isEnabled = false
        binding.progressBar.visibility = View.VISIBLE
        binding.logText.text = ""

        lifecycleScope.launch {
            try {
                log("1/3 正在校验下载策略…")
                when (val policy = DownloadPolicyService.evaluate()) {
                    is PolicyResult.Allow -> Unit
                    is PolicyResult.Block -> {
                        log("❌ 下载被禁止：${policy.message}")
                        toast(policy.message)
                        return@launch
                    }
                }

                log("2/3 正在提取链接…")
                val douyinUrls = DouyinParser.extractUrls(text)
                val tiktokUrls = TikTokParser.extractUrls(text)
                
                if (douyinUrls.isEmpty() && tiktokUrls.isEmpty()) {
                    log("❌ 未找到支持的链接。")
                    return@launch
                }

                val allMedia = mutableListOf<DirectMedia>()
                
                // 处理抖音链接
                for ((index, url) in douyinUrls.withIndex()) {
                    log("正在解析抖音 [${index + 1}/${douyinUrls.size}]: $url")
                    var media = DouyinWebViewParser.resolve(this@MainActivity, url)
                    if (media.isEmpty()) {
                        log("WebView 解析未命中，尝试极速引擎兜底…")
                        media = runCatching { DouyinParser.resolveDirectMedia(url) }.getOrNull() ?: emptyList()
                    }
                    if (media.isNotEmpty()) allMedia.addAll(media)
                    else log("⚠️ 解析失败：$url")
                }
                
                // 处理 TikTok 链接
                for ((index, url) in tiktokUrls.withIndex()) {
                    log("正在解析 TikTok [${index + 1}/${tiktokUrls.size}]: $url")
                    var media = TikTokWebViewParser.resolve(this@MainActivity, url)
                    if (media.isEmpty()) {
                        log("WebView 解析未命中，尝试极速引擎兜底…")
                        media = runCatching { TikTokParser.resolveDirectMedia(url) }.getOrNull() ?: emptyList()
                    }
                    if (media.isNotEmpty()) allMedia.addAll(media)
                    else log("⚠️ 解析失败：$url")
                }

                if (allMedia.isEmpty()) {
                    log("❌ 未能从页面解析出媒体链接。")
                    return@launch
                }

                log("解析到 ${allMedia.size} 个媒体，开始下载…")
                var saved = 0
                for (m in allMedia) {
                    log("下载中：${m.url.take(60)}…")
                    val uri = MediaSaver.downloadAndSave(this@MainActivity, m)
                    if (uri != null) {
                        saved++
                        log("✅ 已保存：$uri")
                    } else log("⚠️ 保存失败")
                }

                log("3/3 完成：成功保存 $saved/${allMedia.size} 个文件。")
                toast("保存完成：$saved 个")
            } catch (e: Exception) {
                log("❌ 错误: ${e.message}")
            } finally {
                busy = false
                binding.downloadButton.isEnabled = true
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun checkVersionAndUpdate(silent: Boolean) {
        lifecycleScope.launch {
            if (!silent) toast("正在检查更新…")
            when (val result = VersionPolicyService.evaluate()) {
                is VersionPolicyResult.Allow -> {
                    if (!silent) toast("当前已是最新版本")
                }
                is VersionPolicyResult.Block -> showForceUpdateDialog(result)
            }
        }
    }

    private fun showForceUpdateDialog(result: VersionPolicyResult.Block) {
        if (isFinishing || isDestroyed) return
        
        val message = StringBuilder(result.message)
        if (result.changelog.isNotBlank()) {
            message.append("\n\n更新日志：\n").append(result.changelog)
        }
        message.append("\n\n将自动下载最新版并安装。")

        MaterialAlertDialogBuilder(this)
            .setTitle("发现新版本")
            .setMessage(message.toString())
            .setCancelable(false)
            .setPositiveButton("立即更新") { _, _ -> startAutoUpdate(result.apkUrl) }
            .setNegativeButton("退出") { _, _ -> finish() }
            .show()
    }

    private fun startAutoUpdate(apkUrl: String) {
        if (apkUrl.isBlank()) {
            openBrowser(VersionPolicyService.DEFAULT_UPDATE_URL)
            return
        }
        if (!packageManager.canRequestPackageInstalls()) {
            MaterialAlertDialogBuilder(this)
                .setTitle("需要安装权限")
                .setMessage("自动更新需要允许安装未知来源应用，请前往设置开启。")
                .setCancelable(false)
                .setPositiveButton("去开启") { _, _ ->
                    openBrowser("package:${packageName}", action = Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
                }
                .setNegativeButton("取消") { _, _ -> finish() }
                .show()
            return
        }

        lifecycleScope.launch {
            try {
                log("正在下载更新包…")
                val uri = UpdaterHelper.downloadApk(this@MainActivity, apkUrl) { progress ->
                    runOnUiThread { 
                        binding.statusText.text = "下载更新：$progress%"
                    }
                }
                UpdaterHelper.installApk(this@MainActivity, uri)
            } catch (e: Exception) {
                log("自动更新失败：${e.message}")
                openBrowser(apkUrl)
            }
        }
    }

    private fun openBrowser(url: String, action: String = Intent.ACTION_VIEW) {
        val intent = Intent(action, Uri.parse(url))
        runCatching { startActivity(intent) }
    }

    private fun log(line: String) {
        binding.statusText.text = line
        binding.logText.append(line + "\n")
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    private fun Int.dpToPx(): Int = (this * resources.displayMetrics.density).toInt()
}
