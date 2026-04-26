package com.example.iotclient

import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

sealed class Endpoint {
    data object Cloud : Endpoint()
    data class Device(
        val host: String,
        val port: Int? = null,
        val useHttps: Boolean = false
    ) : Endpoint()
}

data class HttpResult(
    val code: Int,
    val body: String,
    val headers: Map<String, String>
)

class LocalCloudHttpClient(
    private val client: OkHttpClient = defaultClient()
) {
    fun get(
        endpoint: Endpoint,
        path: String = "/",
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String> = emptyMap()
    ): HttpResult {
        val request = buildRequest(
            endpoint = endpoint,
            method = "GET",
            path = path,
            headers = headers,
            query = query,
            body = null
        )
        return execute(request)
    }

    fun delete(
        endpoint: Endpoint,
        path: String = "/",
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String> = emptyMap()
    ): HttpResult {
        val request = buildRequest(
            endpoint = endpoint,
            method = "DELETE",
            path = path,
            headers = headers,
            query = query,
            body = null
        )
        return execute(request)
    }

    fun postJson(
        endpoint: Endpoint,
        path: String,
        jsonBody: String,
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String> = emptyMap()
    ): HttpResult {
        return sendWithBody(
            endpoint = endpoint,
            method = "POST",
            path = path,
            body = jsonBody.toRequestBody(JSON),
            headers = headers,
            query = query
        )
    }

    fun putJson(
        endpoint: Endpoint,
        path: String,
        jsonBody: String,
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String> = emptyMap()
    ): HttpResult {
        return sendWithBody(
            endpoint = endpoint,
            method = "PUT",
            path = path,
            body = jsonBody.toRequestBody(JSON),
            headers = headers,
            query = query
        )
    }

    fun patchJson(
        endpoint: Endpoint,
        path: String,
        jsonBody: String,
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String> = emptyMap()
    ): HttpResult {
        return sendWithBody(
            endpoint = endpoint,
            method = "PATCH",
            path = path,
            body = jsonBody.toRequestBody(JSON),
            headers = headers,
            query = query
        )
    }

    fun post(
        endpoint: Endpoint,
        path: String,
        body: RequestBody,
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String> = emptyMap()
    ): HttpResult {
        return sendWithBody(endpoint, "POST", path, body, headers, query)
    }

    fun put(
        endpoint: Endpoint,
        path: String,
        body: RequestBody,
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String> = emptyMap()
    ): HttpResult {
        return sendWithBody(endpoint, "PUT", path, body, headers, query)
    }

    fun patch(
        endpoint: Endpoint,
        path: String,
        body: RequestBody,
        headers: Map<String, String> = emptyMap(),
        query: Map<String, String> = emptyMap()
    ): HttpResult {
        return sendWithBody(endpoint, "PATCH", path, body, headers, query)
    }

    private fun sendWithBody(
        endpoint: Endpoint,
        method: String,
        path: String,
        body: RequestBody,
        headers: Map<String, String>,
        query: Map<String, String>
    ): HttpResult {
        val request = buildRequest(
            endpoint = endpoint,
            method = method,
            path = path,
            headers = headers,
            query = query,
            body = body
        )
        return execute(request)
    }

    private fun buildRequest(
        endpoint: Endpoint,
        method: String,
        path: String,
        headers: Map<String, String>,
        query: Map<String, String>,
        body: RequestBody?
    ): Request {
        val requestBuilder = Request.Builder()
            .url(buildUrl(endpoint, path, query))

        headers.forEach { (name, value) ->
            requestBuilder.header(name, value)
        }

        when (method) {
            "GET" -> requestBuilder.get()
            "DELETE" -> requestBuilder.delete()
            "POST", "PUT", "PATCH" -> requestBuilder.method(
                method,
                body ?: ByteArray(0).toRequestBody(null)
            )
            else -> throw IllegalArgumentException("Unsupported method: $method")
        }

        return requestBuilder.build()
    }

    private fun buildUrl(
        endpoint: Endpoint,
        path: String,
        query: Map<String, String>
    ): HttpUrl {
        val builder = when (endpoint) {
            Endpoint.Cloud -> CLOUD_BASE_URL.toHttpUrl().newBuilder()
            is Endpoint.Device -> {
                val host = endpoint.host.trim()
                require(isAllowedLocalHost(host)) {
                    "Device host must be a local/private network address"
                }

                HttpUrl.Builder()
                    .scheme(if (endpoint.useHttps) "https" else "http")
                    .host(host)
                    .apply {
                        endpoint.port?.let { port ->
                            require(port in 1..65535) { "Port must be between 1 and 65535" }
                            port(port)
                        }
                    }
            }
        }

        val normalizedPath = path.trim().removePrefix("/")
        if (normalizedPath.isNotEmpty()) {
            normalizedPath.split('/')
                .filter { it.isNotEmpty() }
                .forEach { segment -> builder.addPathSegment(segment) }
        }

        query.forEach { (name, value) ->
            builder.addQueryParameter(name, value)
        }

        return builder.build()
    }

    private fun execute(request: Request): HttpResult {
        client.newCall(request).execute().use { response ->
            val responseBody = response.body?.string().orEmpty()
            val responseHeaders = response.headers.names().associateWith { name ->
                response.header(name).orEmpty()
            }

            if (!response.isSuccessful) {
                throw IOException("HTTP ${response.code}: $responseBody")
            }

            return HttpResult(
                code = response.code,
                body = responseBody,
                headers = responseHeaders
            )
        }
    }

    private fun isAllowedLocalHost(host: String): Boolean {
        if (host == "localhost" || host.endsWith(".local", ignoreCase = true)) {
            return true
        }
        return isPrivateIpv4(host)
    }

    private fun isPrivateIpv4(host: String): Boolean {
        val parts = host.split(".")
        if (parts.size != 4) return false

        val octets = parts.mapNotNull { it.toIntOrNull() }
        if (octets.size != 4 || octets.any { it !in 0..255 }) return false

        val a = octets[0]
        val b = octets[1]

        return when {
            a == 10 -> true
            a == 172 && b in 16..31 -> true
            a == 192 && b == 168 -> true
            a == 169 && b == 254 -> true
            a == 127 -> true
            else -> false
        }
    }

    companion object {
        private const val CLOUD_BASE_URL = "https://api.example.com"
        private val JSON = "application/json; charset=utf-8".toMediaType()

        fun defaultClient(): OkHttpClient {
            return OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(20, TimeUnit.SECONDS)
                .writeTimeout(20, TimeUnit.SECONDS)
                .callTimeout(30, TimeUnit.SECONDS)
                .retryOnConnectionFailure(true)
                .build()
        }
    }
}

// app/src/main/java/com/example/iotclient/MainActivity.kt
package com.example.iotclient

import android.os.Bundle
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private val client = LocalCloudHttpClient()

    private lateinit var deviceHostInput: EditText
    private lateinit var devicePortInput: EditText
    private lateinit var devicePathInput: EditText
    private lateinit var cloudPathInput: EditText
    private lateinit var bodyInput: EditText
    private lateinit var httpsSwitch: Switch
    private lateinit var outputView: TextView
    private lateinit var getDeviceButton: Button
    private lateinit var postDeviceButton: Button
    private lateinit var getCloudButton: Button
    private lateinit var postCloudButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "IoT HTTP Client"

        val root = ScrollView(this)
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val padding = dp(16)
            setPadding(padding, padding, padding, padding)
        }

        deviceHostInput = input("Device host", "192.168.1.100")
        devicePortInput = input("Device port (optional)", "")
        devicePathInput = input("Device path", "/status")
        cloudPathInput = input("Cloud path", "/status")
        bodyInput = input("JSON body", """{"ping":true}""")
        httpsSwitch = Switch(this).apply {
            text = "Use HTTPS for device"
        }

        getDeviceButton = button("GET Device") {
            runRequest {
                client.get(
                    endpoint = deviceEndpoint(),
                    path = devicePathInput.text.toString().ifBlank { "/" }
                )
            }
        }

        postDeviceButton = button("POST Device JSON") {
            runRequest {
                client.postJson(
                    endpoint = deviceEndpoint(),
                    path = devicePathInput.text.toString().ifBlank { "/" },
                    jsonBody = bodyInput.text.toString()
                )
            }
        }

        getCloudButton = button("GET Cloud") {
            runRequest {
                client.get(
                    endpoint = Endpoint.Cloud,
                    path = cloudPathInput.text.toString().ifBlank { "/" }
                )
            }
        }

        postCloudButton = button("POST Cloud JSON") {
            runRequest {
                client.postJson(
                    endpoint = Endpoint.Cloud,
                    path = cloudPathInput.text.toString().ifBlank { "/" },
                    jsonBody = bodyInput.text.toString()
                )
            }
        }

        outputView = TextView(this).apply {
            text = "Ready"
            setTextIsSelectable(true)
        }

        content.addView(label("Device"))
        content.addView(deviceHostInput)
        content.addView(devicePortInput)
        content.addView(devicePathInput)
        content.addView(httpsSwitch)
        content.addView(spacer())

        content.addView(label("Cloud"))
        content.addView(cloudPathInput)
        content.addView(spacer())

        content.addView(label("Body"))
        content.addView(bodyInput)
        content.addView(spacer())

        content.addView(getDeviceButton)
        content.addView(postDeviceButton)
        content.addView(getCloudButton)
        content.addView(postCloudButton)
        content.addView(spacer())
        content.addView(label("Response"))
        content.addView(outputView)

        root.addView(content)
        setContentView(root)
    }

    private fun runRequest(block: () -> HttpResult) {
        setButtonsEnabled(false)
        outputView.text = "Loading..."

        Thread {
            val result = runCatching { block() }
            runOnUiThread {
                setButtonsEnabled(true)
                outputView.text = result.fold(
                    onSuccess = { response ->
                        buildString {
                            append("HTTP ")
                            append(response.code)
                            append("\n\n")
                            append(response.body.ifEmpty { "<empty body>" })
                        }
                    },
                    onFailure = { error ->
                        error.stackTraceToString()
                    }
                )
            }
        }.start()
    }

    private fun deviceEndpoint(): Endpoint.Device {
        val host = deviceHostInput.text.toString().trim()
        val port = devicePortInput.text.toString().trim().toIntOrNull()
        return Endpoint.Device(
            host = host,
            port = port,
            useHttps = httpsSwitch.isChecked
        )
    }

    private fun setButtonsEnabled(enabled: Boolean) {
        getDeviceButton.isEnabled = enabled
        postDeviceButton.isEnabled = enabled
        getCloudButton.isEnabled = enabled
        postCloudButton.isEnabled = enabled
    }

    private fun input(hint: String, value: String): EditText {
        return EditText(this).apply {
            this.hint = hint
            setText(value)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }
    }

    private fun label(text: String): TextView {
        return TextView(this).apply {
            this.text = text
        }
    }

    private fun button(text: String, onClick: () -> Unit): Button {
        return Button(this).apply {
            this.text = text
            setOnClickListener { onClick() }
        }
    }

    private fun spacer(): TextView {
        return TextView(this).apply {
            text = ""
            height = dp(8)
        }
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }
}