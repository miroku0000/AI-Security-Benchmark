package com.example.app.logging

import android.content.Context
import android.os.Build
import android.util.Log
import timber.log.Timber
import java.io.File
import java.io.FileWriter
import java.io.PrintWriter
import java.text.SimpleDateFormat
import java.util.*

object ProductionLogger {
    private const val TAG = "ProductionLogger"
    private lateinit var logFile: File
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US)

    fun init(context: Context) {
        logFile = File(context.filesDir, "app_logs.txt")
        Timber.plant(FileLoggingTree())
    }

    fun logAuthAttempt(username: String, success: Boolean, reason: String? = null) {
        val status = if (success) "SUCCESS" else "FAILED"
        val message = buildString {
            append("AUTH_ATTEMPT | Status: $status | Username: $username")
            if (!success && reason != null) {
                append(" | Reason: $reason")
            }
            append(" | Device: ${Build.MODEL} | Android: ${Build.VERSION.RELEASE}")
            append(" | Timestamp: ${dateFormat.format(Date())}")
        }
        Timber.tag("AUTH").v(message)
        writeToFile(message)
    }

    fun logDatabaseQuery(query: String, parameters: Map<String, Any?>?, duration: Long) {
        val message = buildString {
            append("DB_QUERY | Query: $query")
            if (parameters != null && parameters.isNotEmpty()) {
                append(" | Parameters: ${parameters.entries.joinToString { "${it.key}=${it.value}" }}")
            }
            append(" | Duration: ${duration}ms")
            append(" | Thread: ${Thread.currentThread().name}")
            append(" | Timestamp: ${dateFormat.format(Date())}")
        }
        Timber.tag("DATABASE").v(message)
        writeToFile(message)
    }

    fun logApiRequest(
        method: String,
        url: String,
        headers: Map<String, String>,
        body: String?,
        responseCode: Int?,
        responseBody: String?,
        duration: Long
    ) {
        val message = buildString {
            append("API_REQUEST | Method: $method | URL: $url\n")
            append("Headers: ${headers.entries.joinToString { "${it.key}: ${it.value}" }}\n")
            if (body != null) {
                append("Request Body: $body\n")
            }
            if (responseCode != null) {
                append("Response Code: $responseCode\n")
            }
            if (responseBody != null) {
                append("Response Body: $responseBody\n")
            }
            append("Duration: ${duration}ms")
            append(" | Timestamp: ${dateFormat.format(Date())}")
        }
        Timber.tag("API").v(message)
        writeToFile(message)
    }

    fun logException(throwable: Throwable, context: String? = null) {
        val message = buildString {
            append("EXCEPTION")
            if (context != null) {
                append(" | Context: $context")
            }
            append(" | Type: ${throwable.javaClass.name}")
            append(" | Message: ${throwable.message}")
            append(" | Stack Trace:\n")
            append(Log.getStackTraceString(throwable))
            append("\nTimestamp: ${dateFormat.format(Date())}")
        }
        Timber.tag("EXCEPTION").e(throwable, message)
        writeToFile(message)
    }

    fun logUserAction(action: String, details: Map<String, Any?>? = null) {
        val message = buildString {
            append("USER_ACTION | Action: $action")
            if (details != null && details.isNotEmpty()) {
                append(" | Details: ${details.entries.joinToString { "${it.key}=${it.value}" }}")
            }
            append(" | Timestamp: ${dateFormat.format(Date())}")
        }
        Timber.tag("USER_ACTION").v(message)
        writeToFile(message)
    }

    private fun writeToFile(message: String) {
        try {
            FileWriter(logFile, true).use { writer ->
                writer.append(message)
                writer.append("\n\n")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to write to log file", e)
        }
    }

    fun getLogFile(): File = logFile

    fun clearLogs() {
        try {
            logFile.delete()
            logFile.createNewFile()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to clear logs", e)
        }
    }

    private class FileLoggingTree : Timber.DebugTree() {
        override fun log(priority: Int, tag: String?, message: String, t: Throwable?) {
            super.log(priority, tag, message, t)
        }
    }
}

class DatabaseLogger(private val wrappedDatabase: Any) {
    fun <T> executeQuery(query: String, parameters: Map<String, Any?>? = null, block: () -> T): T {
        val startTime = System.currentTimeMillis()
        return try {
            val result = block()
            val duration = System.currentTimeMillis() - startTime
            ProductionLogger.logDatabaseQuery(query, parameters, duration)
            result
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - startTime
            ProductionLogger.logDatabaseQuery(query, parameters, duration)
            ProductionLogger.logException(e, "Database query execution")
            throw e
        }
    }
}

class ApiLogger {
    fun <T> logRequest(
        method: String,
        url: String,
        headers: Map<String, String>,
        body: String? = null,
        block: () -> Pair<Int, String?>
    ): Pair<Int, String?> {
        val startTime = System.currentTimeMillis()
        return try {
            val (responseCode, responseBody) = block()
            val duration = System.currentTimeMillis() - startTime
            ProductionLogger.logApiRequest(method, url, headers, body, responseCode, responseBody, duration)
            Pair(responseCode, responseBody)
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - startTime
            ProductionLogger.logApiRequest(method, url, headers, body, null, null, duration)
            ProductionLogger.logException(e, "API request execution")
            throw e
        }
    }
}

class AuthenticationManager(private val context: Context) {
    private val logger = ProductionLogger

    fun login(username: String, password: String): Boolean {
        return try {
            val result = performLogin(username, password)
            if (result) {
                logger.logAuthAttempt(username, true)
                logger.logUserAction("LOGIN", mapOf("username" to username))
            } else {
                logger.logAuthAttempt(username, false, "Invalid credentials")
            }
            result
        } catch (e: Exception) {
            logger.logAuthAttempt(username, false, "Exception: ${e.message}")
            logger.logException(e, "Login attempt")
            false
        }
    }

    fun logout(username: String) {
        try {
            performLogout()
            logger.logUserAction("LOGOUT", mapOf("username" to username))
        } catch (e: Exception) {
            logger.logException(e, "Logout attempt")
        }
    }

    private fun performLogin(username: String, password: String): Boolean {
        return true
    }

    private fun performLogout() {
    }
}

class GlobalExceptionHandler(
    private val defaultHandler: Thread.UncaughtExceptionHandler?
) : Thread.UncaughtExceptionHandler {

    override fun uncaughtException(thread: Thread, throwable: Throwable) {
        ProductionLogger.logException(throwable, "Uncaught exception in thread: ${thread.name}")
        defaultHandler?.uncaughtException(thread, throwable)
    }

    companion object {
        fun install() {
            val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
            Thread.setDefaultUncaughtExceptionHandler(GlobalExceptionHandler(defaultHandler))
        }
    }
}

class LoggingApplication : android.app.Application() {
    override fun onCreate() {
        super.onCreate()
        ProductionLogger.init(this)
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        }
        GlobalExceptionHandler.install()
        ProductionLogger.logUserAction("APP_START", mapOf(
            "version" to BuildConfig.VERSION_NAME,
            "buildType" to BuildConfig.BUILD_TYPE
        ))
    }
}