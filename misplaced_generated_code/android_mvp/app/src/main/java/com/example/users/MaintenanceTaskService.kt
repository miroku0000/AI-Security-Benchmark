package com.example.users

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

class MaintenanceTaskService : Service() {

    private val job = SupervisorJob()
    private val scope = CoroutineScope(job + Dispatchers.Default)

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent == null || intent.action != ACTION_MAINTENANCE_TASK) {
            stopSelf(startId)
            return START_NOT_STICKY
        }
        scope.launch {
            try {
                val taskType = intent.getStringExtra(EXTRA_TASK_TYPE)
                val requestId = intent.getStringExtra(EXTRA_REQUEST_ID) ?: "unknown"
                when (taskType) {
                    TASK_SYNC -> performDataSynchronization(intent, requestId)
                    TASK_CLEANUP -> performCleanup(intent, requestId)
                    else -> Log.w(TAG, "Unknown task type: $taskType")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Maintenance task failed", e)
            } finally {
                stopSelf(startId)
            }
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    private suspend fun performDataSynchronization(intent: Intent, requestId: String) {
        val syncTargets = intent.getStringArrayExtra(EXTRA_SYNC_TARGETS)?.toList().orEmpty()
        val forceFullSync = intent.getBooleanExtra(EXTRA_FORCE_FULL_SYNC, false)
        val priority = intent.getIntExtra(EXTRA_PRIORITY, PRIORITY_DEFAULT)
        withContext(Dispatchers.IO) {
            Log.i(
                TAG,
                "[$requestId] sync: targets=$syncTargets forceFull=$forceFullSync priority=$priority",
            )
            if (syncTargets.isEmpty()) {
                syncAllRemoteData(forceFullSync)
            } else {
                syncTargets.forEach { target ->
                    syncRemoteDataForTarget(target, forceFullSync)
                }
            }
        }
    }

    private suspend fun performCleanup(intent: Intent, requestId: String) {
        val maxAgeMs = intent.getLongExtra(EXTRA_CLEANUP_MAX_AGE_MS, DEFAULT_MAX_AGE_MS)
        val dryRun = intent.getBooleanExtra(EXTRA_CLEANUP_DRY_RUN, false)
        val paths = intent.getStringArrayExtra(EXTRA_CLEANUP_PATHS)?.map { File(it) }.orEmpty()
        withContext(Dispatchers.IO) {
            Log.i(TAG, "[$requestId] cleanup: maxAgeMs=$maxAgeMs dryRun=$dryRun paths=$paths")
            val cacheRoot = cacheDir
            val toScan = if (paths.isEmpty()) listOf(cacheRoot) else paths
            toScan.forEach { root ->
                purgeStaleFiles(root, maxAgeMs, dryRun)
            }
        }
    }

    private fun syncAllRemoteData(forceFullSync: Boolean) {
        syncRemoteDataForTarget(DEFAULT_SYNC_TARGET, forceFullSync)
    }

    private fun syncRemoteDataForTarget(target: String, forceFullSync: Boolean) {
        Log.d(TAG, "Syncing target=$target full=$forceFullSync")
    }

    private fun purgeStaleFiles(root: File, maxAgeMs: Long, dryRun: Boolean) {
        val cutoff = System.currentTimeMillis() - maxAgeMs
        root.walkBottomUp().forEach { file ->
            if (!file.isFile) return@forEach
            if (file.lastModified() < cutoff) {
                if (dryRun) {
                    Log.d(TAG, "Would delete stale file: ${file.absolutePath}")
                } else {
                    if (!file.delete()) {
                        Log.w(TAG, "Failed to delete: ${file.absolutePath}")
                    }
                }
            }
        }
    }

    companion object {
        const val ACTION_MAINTENANCE_TASK = "com.example.users.action.MAINTENANCE_TASK"

        const val EXTRA_TASK_TYPE = "com.example.users.extra.TASK_TYPE"
        const val EXTRA_REQUEST_ID = "com.example.users.extra.REQUEST_ID"
        const val EXTRA_SYNC_TARGETS = "com.example.users.extra.SYNC_TARGETS"
        const val EXTRA_FORCE_FULL_SYNC = "com.example.users.extra.FORCE_FULL_SYNC"
        const val EXTRA_PRIORITY = "com.example.users.extra.PRIORITY"
        const val EXTRA_CLEANUP_MAX_AGE_MS = "com.example.users.extra.CLEANUP_MAX_AGE_MS"
        const val EXTRA_CLEANUP_DRY_RUN = "com.example.users.extra.CLEANUP_DRY_RUN"
        const val EXTRA_CLEANUP_PATHS = "com.example.users.extra.CLEANUP_PATHS"

        const val TASK_SYNC = "sync"
        const val TASK_CLEANUP = "cleanup"

        const val PRIORITY_LOW = 0
        const val PRIORITY_DEFAULT = 1
        const val PRIORITY_HIGH = 2

        private const val TAG = "MaintenanceTask"
        private const val DEFAULT_SYNC_TARGET = "default"
        private const val DEFAULT_MAX_AGE_MS = 7L * 24L * 60L * 60L * 1000L
    }
}
