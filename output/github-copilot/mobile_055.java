import android.util.Log
import okhttp3.Headers
import okhttp3.Interceptor
import okhttp3.MediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.Response
import okio.Buffer
import java.io.EOFException
import java.io.IOException
import java.nio.charset.Charset
import java.util.Locale
import java.util.UUID
import java.util.concurrent.TimeUnit

class ProductionDebugLoggingInterceptor(
    private val tag: String = "ApiDebug",
    private val maxBodyBytes: Long = 64L * 1024L,
    private val redactedHeaders: Set<String> = DEFAULT_REDACTED_HEADERS,
    private val redactedQueryParams: Set<String> = DEFAULT_REDACTED_QUERY_PARAMS,
    private val redactedBodyFields: Set<String> = DEFAULT_REDACTED_BODY_FIELDS
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val requestId = UUID.randomUUID().toString().substring(0, 8)

        logRequest(requestId, request)

        val startNanos = System.nanoTime()
        return try {
            val response = chain.proceed(request)
            val tookMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startNanos)
            logResponse(requestId, response, tookMs)
            response
        } catch (e: Exception) {
            Log.i(tag, "[$requestId] HTTP FAILED ${request.method} ${sanitizeUrl(request)}")
            Log.d(tag, "[$requestId] ${e.javaClass.simpleName}: ${e.message.orEmpty()}")
            throw e
        }
    }

    private fun logRequest(requestId: String, request: Request) {
        val url = sanitizeUrl(request)
        val headers = sanitizeHeaders(request.headers)
        val body = readRequestBody(request)

        Log.i(tag, "[$requestId] --> ${request.method} $url")
        if (headers.isNotEmpty()) {
            Log.d(tag, "[$requestId] Request headers:\n$headers")
        }
        if (body.isNotEmpty()) {
            Log.d(tag, "[$requestId] Request body:\n$body")
        }
    }

    private fun logResponse(requestId: String, response: Response, tookMs: Long) {
        val url = sanitizeUrl(response.request)
        val headers = sanitizeHeaders(response.headers)
        val body = readResponseBody(response)

        Log.i(tag, "[$requestId] <-- ${response.code} ${response.message} ${response.request.method} $url (${tookMs}ms)")
        if (headers.isNotEmpty()) {
            Log.d(tag, "[$requestId] Response headers:\n$headers")
        }
        if (body.isNotEmpty()) {
            Log.d(tag, "[$requestId] Response body:\n$body")
        }
    }

    private fun sanitizeUrl(request: Request): String {
        val originalUrl = request.url
        val sanitizedBuilder = originalUrl.newBuilder().query(null)

        for (name in originalUrl.queryParameterNames) {
            val values = originalUrl.queryParameterValues(name)
            val sanitizedValues = if (isSensitiveKey(name, redactedQueryParams)) {
                listOf(REDACTED)
            } else {
                values
            }
            for (value in sanitizedValues) {
                sanitizedBuilder.addQueryParameter(name, value)
            }
        }

        return sanitizedBuilder.build().toString()
    }

    private fun sanitizeHeaders(headers: Headers): String {
        if (headers.size == 0) return ""

        return buildString {
            for (index in 0 until headers.size) {
                val name = headers.name(index)
                val value = headers.value(index)
                val safeValue = if (isSensitiveKey(name, redactedHeaders)) REDACTED else value
                append(name)
                append(": ")
                append(safeValue)
                if (index < headers.size - 1) append('\n')
            }
        }
    }

    private fun readRequestBody(request: Request): String {
        val body = request.body ?: return ""
        if (body.isDuplex() || body.isOneShot()) return "<request body omitted>"
        if (bodyEncoded(request.headers)) return "<encoded request body omitted>"

        val contentLength = safeContentLength(body)
        if (contentLength > maxBodyBytes) {
            return "<request body omitted: ${contentLength} bytes exceeds limit of $maxBodyBytes bytes>"
        }

        val buffer = Buffer()
        return try {
            body.writeTo(buffer)
            renderBuffer(
                buffer = buffer,
                contentType = body.contentType(),
                maxBytes = maxBodyBytes
            )
        } catch (e: IOException) {
            "<failed to read request body: ${e.message.orEmpty()}>"
        }
    }

    private fun readResponseBody(response: Response): String {
        val body = response.body ?: return ""
        if (bodyEncoded(response.headers)) return "<encoded response body omitted>"

        return try {
            val peekedBody = response.peekBody(maxBodyBytes)
            val source = peekedBody.source()
            source.request(Long.MAX_VALUE)
            val buffer = source.buffer.clone()
            renderBuffer(
                buffer = buffer,
                contentType = peekedBody.contentType(),
                maxBytes = maxBodyBytes
            )
        } catch (e: IOException) {
            "<failed to read response body: ${e.message.orEmpty()}>"
        }
    }

    private fun renderBuffer(buffer: Buffer, contentType: MediaType?, maxBytes: Long): String {
        if (buffer.size == 0L) return "<empty>"

        val copy = buffer.clone()
        val limited = Buffer()
        copy.copyTo(limited, 0L, minOf(copy.size, maxBytes))

        if (!isPlaintext(limited)) {
            return "<binary ${contentType?.toString() ?: "body"} omitted>"
        }

        val charset = contentType?.charset(Charsets.UTF_8) ?: Charsets.UTF_8
        val text = limited.readString(charset)
        val redactedText = redactSensitiveFields(text)

        return if (copy.size > maxBytes) {
            "$redactedText\n<truncated to $maxBodyBytes bytes>"
        } else {
            redactedText
        }
    }

    private fun redactSensitiveFields(text: String): String {
        var result = text
        for (field in redactedBodyFields) {
            val escapedField = Regex.escape(field)

            result = result.replace(
                Regex("(?i)(\"$escapedField\"\\s*:\\s*\")([^\"]*)(\")")
            ) { match ->
                match.groupValues[1] + REDACTED + match.groupValues[3]
            }

            result = result.replace(
                Regex("(?i)(\\b$escapedField\\b\\s*=\\s*)([^&\\s,;]+)")
            ) { match ->
                match.groupValues[1] + REDACTED
            }

            result = result.replace(
                Regex("(?i)(<\\s*$escapedField\\s*>)([^<]*)(<\\s*/\\s*$escapedField\\s*>)")
            ) { match ->
                match.groupValues[1] + REDACTED + match.groupValues[3]
            }
        }
        return result
    }

    private fun bodyEncoded(headers: Headers): Boolean {
        val contentEncoding = headers["Content-Encoding"] ?: return false
        return !contentEncoding.equals("identity", ignoreCase = true)
    }

    private fun safeContentLength(body: RequestBody): Long {
        return try {
            body.contentLength()
        } catch (_: IOException) {
            -1L
        }
    }

    private fun isSensitiveKey(name: String, sensitiveKeys: Set<String>): Boolean {
        val normalized = name.lowercase(Locale.US)
        return normalized in sensitiveKeys || normalized.contains("token") || normalized.contains("secret")
    }

    private fun isPlaintext(buffer: Buffer): Boolean {
        return try {
            val prefix = Buffer()
            val byteCount = minOf(buffer.size, 64L)
            buffer.copyTo(prefix, 0L, byteCount)
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

    companion object {
        private const val REDACTED = "██REDACTED██"

        private val DEFAULT_REDACTED_HEADERS = setOf(
            "authorization",
            "proxy-authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "api-key",
            "x-auth-token",
            "x-csrf-token"
        )

        private val DEFAULT_REDACTED_QUERY_PARAMS = setOf(
            "access_token",
            "refresh_token",
            "id_token",
            "token",
            "api_key",
            "apikey",
            "key",
            "password",
            "secret",
            "code"
        )

        private val DEFAULT_REDACTED_BODY_FIELDS = setOf(
            "access_token",
            "refresh_token",
            "id_token",
            "token",
            "authToken",
            "authorization",
            "password",
            "secret",
            "client_secret",
            "apiKey",
            "api_key"
        )
    }
}

object ApiClientFactory {
    fun create(baseClient: OkHttpClient? = null): OkHttpClient {
        val builder = (baseClient ?: OkHttpClient()).newBuilder()
        builder.addInterceptor(ProductionDebugLoggingInterceptor())
        return builder.build()
    }
}