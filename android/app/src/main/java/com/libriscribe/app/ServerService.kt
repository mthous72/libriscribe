package com.libriscribe.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import kotlin.concurrent.thread

/**
 * Runs the embedded uvicorn/FastAPI server on a background thread for the life
 * of the app. A foreground service + partial wake lock keep a multi-minute
 * generation run alive when the screen sleeps.
 */
class ServerService : Service() {

    private var wakeLock: PowerManager.WakeLock? = null
    @Volatile private var started = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (started) return START_STICKY
        started = true

        startForeground(NOTIF_ID, buildNotification())

        wakeLock = (getSystemService(POWER_SERVICE) as PowerManager)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "libriscribe:server")
            .apply { acquire() }

        // Unpack bundled web UI + prompt templates into writable storage the
        // first time, then hand the path to Python.
        val baseDir = filesDir
        extractAssetDir("webdist", File(baseDir, "frontend/dist"))
        extractAssetDir("prompts", File(baseDir, "prompts"))

        thread(name = "libriscribe-server", isDaemon = true) {
            if (!Python.isStarted()) Python.start(AndroidPlatform(this))
            Python.getInstance()
                .getModule("android_main")
                .callAttr("serve", baseDir.absolutePath)
        }
        return START_STICKY
    }

    /** Recursively copy an assets/<name> tree to dest (skips if already present). */
    private fun extractAssetDir(assetPath: String, dest: File) {
        val am = assets
        val entries = am.list(assetPath) ?: return
        if (entries.isEmpty()) {
            // It's a file: copy it.
            dest.parentFile?.mkdirs()
            if (!dest.exists()) am.open(assetPath).use { input ->
                dest.outputStream().use { input.copyTo(it) }
            }
            return
        }
        dest.mkdirs()
        for (entry in entries) extractAssetDir("$assetPath/$entry", File(dest, entry))
    }

    private fun buildNotification(): Notification {
        val channelId = "libriscribe"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId, "LibriScribe", NotificationManager.IMPORTANCE_LOW
            )
            (getSystemService(NOTIFICATION_SERVICE) as NotificationManager)
                .createNotificationChannel(channel)
        }
        return Notification.Builder(this, channelId)
            .setContentTitle("LibriScribe")
            .setContentText("Writing engine running")
            .setSmallIcon(android.R.drawable.ic_menu_edit)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        wakeLock?.let { if (it.isHeld) it.release() }
        super.onDestroy()
    }

    private companion object {
        const val NOTIF_ID = 1
    }
}
