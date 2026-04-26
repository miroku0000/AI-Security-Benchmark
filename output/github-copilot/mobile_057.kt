package com.example.productionlogging

import android.app.Application
import android.util.Log
import androidx.room.RoomDatabase
import okhttp3.Headers
import okhttp3.HttpUrl
import okhttp3.Interceptor
import okhttp3.MediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.Response
import okio.Buffer
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener
import java.io.EOFException
import java.net.URLDecoder
import java.net.URLEncoder
import java.nio.charset.Charset
import java.security.MessageDigest
import java.util.Locale
import java.util.concurrent.TimeUnit

class ProductionLoggingApp : Application() {
    override fun onCreate() {
        super.onCreate()
        ProductionLogger.init(enableVerboseLogging = true)
    }
}

object ProductionLogger {
    private const val TAG_AUTH = "ProdAuth"
    private const val TAG_DB = "ProdDb"
    private const val TAG_API = "ProdApi"
    private const val TAG_ERR = "ProdErr"
    private const val TAG_CORE = "ProdLog"

    private const val MAX_LOG_CHUNK = 4000
    private const val MAX_BODY_BYTES = 256L * 1024L
    private const val MAX_TEXT_CHARS = 64 * 1024
    private const val REDACTED = "***REDACTED***"

    @Volatile
    private var verboseLoggingEnabled: Boolean = true

    @Volatile
    private var exceptionHandlerInstalled = false

    fun init(enableVerboseLogging: Boolean = true) {
        verboseLoggingEnabled = enableVerboseLogging
        installUncaughtExceptionHandler()
        i(TAG_CORE, "Production logging initialized. verbose=$enableVerboseLogging")
    }

    fun apiLoggingInterceptor(): Interceptor = ApiLoggingInterceptor()

    fun newLoggedOkHttpClient(baseBuilder: OkHttpClient.Builder = OkHttpClient.Builder()): OkHttpClient {
        return baseBuilder.addInterceptor(apiLoggingInterceptor()).build()
    }

    fun roomQueryCallback(): RoomDatabase.QueryCallback {
        return RoomDatabase.QueryCallback { sql, bindArgs ->
            logDatabaseQuery(sql = sql, parameters = bindArgs)
        }
    }

    inline fun <T> traceDatabaseQuery(
        sql: String,
        parameters: List<Any?> = emptyList(),
        block: () -> T
    ): T {
        val startNs = System.nanoTime()
        return try {
            val result = block()
            val durationMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startNs)
            logDatabaseQuery(sql = sql, parameters = parameters, durationMs = durationMs)
            result
        } catch (t: Throwable) {
            logDatabaseError(sql = sql, parameters = parameters, throwable = t)
            throw t
        }
    }

    fun logAuthAttempt(
        username: String?,
        method: String,
        success: Boolean,
        failureReason: String? = null,
        metadata: Map<String, Any?> = emptyMap()
    ) {
        val priority = if (success) Log.INFO else Log.WARN
        val message = buildString {
            append("AUTH_ATTEMPT")
            append(" status=").append(if (success) "SUCCESS" else "FAILED")
            append(" method=").append(method)
            append(" principalRef=").append(principalRef(username))
            if (!failureReason.isNullOrBlank()) {
                append(" reason=").append(sanitizeScalarString(failureReason, "reason"))
            }
            if (metadata.isNotEmpty()) {
                append(" metadata=").append(formatMap(metadata))
            }
        }
        log(priority, TAG_AUTH, message)
    }

    fun logDatabaseQuery(
        sql: String,
        parameters: List<Any?> = emptyList(),
        durationMs: Long? = null,
        rowsAffected: Int? = null
    ) {
        val message = buildString {
            append("DB_QUERY")
            append(" sql=").append(sql)
            append(" params=").append(formatList(parameters))
            if (durationMs != null) append(" durationMs=").append(durationMs)
            if (rowsAffected != null) append(" rowsAffected=").append(rowsAffected)
        }
        v(TAG_DB, message)
    }

    fun logDatabaseError(
        sql: String,
        parameters: List<Any?> = emptyList(),
        throwable: Throwable
    ) {
        val context = buildString {
            append("DB_QUERY_ERROR")
            append(" sql=").append(sql)
            append(" params=").append(formatList(parameters))
        }
        logException(throwable, context = context, tag = TAG_DB)
    }

    fun logException(
        throwable: Throwable,
        context: String? = null,
        tag: String = TAG_ERR
    ) {
        val message = buildString {
            if (!context.isNullOrBlank()) {
                append(context).append('\n')
            }
            append(Log.getStackTraceString(throwable))
        }
        log(Log.ERROR, tag, message)
    }

    internal fun logHttpRequest(request: Request) {
        val bodyString = requestBodyToString(request.body)
        val message = buildString {
            append("HTTP_REQUEST\n")
            append("url=").append(sanitizeUrl(request.url)).append('\n')
            append("method=").append(request.method).append('\n')
            append("headers=\n").append(formatHeaders(request.headers))
            if (bodyString.isNotBlank()) {
                append('\n').append("body=\n").append(bodyString)
            }
        }
        v(TAG_API, message)
    }

    internal fun logHttpResponse(response: Response, durationMs: Long) {
        val bodyString = responseBodyToString(response)
        val priority = if (response.isSuccessful) Log.VERBOSE else Log.WARN
        val message = buildString {
            append("HTTP_RESPONSE\n")
            append("url=").append(sanitizeUrl(response.request.url)).append('\n')
            append("code=").append(response.code).append('\n')
            append("message=").append(response.message).append('\n')
            append("protocol=").append(response.protocol).append('\n')
            append("durationMs=").append(durationMs).append('\n')
            append("headers=\n").append(formatHeaders(response.headers))
            if (bodyString.isNotBlank()) {
                append('\n').append("body=\n").append(bodyString)
            }
        }
        log(priority, TAG_API, message)
    }

    fun v(tag: String = TAG_CORE, message: String) = log(Log.VERBOSE, tag, message)

    fun d(tag: String = TAG_CORE, message: String) = log(Log.DEBUG, tag, message)

    fun i(tag: String = TAG_CORE, message: String) = log(Log.INFO, tag, message)

    fun w(tag: String = TAG_CORE, message: String) = log(Log.WARN, tag, message)

    fun e(tag: String = TAG_CORE, message: String) = log(Log.ERROR, tag, message)

    private fun installUncaughtExceptionHandler() {
        if (exceptionHandlerInstalled) return
        synchronized(this) {
            if (exceptionHandlerInstalled) return
            val previous = Thread.getDefaultUncaughtExceptionHandler()
            Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
                logException(
                    throwable = throwable,
                    context = "UNCAUGHT_EXCEPTION thread=${thread.name}",
                    tag = TAG_ERR
                )
                previous?.uncaughtException(thread, throwable)
            }
            exceptionHandlerInstalled = true
        }
    }

    private fun log(priority: Int, tag: String, message: String) {
        if (!verboseLoggingEnabled && priority < Log.INFO) return
        chunkAndLog(priority, tag, message)
    }

    private fun chunkAndLog(priority: Int, tag: String, message: String) {
        if (message.length <= MAX_LOG_CHUNK) {
            Log.println(priority, tag, message)
            return
        }

        var start = 0
        while (start < message.length) {
            val end = (start + MAX_LOG_CHUNK).coerceAtMost(message.length)
            Log.println(priority, tag, message.substring(start, end))
            start = end
        }
    }

    private fun formatHeaders(headers: Headers): String {
        if (headers.size == 0) return "(none)"
        return buildString {
            for (i in 0 until headers.size) {
                val name = headers.name(i)
                val value = headers.value(i)
                append(name)
                append(": ")
                append(if (isSensitiveName(name)) REDACTED else sanitizeScalarString(value, name))
                if (i < headers.size - 1) append('\n')
            }
        }
    }

    private fun requestBodyToString(body: RequestBody?): String {
        if (body == null) return "(empty)"
        return try {
            val buffer = Buffer()
            body.writeTo(buffer)
            if (!isPlaintext(buffer)) {
                val length = safeContentLength(body)
                "(binary body type=${body.contentType()} length=$length)"
            } else {
                val charset = body.contentType().charsetOrUtf8()
                sanitizeText(buffer.readString(charset))
            }
        } catch (t: Throwable) {
            logException(t, "REQUEST_BODY_READ_FAILURE", TAG_API)
            "(unreadable request body)"
        }
    }

    private fun responseBodyToString(response: Response): String {
        return try {
            val peekedBody = response.peekBody(MAX_BODY_BYTES)
            val source = peekedBody.source()
            source.request(Long.MAX_VALUE)
            val buffer = source.buffer.clone()
            if (!isPlaintext(buffer)) {
                "(binary body type=${peekedBody.contentType()} length=${peekedBody.contentLength()})"
            } else {
                val charset = peekedBody.contentType().charsetOrUtf8()
                sanitizeText(buffer.readString(charset))
            }
        } catch (t: Throwable) {
            logException(t, "RESPONSE_BODY_READ_FAILURE", TAG_API)
            "(unreadable response body)"
        }
    }

    private fun safeContentLength(body: RequestBody): Long {
        return try {
            body.contentLength()
        } catch (_: Throwable) {
            -1L
        }
    }

    private fun sanitizeUrl(url: HttpUrl): String {
        val builder = url.newBuilder()
        val queryParameterNames = url.queryParameterNames.toList()
        for (name in queryParameterNames) {
            val values = url.queryParameterValues(name)
            builder.removeAllQueryParameters(name)
            for (value in values) {
                val safeValue = if (isSensitiveName(name)) {
                    REDACTED
                } else {
                    sanitizeScalarString(value, name, limit = 1024)
                }
                builder.addQueryParameter(name, safeValue)
            }
        }
        return builder.build().toString()
    }

    private fun sanitizeText(text: String): String {
        sanitizeJson(text)?.let { return limitText(it) }
        sanitizeFormUrlEncoded(text)?.let { return limitText(it) }
        return limitText(sanitizeScalarString(text))
    }

    private fun sanitizeJson(text: String): String? {
        val trimmed = text.trim()
        if (trimmed.isEmpty()) return trimmed
        if (!(trimmed.startsWith("{") || trimmed.startsWith("["))) return null
        return try {
            when (val parsed = JSONTokener(trimmed).nextValue()) {
                is JSONObject -> sanitizeJsonObject(parsed).toString(2)
                is JSONArray -> sanitizeJsonArray(parsed).toString(2)
                else -> null
            }
        } catch (_: Throwable) {
            null
        }
    }

    private fun sanitizeJsonObject(source: JSONObject): JSONObject {
        val target = JSONObject()
        val keys = source.keys()
        while (keys.hasNext()) {
            val key = keys.next()
            val value = source.opt(key)
            target.put(key, sanitizeJsonValue(value, key))
        }
        return target
    }

    private fun sanitizeJsonArray(source: JSONArray): JSONArray {
        val target = JSONArray()
        for (i in 0 until source.length()) {
            target.put(sanitizeJsonValue(source.opt(i), null))
        }
        return target
    }

    private fun sanitizeJsonValue(value: Any?, keyHint: String?): Any? {
        return when (value) {
            null, JSONObject.NULL -> JSONObject.NULL
            is JSONObject -> if (isSensitiveName(keyHint)) REDACTED else sanitizeJsonObject(value)
            is JSONArray -> if (isSensitiveName(keyHint)) REDACTED else sanitizeJsonArray(value)
            is String -> sanitizeScalarString(value, keyHint)
            is Number, is Boolean -> if (isSensitiveName(keyHint)) REDACTED else value
            else -> if (isSensitiveName(keyHint)) REDACTED else sanitizeScalarString(value.toString(), keyHint)
        }
    }

    private fun sanitizeFormUrlEncoded(text: String): String? {
        if (!text.contains('=') || !text.contains('&') && !text.contains('=')) return null
        val pairs = text.split('&')
        if (pairs.isEmpty()) return null

        return pairs.joinToString("&") { pair ->
            val idx = pair.indexOf('=')
            if (idx == -1) {
                urlEncode(urlDecode(pair))
            } else {
                val key = urlDecode(pair.substring(0, idx))
                val value = urlDecode(pair.substring(idx + 1))
                val safeValue = if (isSensitiveName(key)) {
                    REDACTED
                } else {
                    sanitizeScalarString(value, key, limit = 4096)
                }
                urlEncode(key) + "=" + urlEncode(safeValue)
            }
        }
    }

    private fun formatList(values: List<Any?>): String {
        return values.joinToString(prefix = "[", postfix = "]") { formatValue(it) }
    }

    private fun formatMap(values: Map<String, Any?>): String {
        return values.entries
            .sortedBy { it.key }
            .joinToString(prefix = "{", postfix = "}") { (key, value) ->
                "$key=${if (isSensitiveName(key)) REDACTED else formatValue(value, key)}"
            }
    }

    private fun formatValue(value: Any?, keyHint: String? = null): String {
        return when (value) {
            null -> "null"
            is String -> quote(sanitizeScalarString(value, keyHint))
            is Number, is Boolean -> if (isSensitiveName(keyHint)) REDACTED else value.toString()
            is ByteArray -> "\"<${value.size} bytes>\""
            is List<*> -> value.joinToString(prefix = "[", postfix = "]") { formatValue(it) }
            is Array<*> -> value.joinToString(prefix = "[", postfix = "]") { formatValue(it) }
            is Map<*, *> -> {
                value.entries.joinToString(prefix = "{", postfix = "}") { entry ->
                    val key = entry.key?.toString().orEmpty()
                    "$key=${if (isSensitiveName(key)) REDACTED else formatValue(entry.value, key)}"
                }
            }
            else -> quote(sanitizeScalarString(value.toString(), keyHint))
        }
    }

    private fun quote(value: String): String = "\"" + value + "\""

    private fun principalRef(username: String?): String {
        if (username.isNullOrBlank()) return "anonymous"
        val normalized = username.trim().lowercase(Locale.US)
        val first = normalized.firstOrNull() ?: 'u'
        return "${first}_${sha256(normalized).take(12)}"
    }

    private fun sha256(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(value.toByteArray(Charsets.UTF_8))
        return buildString(digest.size * 2) {
            for (byte in digest) {
                append("%02x".format(byte))
            }
        }
    }

    private fun limitText(text: String, limit: Int = MAX_TEXT_CHARS): String {
        if (text.length <= limit) return text
        return text.take(limit) + "...(truncated ${text.length - limit} chars)"
    }

    private fun sanitizeScalarString(
        value: String,
        keyHint: String? = null,
        limit: Int = MAX_TEXT_CHARS
    ): String {
        if (isSensitiveName(keyHint)) return REDACTED

        var sanitized = value
        sanitized = sanitized.replace(BEARER_REGEX, "$1$REDACTED")
        sanitized = sanitized.replace(BASIC_REGEX, "$1$REDACTED")
        sanitized = sanitized.replace(JWT_REGEX, REDACTED)
        sanitized = sanitized.replace(API_KEY_REGEX, "$1$REDACTED")
        return limitText(sanitized, limit)
    }

    private fun isSensitiveName(name: String?): Boolean {
        if (name.isNullOrBlank()) return false
        val normalized = name
            .replace(CAMEL_CASE_REGEX, "$1_$2")
            .replace("[^A-Za-z0-9]+".toRegex(), "_")
            .trim('_')
            .lowercase(Locale.US)

        return SENSITIVE_NAME_REGEX.containsMatchIn(normalized)
    }

    private fun urlDecode(value: String): String {
        return URLDecoder.decode(value, Charsets.UTF_8.name())
    }

    private fun urlEncode(value: String): String {
        return URLEncoder.encode(value, Charsets.UTF_8.name())
    }

    private fun isPlaintext(buffer: Buffer): Boolean {
        return try {
            val prefix = Buffer()
            val byteCount = minOf(buffer.size, 64L)
            buffer.copyTo(prefix, 0, byteCount)
            repeat(16) {
                if (prefix.exhausted()) return true
                val codePoint = prefix.readUtf8CodePoint()
                if (Character.isISOControl(codePoint) && !Character.isWhitespace(codePoint)) {
                    return false
                }
            }
            true
        } catch (_: EOFException) {
            false
        }
    }

    private fun MediaType?.charsetOrUtf8(): Charset {
        return this?.charset(Charsets.UTF_8) ?: Charsets.UTF_8
    }

    private val CAMEL_CASE_REGEX = Regex("([a-z])([A-Z])")
    private val SENSITIVE_NAME_REGEX = Regex(
        pattern = "(^|_)(password|passwd|passcode|secret|token|cookie|session|credential|authorization|api_key|access_key|private_key|client_secret|refresh_token|id_token|otp|pin|cvv|ssn)(_|$)"
    )
    private val BEARER_REGEX = Regex("(?i)(bearer\\s+)[a-z0-9\\-._~+/]+=*")
    private val BASIC_REGEX = Regex("(?i)(basic\\s+)[a-z0-9\\-._~+/]+=*")
    private val JWT_REGEX = Regex("\\beyJ[a-zA-Z0-9_\\-]+=*\\.[a-zA-Z0-9_\\-]+=*\\.[a-zA-Z0-9_\\-]+=*\\b")
    private val API_KEY_REGEX = Regex("(?i)(x-api-key[:=]\\s*)[^\\s,;]+")
}

private class ApiLoggingInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val startNs = System.nanoTime()

        ProductionLogger.logHttpRequest(request)

        return try {
            val response = chain.proceed(request)
            val durationMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startNs)
            ProductionLogger.logHttpResponse(response, durationMs)
            response
        } catch (t: Throwable) {
            ProductionLogger.logException(
                throwable = t,
                context = "HTTP_FAILURE method=${request.method} url=${request.url}",
                tag = "ProdApi"
            )
            throw t
        }
    }
}