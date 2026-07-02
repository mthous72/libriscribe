package com.libriscribe.app

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

/**
 * Hosts the LibriScribe web UI in a WebView. The Python backend runs in a
 * foreground service (ServerService); here we just wait for it to answer on
 * localhost, then point the WebView at it.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private val baseUrl = "http://127.0.0.1:8000"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this)
        setContentView(webView)
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true          // Zustand/localStorage
            mediaPlaybackRequiresUserGesture = false
        }
        webView.webViewClient = WebViewClient()

        val svc = Intent(this, ServerService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(svc)
        } else {
            startService(svc)
        }

        scope.launch { waitForServerThenLoad() }
    }

    /** Poll /api/health for up to ~60s (first launch unpacks Python + assets). */
    private suspend fun waitForServerThenLoad() {
        val ready = withContext(Dispatchers.IO) {
            repeat(120) {
                try {
                    val c = URL("$baseUrl/api/health").openConnection() as HttpURLConnection
                    c.connectTimeout = 500
                    c.readTimeout = 500
                    val code = c.responseCode
                    c.disconnect()
                    if (code in 200..299) return@withContext true
                } catch (_: Exception) {
                    // server not up yet
                }
                delay(500)
            }
            false
        }
        if (ready) webView.loadUrl(baseUrl)
    }

    override fun onDestroy() {
        scope.cancel()
        // Leave the service running if you want generation to continue in the
        // background; stop it here for a "close = stop" behavior.
        stopService(Intent(this, ServerService::class.java))
        super.onDestroy()
    }
}
