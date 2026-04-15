import android.content.Context
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Simple HTTP/HTTPS client for:
 * - Local IoT devices (e.g. 192.168.x.x)
 * - Cloud API
 *
 * Uses OkHttp under the hood.
 */
class IoTHttpClient private constructor(
    private val cloudBaseUrl: String,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
    // You can inject a custom OkHttpClient if needed (e.g., for custom TLS)
    private val okHttpClient: OkHttpClient = defaultClient()
) {

    companion object {

        private const val DEFAULT_CONNECT_TIMEOUT_SECONDS = 10L
        private const val DEFAULT_READ_TIMEOUT_SECONDS = 30L
        private const val DEFAULT_WRITE_TIMEOUT_SECONDS = 30L

        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()

        fun create(
            context: Context,
            cloudBaseUrl: String,
            ioDispatcher: CoroutineDispatcher = Dispatchers.IO
        ): IoTHttpClient {
            return IoTHttpClient(
                cloudBaseUrl = cloudBaseUrl.trimEnd('/'),
                ioDispatcher = ioDispatcher,
                okHttpClient = defaultClient()
            )
        }

        private fun defaultClient(): OkHttpClient {
            return OkHttpClient.Builder()
                .connectTimeout(DEFAULT_CONNECT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                .readTimeout(DEFAULT_READ_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                .writeTimeout(DEFAULT_WRITE_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                .followRedirects(true)
                .followSslRedirects(true)
                .retryOnConnectionFailure(true)
                .build()
        }
    }

    // region Public API

    /**
     * Perform a GET request against a local device.
     *
     * @param scheme "http" or "https"
     * @param deviceHost e.g. "192.168.1.50"
     * @param port optional port, null uses default for scheme
     * @param path path segment (e.g. "/status")
     * @param headers optional extra headers
     */
    suspend fun getLocalDevice(
        scheme: String = "http",
        deviceHost: String,
        port: Int? = null,
        path: String = "/",
        headers: Map<String, String> = emptyMap()
    ): HttpResult {
        val url = buildUrl(
            scheme = scheme,
            host = deviceHost,
            port = port,
            path = path
        )
        return executeGet(url, headers)
    }

    /**
     * Perform a POST request against a local device.
     *
     * @param scheme "http" or "https"
     * @param deviceHost e.g. "192.168.1.50"
     * @param port optional port, null uses default for scheme
     * @param path path segment (e.g. "/configure")
     * @param jsonBody optional JSON string body
     * @param headers optional extra headers
     */
    suspend fun postLocalDevice(
        scheme: String = "http",
        deviceHost: String,
        port: Int? = null,
        path: String = "/",
        jsonBody: String? = null,
        headers: Map<String, String> = emptyMap()
    ): HttpResult {
        val url = buildUrl(
            scheme = scheme,
            host = deviceHost,
            port = port,
            path = path
        )
        return executePost(url, jsonBody, headers)
    }

    /**
     * Perform a GET request against the cloud API.
     *
     * @param path path under cloudBaseUrl (e.g. "/v1/devices")
     * @param query optional query string (without '?')
     * @param headers optional extra headers (e.g. auth)
     */
    suspend fun getCloud(
        path: String,
        query: String? = null,
        headers: Map<String, String> = emptyMap()
    ): HttpResult {
        val url = buildCloudUrl(path, query)
        return executeGet(url, headers)
    }

    /**
     * Perform a POST request against the cloud API.
     *
     * @param path path under cloudBaseUrl (e.g. "/v1/devices")
     * @param query optional query string (without '?')
     * @param jsonBody optional JSON string body
     * @param headers optional extra headers (e.g. auth)
     */
    suspend fun postCloud(
        path: String,
        query: String? = null,
        jsonBody: String? = null,
        headers: Map<String, String> = emptyMap()
    ): HttpResult {
        val url = buildCloudUrl(path, query)
        return executePost(url, jsonBody, headers)
    }

    // endregion

    // region Internal helpers

    private fun buildCloudUrl(path: String, query: String?): String {
        val normalizedPath = path.trim()
        val full = if (normalizedPath.startsWith("/")) {
            "$cloudBaseUrl$normalizedPath"
        } else {
            "$cloudBaseUrl/$normalizedPath"
        }
        return if (!query.isNullOrBlank()) {
            "$full?$query"
        } else {
            full
        }
    }

    private fun buildUrl(
        scheme: String,
        host: String,
        port: Int?,
        path: String
    ): String {
        val normalizedScheme = when (scheme.lowercase()) {
            "http", "https" -> scheme.lowercase()
            else -> "http"
        }

        val normalizedHost = host.trim().trimEnd('/')

        val normalizedPath = when {
            path.isBlank() -> ""
            path.startsWith("/") -> path
            else -> "/$path"
        }

        val portPart = port?.let { ":$it" } ?: ""

        return "$normalizedScheme://$normalizedHost$portPart$normalizedPath"
    }

    private suspend fun executeGet(
        url: String,
        headers: Map<String, String>
    ): HttpResult = withContext(ioDispatcher) {
        val builder = Request.Builder().url(url)
        for ((k, v) in headers) {
            builder.addHeader(k, v)
        }

        val request = builder.get().build()

        runCatching {
            okHttpClient.newCall(request).execute().use { resp ->
                resp.toHttpResult()
            }
        }.getOrElse { throwable ->
            HttpResult(error = throwable)
        }
    }

    private suspend fun executePost(
        url: String,
        jsonBody: String?,
        headers: Map<String, String>
    ): HttpResult = withContext(ioDispatcher) {
        val body: RequestBody = (jsonBody ?: "")
            .toRequestBody(JSON_MEDIA_TYPE)

        val builder = Request.Builder().url(url)
        for ((k, v) in headers) {
            builder.addHeader(k, v)
        }

        val request = builder.post(body).build()

        runCatching {
            okHttpClient.newCall(request).execute().use { resp ->
                resp.toHttpResult()
            }
        }.getOrElse { throwable ->
            HttpResult(error = throwable)
        }
    }

    private fun Response.toHttpResult(): HttpResult {
        return try {
            val responseBody = body?.string()
            HttpResult(
                code = code,
                body = responseBody,
                headers = headers.toMultimap(),
                error = null
            )
        } catch (io: IOException) {
            HttpResult(
                code = code,
                body = null,
                headers = headers.toMultimap(),
                error = io
            )
        }
    }

    // endregion
}

/**
 * Simple wrapper around HTTP response data.
 */
data class HttpResult(
    val code: Int? = null,
    val body: String? = null,
    val headers: Map<String, List<String>> = emptyMap(),
    val error: Throwable? = null
) {
    val isSuccessful: Boolean
        get() = error == null && code != null && code in 200..299
}

/**
 * Example of how you might use IoTHttpClient from a ViewModel or similar:
 *
 * class ExampleViewModel(
 *     app: Application
 * ) : AndroidViewModel(app) {
 *
 *     private val client = IoTHttpClient.create(
 *         context = app,
 *         cloudBaseUrl = "https://api.your-cloud.com"
 *     )
 *
 *     fun pingLocalDevice() {
 *         viewModelScope.launch {
 *             val result = client.getLocalDevice(
 *                 scheme = "http",
 *                 deviceHost = "192.168.1.50",
 *                 path = "/ping"
 *             )
 *             // Handle result
 *         }
 *     }
 * }
 */