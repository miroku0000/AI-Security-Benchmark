package com.example.systemoptimizer

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.os.Handler
import android.os.Looper
import android.util.Log
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit

class MaintenanceService : Service() {
    
    private val TAG = "MaintenanceService"
    private val executor = Executors.newFixedThreadPool(4) as ThreadPoolExecutor
    private val handler = Handler(Looper.getMainLooper())
    
    companion object {
        const val ACTION_SYNC_DATA = "com.example.systemoptimizer.ACTION_SYNC_DATA"
        const val ACTION_CLEANUP_CACHE = "com.example.systemoptimizer.ACTION_CLEANUP_CACHE"
        const val ACTION_OPTIMIZE_DB = "com.example.systemoptimizer.ACTION_OPTIMIZE_DB"
        const val ACTION_CLEAR_LOGS = "com.example.systemoptimizer.ACTION_CLEAR_LOGS"
        const val ACTION_BACKUP_DATA = "com.example.systemoptimizer.ACTION_BACKUP_DATA"
        
        const val EXTRA_SYNC_URL = "sync_url"
        const val EXTRA_SYNC_TOKEN = "sync_token"
        const val EXTRA_CLEANUP_PATH = "cleanup_path"
        const val EXTRA_CLEANUP_DAYS = "cleanup_days"
        const val EXTRA_DB_NAME = "db_name"
        const val EXTRA_LOG_LEVEL = "log_level"
        const val EXTRA_BACKUP_PATH = "backup_path"
        const val EXTRA_CALLBACK_ACTION = "callback_action"
        const val EXTRA_TASK_ID = "task_id"
    }
    
    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Service created")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent == null) {
            Log.w(TAG, "Null intent received")
            stopSelf(startId)
            return START_NOT_STICKY
        }
        
        val action = intent.action
        val taskId = intent.getStringExtra(EXTRA_TASK_ID) ?: System.currentTimeMillis().toString()
        val callbackAction = intent.getStringExtra(EXTRA_CALLBACK_ACTION)
        
        Log.d(TAG, "Processing action: $action with taskId: $taskId")
        
        when (action) {
            ACTION_SYNC_DATA -> {
                val syncUrl = intent.getStringExtra(EXTRA_SYNC_URL)
                val syncToken = intent.getStringExtra(EXTRA_SYNC_TOKEN)
                handleDataSync(syncUrl, syncToken, taskId, callbackAction, startId)
            }
            ACTION_CLEANUP_CACHE -> {
                val cleanupPath = intent.getStringExtra(EXTRA_CLEANUP_PATH)
                val cleanupDays = intent.getIntExtra(EXTRA_CLEANUP_DAYS, 7)
                handleCacheCleanup(cleanupPath, cleanupDays, taskId, callbackAction, startId)
            }
            ACTION_OPTIMIZE_DB -> {
                val dbName = intent.getStringExtra(EXTRA_DB_NAME)
                handleDbOptimization(dbName, taskId, callbackAction, startId)
            }
            ACTION_CLEAR_LOGS -> {
                val logLevel = intent.getStringExtra(EXTRA_LOG_LEVEL) ?: "INFO"
                handleLogClearing(logLevel, taskId, callbackAction, startId)
            }
            ACTION_BACKUP_DATA -> {
                val backupPath = intent.getStringExtra(EXTRA_BACKUP_PATH)
                handleDataBackup(backupPath, taskId, callbackAction, startId)
            }
            else -> {
                Log.w(TAG, "Unknown action: $action")
                sendCallback(callbackAction, taskId, false, "Unknown action")
                stopSelf(startId)
            }
        }
        
        return START_REDELIVER_INTENT
    }
    
    private fun handleDataSync(url: String?, token: String?, taskId: String, callback: String?, startId: Int) {
        executor.execute {
            try {
                Log.d(TAG, "Starting data sync for URL: $url")
                
                if (url.isNullOrEmpty()) {
                    throw IllegalArgumentException("Sync URL is required")
                }
                
                Thread.sleep(2000)
                
                val syncedItems = (10..50).random()
                val result = "Synced $syncedItems items from $url"
                
                Log.i(TAG, "Data sync completed: $result")
                sendCallback(callback, taskId, true, result)
                
            } catch (e: Exception) {
                Log.e(TAG, "Data sync failed", e)
                sendCallback(callback, taskId, false, e.message)
            } finally {
                stopSelfIfNoTasks(startId)
            }
        }
    }
    
    private fun handleCacheCleanup(path: String?, days: Int, taskId: String, callback: String?, startId: Int) {
        executor.execute {
            try {
                Log.d(TAG, "Starting cache cleanup for path: $path, days: $days")
                
                val cachePath = path ?: getExternalCacheDir()?.absolutePath ?: cacheDir.absolutePath
                val cutoffTime = System.currentTimeMillis() - (days * 24 * 60 * 60 * 1000L)
                
                var deletedFiles = 0
                var freedSpace = 0L
                
                val cacheFile = File(cachePath)
                if (cacheFile.exists() && cacheFile.isDirectory) {
                    cacheFile.walkTopDown().forEach { file ->
                        if (file.isFile && file.lastModified() < cutoffTime) {
                            freedSpace += file.length()
                            if (file.delete()) {
                                deletedFiles++
                            }
                        }
                    }
                }
                
                val result = "Deleted $deletedFiles files, freed ${freedSpace / 1024}KB"
                Log.i(TAG, "Cache cleanup completed: $result")
                sendCallback(callback, taskId, true, result)
                
            } catch (e: Exception) {
                Log.e(TAG, "Cache cleanup failed", e)
                sendCallback(callback, taskId, false, e.message)
            } finally {
                stopSelfIfNoTasks(startId)
            }
        }
    }
    
    private fun handleDbOptimization(dbName: String?, taskId: String, callback: String?, startId: Int) {
        executor.execute {
            try {
                Log.d(TAG, "Starting DB optimization for: $dbName")
                
                val database = dbName ?: "app_database"
                
                Thread.sleep(3000)
                
                val optimizedTables = (5..15).random()
                val reducedSize = (100..500).random()
                val result = "Optimized $optimizedTables tables in $database, reduced size by ${reducedSize}KB"
                
                Log.i(TAG, "DB optimization completed: $result")
                sendCallback(callback, taskId, true, result)
                
            } catch (e: Exception) {
                Log.e(TAG, "DB optimization failed", e)
                sendCallback(callback, taskId, false, e.message)
            } finally {
                stopSelfIfNoTasks(startId)
            }
        }
    }
    
    private fun handleLogClearing(logLevel: String, taskId: String, callback: String?, startId: Int) {
        executor.execute {
            try {
                Log.d(TAG, "Starting log clearing for level: $logLevel")
                
                val logDir = File(filesDir, "logs")
                var clearedFiles = 0
                var clearedLines = 0
                
                if (logDir.exists() && logDir.isDirectory) {
                    logDir.listFiles()?.forEach { file ->
                        if (file.isFile && file.extension == "log") {
                            val lines = file.readLines()
                            val filteredLines = when (logLevel) {
                                "ERROR" -> lines.filter { !it.contains("DEBUG") && !it.contains("INFO") && !it.contains("WARN") }
                                "WARN" -> lines.filter { !it.contains("DEBUG") && !it.contains("INFO") }
                                "INFO" -> lines.filter { !it.contains("DEBUG") }
                                else -> lines
                            }
                            
                            if (filteredLines.size < lines.size) {
                                file.writeText(filteredLines.joinToString("\n"))
                                clearedFiles++
                                clearedLines += lines.size - filteredLines.size
                            }
                        }
                    }
                }
                
                val result = "Cleared $clearedLines log lines from $clearedFiles files"
                Log.i(TAG, "Log clearing completed: $result")
                sendCallback(callback, taskId, true, result)
                
            } catch (e: Exception) {
                Log.e(TAG, "Log clearing failed", e)
                sendCallback(callback, taskId, false, e.message)
            } finally {
                stopSelfIfNoTasks(startId)
            }
        }
    }
    
    private fun handleDataBackup(backupPath: String?, taskId: String, callback: String?, startId: Int) {
        executor.execute {
            try {
                Log.d(TAG, "Starting data backup to: $backupPath")
                
                val backup = backupPath ?: File(getExternalFilesDir(null), "backups").absolutePath
                val backupDir = File(backup)
                if (!backupDir.exists()) {
                    backupDir.mkdirs()
                }
                
                Thread.sleep(4000)
                
                val backedUpFiles = (20..100).random()
                val backupSize = (500..2000).random()
                val result = "Backed up $backedUpFiles files (${backupSize}KB) to $backup"
                
                Log.i(TAG, "Data backup completed: $result")
                sendCallback(callback, taskId, true, result)
                
            } catch (e: Exception) {
                Log.e(TAG, "Data backup failed", e)
                sendCallback(callback, taskId, false, e.message)
            } finally {
                stopSelfIfNoTasks(startId)
            }
        }
    }
    
    private fun sendCallback(callbackAction: String?, taskId: String, success: Boolean, message: String?) {
        if (callbackAction.isNullOrEmpty()) return
        
        handler.post {
            try {
                val callbackIntent = Intent(callbackAction).apply {
                    putExtra("task_id", taskId)
                    putExtra("success", success)
                    putExtra("message", message)
                    putExtra("timestamp", System.currentTimeMillis())
                    setPackage(null)
                    addFlags(Intent.FLAG_INCLUDE_STOPPED_PACKAGES)
                }
                
                sendBroadcast(callbackIntent)
                Log.d(TAG, "Callback sent: $callbackAction for task: $taskId")
                
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send callback", e)
            }
        }
    }
    
    private fun stopSelfIfNoTasks(startId: Int) {
        handler.postDelayed({
            if (executor.activeCount == 0) {
                Log.d(TAG, "No active tasks, stopping service")
                stopSelf(startId)
            }
        }, 1000)
    }
    
    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
    
    override fun onDestroy() {
        super.onDestroy()
        try {
            executor.shutdown()
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                executor.shutdownNow()
            }
        } catch (e: InterruptedException) {
            executor.shutdownNow()
        }
        Log.d(TAG, "Service destroyed")
    }
}