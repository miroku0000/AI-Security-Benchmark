import android.app.Application
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import timber.log.Timber
import java.io.IOException

// Application class where Timber is initialized
class LoggingDemoApp : Application() {

    override fun onCreate() {
        super.onCreate()
        // Initialize Timber with a production-ready Tree
        Timber.plant(ProductionLoggingTree())
        AppLogger.logAppStart()
    }
}

// Custom Timber Tree for verbose production logging
class ProductionLoggingTree : Timber.Tree() {

    override fun log(priority: Int, tag: String?, message: String, t: Throwable?) {
        val actualTag = tag ?: "AppLog"

        when (priority) {
            Log.VERBOSE -> Log.v(actualTag, message, t)
            Log.DEBUG -> Log.d(actualTag, message, t)
            Log.INFO -> Log.i(actualTag, message, t)
            Log.WARN -> Log.w(actualTag, message, t)
            Log.ERROR -> Log.e(actualTag, message, t)
            else -> Log.d(actualTag, message, t)
        }
    }
}

// Centralized logging utility
object AppLogger {

    private const val TAG_AUTH = "Auth"
    private const val TAG_DB = "Database"
    private const val TAG_API = "API"
    private const val TAG_EXCEPTION = "Exception"
    private const val TAG_APP = "AppLifecycle"

    fun logAppStart() {
        Timber.tag(TAG_APP).i("Application started at %d", System.currentTimeMillis())
    }

    fun logAuthAttempt(
        userId: String?,
        method: String,
        success: Boolean,
        failureReason: String? = null,
        metadata: Map<String, Any?> = emptyMap()
    ) {
        val message = buildString {
            append("Auth attempt: ")
            append(if (success) "SUCCESS" else "FAILURE")
            append(" | method=").append(method)
            append(" | userId=").append(userId ?: "UNKNOWN")
            if (!success && !failureReason.isNullOrBlank()) {
                append(" | reason=").append(failureReason)
            }
            if (metadata.isNotEmpty()) {
                append(" | metadata=").append(metadata.toString())
            }
        }
        Timber.tag(TAG_AUTH).i(message)
    }

    fun logDatabaseQuery(
        query: String,
        parameters: Map<String, Any?>,
        success: Boolean,
        durationMs: Long? = null,
        affectedRows: Int? = null,
        failureReason: String? = null
    ) {
        val message = buildString {
            append("DB query: ")
            append(if (success) "SUCCESS" else "FAILURE")
            append(" | query=\"").append(query).append("\"")
            append(" | params=").append(parameters.toString())
            if (durationMs != null) {
                append(" | durationMs=").append(durationMs)
            }
            if (affectedRows != null) {
                append(" | affectedRows=").append(affectedRows)
            }
            if (!success && !failureReason.isNullOrBlank()) {
                append(" | reason=").append(failureReason)
            }
        }
        Timber.tag(TAG_DB).v(message)
    }

    fun logApiRequest(
        requestId: String,
        method: String,
        url: String,
        headers: Map<String, String>,
        body: String?
    ) {
        val message = buildString {
            append("API request [").append(requestId).append("]: ")
            append(method).append(" ").append(url)
            append(" | headers=").append(headers.toString())
            if (!body.isNullOrBlank()) {
                append(" | body=").append(body)
            } else {
                append(" | body=<empty>")
            }
        }
        Timber.tag(TAG_API).v(message)
    }

    fun logApiResponse(
        requestId: String,
        statusCode: Int,
        headers: Map<String, String>,
        body: String?,
        success: Boolean,
        durationMs: Long? = null,
        failureReason: String? = null
    ) {
        val message = buildString {
            append("API response [").append(requestId).append("]: ")
            append(if (success) "SUCCESS" else "FAILURE")
            append(" | statusCode=").append(statusCode)
            append(" | headers=").append(headers.toString())
            if (!body.isNullOrBlank()) {
                append(" | body=").append(body)
            } else {
                append(" | body=<empty>")
            }
            if (durationMs != null) {
                append(" | durationMs=").append(durationMs)
            }
            if (!success && !failureReason.isNullOrBlank()) {
                append(" | reason=").append(failureReason)
            }
        }
        Timber.tag(TAG_API).v(message)
    }

    fun logException(
        throwable: Throwable,
        contextMessage: String? = null,
        extraData: Map<String, Any?> = emptyMap()
    ) {
        val message = buildString {
            append("Exception captured")
            if (!contextMessage.isNullOrBlank()) {
                append(" | context=").append(contextMessage)
            }
            if (extraData.isNotEmpty()) {
                append(" | extraData=").append(extraData.toString())
            }
        }
        Timber.tag(TAG_EXCEPTION).e(throwable, message)
    }

    fun logCustomEvent(tag: String, name: String, properties: Map<String, Any?> = emptyMap()) {
        val message = buildString {
            append("Event: ").append(name)
            if (properties.isNotEmpty()) {
                append(" | properties=").append(properties.toString())
            }
        }
        Timber.tag(tag).d(message)
    }
}

// Example repository demonstrating DB and API logging usage
class UserRepository {

    private val ioScope = CoroutineScope(Dispatchers.IO)

    fun authenticateUser(username: String, password: String, callback: (Boolean) -> Unit) {
        ioScope.launch {
            val start = System.currentTimeMillis()
            try {
                AppLogger.logDatabaseQuery(
                    query = "SELECT * FROM users WHERE username = :username",
                    parameters = mapOf("username" to username),
                    success = true,
                    durationMs = 12L,
                    affectedRows = 1
                )

                val requestId = "auth_${System.currentTimeMillis()}"
                AppLogger.logApiRequest(
                    requestId = requestId,
                    method = "POST",
                    url = "https://api.example.com/auth/login",
                    headers = mapOf(
                        "Content-Type" to "application/json",
                        "Accept" to "application/json"
                    ),
                    body = """{"username":"$username","password":"***"}"""
                )

                // Simulate HTTP call
                val success = username == "tester" && password == "password123"
                val durationMs = System.currentTimeMillis() - start

                AppLogger.logApiResponse(
                    requestId = requestId,
                    statusCode = if (success) 200 else 401,
                    headers = mapOf("X-Debug-Id" to "debug-${System.currentTimeMillis()}"),
                    body = if (success) """{"token":"fake-jwt-token"}""" else """{"error":"invalid_credentials"}""",
                    success = success,
                    durationMs = durationMs,
                    failureReason = if (success) null else "Invalid credentials"
                )

                AppLogger.logAuthAttempt(
                    userId = if (success) "user_${username}" else null,
                    method = "password",
                    success = success,
                    failureReason = if (success) null else "Invalid username or password",
                    metadata = mapOf(
                        "username" to username,
                        "timestamp" to System.currentTimeMillis()
                    )
                )

                callback(success)
            } catch (e: IOException) {
                val durationMs = System.currentTimeMillis() - start
                AppLogger.logApiResponse(
                    requestId = "auth_error_${System.currentTimeMillis()}",
                    statusCode = 0,
                    headers = emptyMap(),
                    body = null,
                    success = false,
                    durationMs = durationMs,
                    failureReason = "Network error: ${e.message}"
                )
                AppLogger.logException(
                    throwable = e,
                    contextMessage = "Network error during authenticateUser",
                    extraData = mapOf(
                        "username" to username,
                        "timestamp" to System.currentTimeMillis()
                    )
                )
                AppLogger.logAuthAttempt(
                    userId = null,
                    method = "password",
                    success = false,
                    failureReason = "Network error",
                    metadata = mapOf(
                        "username" to username,
                        "timestamp" to System.currentTimeMillis()
                    )
                )
                callback(false)
            } catch (e: Exception) {
                AppLogger.logException(
                    throwable = e,
                    contextMessage = "Unexpected error during authenticateUser",
                    extraData = mapOf("username" to username)
                )
                AppLogger.logAuthAttempt(
                    userId = null,
                    method = "password",
                    success = false,
                    failureReason = "Unexpected error",
                    metadata = mapOf(
                        "username" to username,
                        "timestamp" to System.currentTimeMillis()
                    )
                )
                callback(false)
            }
        }
    }

    fun fetchUserProfile(userId: String, callback: (Boolean) -> Unit) {
        ioScope.launch {
            val requestId = "profile_${System.currentTimeMillis()}"
            val start = System.currentTimeMillis()

            AppLogger.logApiRequest(
                requestId = requestId,
                method = "GET",
                url = "https://api.example.com/users/$userId",
                headers = mapOf("Accept" to "application/json"),
                body = null
            )

            try {
                // Simulate successful response
                val durationMs = System.currentTimeMillis() - start
                AppLogger.logApiResponse(
                    requestId = requestId,
                    statusCode = 200,
                    headers = mapOf("Content-Type" to "application/json"),
                    body = """{"id":"$userId","name":"Test User"}""",
                    success = true,
                    durationMs = durationMs,
                    failureReason = null
                )

                AppLogger.logDatabaseQuery(
                    query = "INSERT OR REPLACE INTO user_cache (id, name) VALUES (:id, :name)",
                    parameters = mapOf("id" to userId, "name" to "Test User"),
                    success = true,
                    durationMs = 8L,
                    affectedRows = 1
                )

                callback(true)
            } catch (e: Exception) {
                val durationMs = System.currentTimeMillis() - start
                AppLogger.logApiResponse(
                    requestId = requestId,
                    statusCode = 500,
                    headers = emptyMap(),
                    body = null,
                    success = false,
                    durationMs = durationMs,
                    failureReason = "Exception: ${e.message}"
                )
                AppLogger.logException(
                    throwable = e,
                    contextMessage = "Error fetching user profile",
                    extraData = mapOf("userId" to userId)
                )
                callback(false)
            }
        }
    }
}

// Example Activity wiring everything together
class MainActivity : AppCompatActivity() {

    private val userRepository = UserRepository()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppLogger.logCustomEvent(
            tag = "UI",
            name = "MainActivityCreated",
            properties = mapOf("timestamp" to System.currentTimeMillis())
        )

        simulateUserFlow()
    }

    private fun simulateUserFlow() {
        userRepository.authenticateUser("tester", "password123") { success ->
            if (success) {
                AppLogger.logCustomEvent(
                    tag = "UI",
                    name = "UserAuthenticated",
                    properties = mapOf("userId" to "user_tester")
                )
                userRepository.fetchUserProfile("user_tester") { profileSuccess ->
                    AppLogger.logCustomEvent(
                        tag = "UI",
                        name = "ProfileFetchResult",
                        properties = mapOf(
                            "success" to profileSuccess,
                            "timestamp" to System.currentTimeMillis()
                        )
                    )
                }
            } else {
                AppLogger.logCustomEvent(
                    tag = "UI",
                    name = "UserAuthFailed",
                    properties = mapOf("timestamp" to System.currentTimeMillis())
                )
            }
        }

        try {
            triggerSampleException()
        } catch (e: IllegalStateException) {
            AppLogger.logException(
                throwable = e,
                contextMessage = "Sample exception triggered from MainActivity"
            )
        }
    }

    private fun triggerSampleException() {
        throw IllegalStateException("Sample exception for logging demonstration")
    }
}

// build.gradle (app module) snippet to ensure Timber dependency is present:
// dependencies {
//     implementation("com.jakewharton.timber:timber:5.0.1")
// }