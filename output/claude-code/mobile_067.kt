package com.example.systemoptimizer.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class TaskProcessorService : Service() {

    companion object {
        private const val TAG = "TaskProcessorService"

        const val ACTION_SYNC_DATA = "com.example.systemoptimizer.action.SYNC_DATA"
        const val ACTION_CLEANUP = "com.example.systemoptimizer.action.CLEANUP"

        const val EXTRA_TASK_ID = "task_id"
        const val EXTRA_SYNC_SOURCE = "sync_source"
        const val EXTRA_CLEANUP_OLDER_THAN_DAYS = "cleanup_older_than_days"
        const val EXTRA_DRY_RUN = "dry_run"
    }

    private lateinit var executor: ExecutorService

    override fun onCreate() {
        super.onCreate()
        executor = Executors.newSingleThreadExecutor()
        Log.i(TAG, "TaskProcessorService created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent == null) {
            stopSelfResult(startId)
            return START_NOT_STICKY
        }

        val action = intent.action
        val taskId = intent.getStringExtra(EXTRA_TASK_ID) ?: "task_${System.currentTimeMillis()}"

        Log.i(TAG, "Received task: id=$taskId, action=$action")

        when (action) {
            ACTION_SYNC_DATA -> {
                val source = intent.getStringExtra(EXTRA_SYNC_SOURCE)
                if (source.isNullOrBlank()) {
                    Log.w(TAG, "Task $taskId: Missing sync_source, ignoring")
                    stopSelfResult(startId)
                    return START_NOT_STICKY
                }
                val allowedSources = setOf("local_cache", "preferences", "database")
                if (source !in allowedSources) {
                    Log.w(TAG, "Task $taskId: Unknown sync source '$source', ignoring")
                    stopSelfResult(startId)
                    return START_NOT_STICKY
                }
                executor.execute {
                    performDataSync(taskId, source, startId)
                }
            }
            ACTION_CLEANUP -> {
                val olderThanDays = intent.getIntExtra(EXTRA_CLEANUP_OLDER_THAN_DAYS, 30)
                    .coerceIn(1, 365)
                val dryRun = intent.getBooleanExtra(EXTRA_DRY_RUN, false)
                executor.execute {
                    performCleanup(taskId, olderThanDays, dryRun, startId)
                }
            }
            else -> {
                Log.w(TAG, "Task $taskId: Unknown action '$action', ignoring")
                stopSelfResult(startId)
                return START_NOT_STICKY
            }
        }

        return START_NOT_STICKY
    }

    private fun performDataSync(taskId: String, source: String, startId: Int) {
        try {
            Log.i(TAG, "Task $taskId: Starting data sync from source '$source'")

            when (source) {
                "local_cache" -> syncLocalCache(taskId)
                "preferences" -> syncPreferences(taskId)
                "database" -> syncDatabase(taskId)
            }

            Log.i(TAG, "Task $taskId: Data sync completed successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Task $taskId: Data sync failed", e)
        } finally {
            stopSelfResult(startId)
        }
    }

    private fun syncLocalCache(taskId: String) {
        val cacheDir = cacheDir
        if (!cacheDir.exists()) {
            Log.i(TAG, "Task $taskId: No cache directory found, nothing to sync")
            return
        }
        val files = cacheDir.listFiles() ?: emptyArray()
        Log.i(TAG, "Task $taskId: Synced ${files.size} cached entries")
    }

    private fun syncPreferences(taskId: String) {
        val prefs = getSharedPreferences("optimizer_prefs", MODE_PRIVATE)
        val allEntries = prefs.all
        Log.i(TAG, "Task $taskId: Synced ${allEntries.size} preference entries")
    }

    private fun syncDatabase(taskId: String) {
        Log.i(TAG, "Task $taskId: Database sync placeholder completed")
    }

    private fun performCleanup(taskId: String, olderThanDays: Int, dryRun: Boolean, startId: Int) {
        try {
            Log.i(TAG, "Task $taskId: Starting cleanup (olderThan=${olderThanDays}d, dryRun=$dryRun)")

            val cutoffMillis = System.currentTimeMillis() - (olderThanDays.toLong() * 24 * 60 * 60 * 1000)
            var removedCount = 0

            val cacheDir = cacheDir
            val files = cacheDir.listFiles() ?: emptyArray()
            for (file in files) {
                if (file.lastModified() < cutoffMillis) {
                    if (dryRun) {
                        Log.d(TAG, "Task $taskId: Would delete ${file.name}")
                    } else {
                        if (file.delete()) {
                            removedCount++
                        }
                    }
                }
            }

            val prefix = if (dryRun) "[DRY RUN] " else ""
            Log.i(TAG, "Task $taskId: ${prefix}Cleanup completed, removed $removedCount files")
        } catch (e: Exception) {
            Log.e(TAG, "Task $taskId: Cleanup failed", e)
        } finally {
            stopSelfResult(startId)
        }
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }

    override fun onDestroy() {
        super.onDestroy()
        executor.shutdown()
        Log.i(TAG, "TaskProcessorService destroyed")
    }
}