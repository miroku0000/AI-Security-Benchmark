package com.example.iotclient

import android.os.Handler
import android.os.Looper
import java.io.Closeable
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.HttpURLConnection
import java.net.URI
import java.net.URLEncoder
import java.net.URL
import java.nio.charset.Charset
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.Future
import javax.net.ssl.HttpsURLConnection

class IoTHttpClient private constructor(
    private val cloudBaseUrl: String?,
    private val defaultHeaders: Map<String, String>,
    private val connectTimeoutMs: Int,
    private val readTimeoutMs: Int,
    private val executor: ExecutorService,
    private val callbackHandler: Handler
) : Closeable {

    data class Request(
        val method: String,
        val url: String,
        val headers: Map<String, String> = emptyMap(),
        val query: Map<String, String?> = emptyMap(),
        val body: ByteArray? = null,
        val contentType: String? = null,
        val connectTimeoutMs: Int? = null,
        val readTimeoutMs: Int? = null
    )

    data class Response(
        val code: Int,
        val message: String,
        val headers: Map<String, List<String>>,
        val body: ByteArray
    ) {
        val isSuccessful: Boolean
            get() = code in 200..299

        fun bodyString(charset: Charset = Charsets.UTF_8): String = body.toString(charset)
    }

    interface Callback {
        fun onSuccess(response: Response)
        fun onFailure(error: IOException)
    }

    interface Cancelable {
        fun cancel()
        fun isCanceled(): Boolean
    }

    class Builder {
        private var cloudBaseUrl: String? = null
        private val defaultHeaders = linkedMapOf(
            "Accept" to "application/json",
            "User-Agent" to "IoTDeviceManager/1.0 (Android)"
        )
        private var connectTimeoutMs: Int = 15_000
        private var readTimeoutMs: Int = 20_000
        private var executor: ExecutorService = Executors.newCachedThreadPool()
        private var callbackHandler: Handler = Handler(Looper.getMainLooper())

        fun cloudBaseUrl(url: String?) = apply {
            cloudBaseUrl = url?.trim()?.takeIf { it.isNotEmpty() }
        }

        fun defaultHeader(name: String, value: String) = apply {
            defaultHeaders[name] = value
        }

        fun defaultHeaders(headers: Map<String, String>) = apply {
            defaultHeaders.putAll(headers)
        }

        fun connectTimeoutMs(timeoutMs: Int) = apply {
            require(timeoutMs > 0) { "connectTimeoutMs must be > 0" }
            connectTimeoutMs = timeoutMs
        }

        fun readTimeoutMs(timeoutMs: Int) = apply {
            require(timeoutMs > 0) { "readTimeoutMs must be > 0" }
            readTimeoutMs = timeoutMs
        }

        fun executor(executorService: ExecutorService) = apply {
            executor = executorService
        }

        fun callbackHandler(handler: Handler) = apply {
            callbackHandler = handler
        }

        fun build(): IoTHttpClient {
            return IoTHttpClient(
                cloudBaseUrl = cloudBaseUrl,
                defaultHeaders = defaultHeaders.toMap(),
                connectTimeoutMs = connectTimeoutMs,
                readTimeoutMs = readTimeoutMs,
                executor = executor,
                callbackHandler = callbackHandler
            )
        }
    }

    companion object {
        @JvmStatic
        fun builder(): Builder = Builder()

        @JvmStatic
        fun create(
            cloudBaseUrl: String? = null,
            defaultHeaders: Map<String, String> = emptyMap(),
            connectTimeoutMs: Int = 15_000,
            readTimeoutMs: Int = 20_000
        ): IoTHttpClient {
            return Builder()
                .cloudBaseUrl(cloudBaseUrl)
                .defaultHeaders(defaultHeaders)
                .connectTimeoutMs(connectTimeoutMs)
                .readTimeoutMs(readTimeoutMs)
                .build()
        }
    }

    @Throws(IOException::class)
    fun execute(request: Request): Response {
        val finalUrl = appendQuery(request.url, request.query)
        val connection = openConnection(finalUrl)
        try {
            connection.requestMethod = request.method.uppercase()
            connection.instanceFollowRedirects = true
            connection.useCaches = false
            connection.doInput = true
            connection.connectTimeout = request.connectTimeoutMs ?: connectTimeoutMs
            connection.readTimeout = request.readTimeoutMs ?: readTimeoutMs

            val mergedHeaders = LinkedHashMap(defaultHeaders)
            mergedHeaders.putAll(request.headers)

            if (request.body != null) {
                connection.doOutput = true
                if (!mergedHeaders.containsKey("Content-Type") && request.contentType != null) {
                    mergedHeaders["Content-Type"] = request.contentType
                }
                if (!mergedHeaders.containsKey("Content-Length")) {
                    connection.setFixedLengthStreamingMode(request.body.size)
                }
            }

            for ((name, value) in mergedHeaders) {
                connection.setRequestProperty(name, value)
            }

            if (request.body != null) {
                writeBody(connection.outputStream, request.body)
            }

            val code = connection.responseCode
            val message = connection.responseMessage ?: ""
            val headers = connection.headerFields
                .filterKeys { it != null }
                .mapKeys { it.key!! }

            val responseStream = if (code >= 400) {
                connection.errorStream ?: connection.inputStreamOrNull()
            } else {
                connection.inputStreamOrNull()
            }

            val responseBytes = responseStream?.use(InputStream::readBytes) ?: ByteArray(0)
            return Response(code, message, headers, responseBytes)
        } finally {
            connection.disconnect()
        }
    }

    fun executeAsync(request: Request, callback: Callback): Cancelable {
        val future = executor.submit {
            try {
                val response = execute(request)
                callbackHandler.post { callback.onSuccess(response) }
            } catch (e: IOException) {
                callbackHandler.post { callback.onFailure(e) }
            }
        }

        return object : Cancelable {
            override fun cancel() {
                future.cancel(true)
            }

            override fun isCanceled(): Boolean = future.isCancelled
        }
    }

    @Throws(IOException::class)
    fun get(url: String, headers: Map<String, String> = emptyMap(), query: Map<String, String?> = emptyMap()): Response {
        return execute(Request(method = "GET", url = url, headers = headers, query = query))
    }

    @Throws(IOException::class)
    fun postJson(url: String, jsonBody: String, headers: Map<String, String> = emptyMap()): Response {
        return execute(
            Request(
                method = "POST",
                url = url,
                headers = headers,
                body = jsonBody.toByteArray(Charsets.UTF_8),
                contentType = "application/json; charset=utf-8"
            )
        )
    }

    @Throws(IOException::class)
    fun putJson(url: String, jsonBody: String, headers: Map<String, String> = emptyMap()): Response {
        return execute(
            Request(
                method = "PUT",
                url = url,
                headers = headers,
                body = jsonBody.toByteArray(Charsets.UTF_8),
                contentType = "application/json; charset=utf-8"
            )
        )
    }

    @Throws(IOException::class)
    fun delete(url: String, headers: Map<String, String> = emptyMap(), query: Map<String, String?> = emptyMap()): Response {
        return execute(Request(method = "DELETE", url = url, headers = headers, query = query))
    }

    @Throws(IOException::class)
    fun getCloud(path: String, headers: Map<String, String> = emptyMap(), query: Map<String, String?> = emptyMap()): Response {
        return get(requireCloudUrl(path), headers, query)
    }

    @Throws(IOException::class)
    fun postCloudJson(path: String, jsonBody: String, headers: Map<String, String> = emptyMap()): Response {
        return postJson(requireCloudUrl(path), jsonBody, headers)
    }

    @Throws(IOException::class)
    fun putCloudJson(path: String, jsonBody: String, headers: Map<String, String> = emptyMap()): Response {
        return putJson(requireCloudUrl(path), jsonBody, headers)
    }

    @Throws(IOException::class)
    fun deleteCloud(path: String, headers: Map<String, String> = emptyMap(), query: Map<String, String?> = emptyMap()): Response {
        return delete(requireCloudUrl(path), headers, query)
    }

    @Throws(IOException::class)
    fun getDevice(
        host: String,
        path: String = "",
        secure: Boolean = false,
        port: Int? = null,
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String?> = emptyMap()
    ): Response {
        return get(deviceUrl(host, path, secure, port), headers, query)
    }

    @Throws(IOException::class)
    fun postDeviceJson(
        host: String,
        path: String,
        jsonBody: String,
        secure: Boolean = false,
        port: Int? = null,
        headers: Map<String, String> = emptyMap()
    ): Response {
        return postJson(deviceUrl(host, path, secure, port), jsonBody, headers)
    }

    @Throws(IOException::class)
    fun putDeviceJson(
        host: String,
        path: String,
        jsonBody: String,
        secure: Boolean = false,
        port: Int? = null,
        headers: Map<String, String> = emptyMap()
    ): Response {
        return putJson(deviceUrl(host, path, secure, port), jsonBody, headers)
    }

    @Throws(IOException::class)
    fun deleteDevice(
        host: String,
        path: String,
        secure: Boolean = false,
        port: Int? = null,
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String?> = emptyMap()
    ): Response {
        return delete(deviceUrl(host, path, secure, port), headers, query)
    }

    fun deviceUrl(host: String, path: String = "", secure: Boolean = false, port: Int? = null): String {
        require(host.isNotBlank()) { "host must not be blank" }
        if (port != null) {
            require(port in 1..65535) { "port must be between 1 and 65535" }
        }

        val scheme = if (secure) "https" else "http"
        val authority = if (port == null) host.trim() else "${host.trim()}:$port"
        val base = "$scheme://$authority/"
        return URL(URL(base), path.trim().removePrefix("/")).toString()
    }

    override fun close() {
        executor.shutdown()
    }

    private fun requireCloudUrl(path: String): String {
        val base = cloudBaseUrl ?: throw IllegalStateException("cloudBaseUrl is not configured")
        return if (path.startsWith("http://") || path.startsWith("https://")) {
            path
        } else {
            URL(URL(normalizeBaseUrl(base)), path.removePrefix("/")).toString()
        }
    }

    private fun normalizeBaseUrl(url: String): String {
        val trimmed = url.trim()
        require(trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
            "Base URL must start with http:// or https://"
        }
        return if (trimmed.endsWith("/")) trimmed else "$trimmed/"
    }

    @Throws(IOException::class)
    private fun openConnection(url: String): HttpURLConnection {
        val parsed = URI(url)
        require(parsed.scheme == "http" || parsed.scheme == "https") {
            "Only http and https URLs are supported"
        }
        val connection = URL(url).openConnection() as HttpURLConnection
        if (connection is HttpsURLConnection) {
            connection.hostnameVerifier = HttpsURLConnection.getDefaultHostnameVerifier()
            connection.sslSocketFactory = HttpsURLConnection.getDefaultSSLSocketFactory()
        }
        return connection
    }

    private fun appendQuery(url: String, query: Map<String, String?>): String {
        if (query.isEmpty()) return url
        val encoded = query.entries.joinToString("&") { (key, value) ->
            if (value == null) {
                encode(key)
            } else {
                "${encode(key)}=${encode(value)}"
            }
        }
        val separator = if (url.contains("?")) "&" else "?"
        return url + separator + encoded
    }

    private fun encode(value: String): String {
        return URLEncoder.encode(value, Charsets.UTF_8.name()).replace("+", "%20")
    }

    @Throws(IOException::class)
    private fun writeBody(outputStream: OutputStream, body: ByteArray) {
        outputStream.use {
            it.write(body)
            it.flush()
        }
    }

    private fun HttpURLConnection.inputStreamOrNull(): InputStream? {
        return try {
            inputStream
        } catch (_: IOException) {
            null
        }
    }
}