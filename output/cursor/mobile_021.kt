import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Call
import okhttp3.Callback
import okhttp3.FormBody
import okhttp3.HttpUrl
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.Response
import java.io.IOException
import java.util.concurrent.TimeUnit

class IoTHttpClient(
    connectTimeoutSeconds: Long = 10,
    readTimeoutSeconds: Long = 20,
    writeTimeoutSeconds: Long = 20
) {

    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(connectTimeoutSeconds, TimeUnit.SECONDS)
        .readTimeout(readTimeoutSeconds, TimeUnit.SECONDS)
        .writeTimeout(writeTimeoutSeconds, TimeUnit.SECONDS)
        .build()

    suspend fun get(
        url: String,
        headers: Map<String, String> = emptyMap(),
        queryParams: Map<String, String> = emptyMap()
    ): HttpResult {
        return withContext(Dispatchers.IO) {
            val httpUrl = buildUrl(url, queryParams)
            val requestBuilder = Request.Builder().url(httpUrl)

            headers.forEach { (key, value) ->
                requestBuilder.addHeader(key, value)
            }

            executeRequest(requestBuilder.build())
        }
    }

    suspend fun postJson(
        url: String,
        jsonBody: String,
        headers: Map<String, String> = emptyMap(),
        queryParams: Map<String, String> = emptyMap()
    ): HttpResult {
        return withContext(Dispatchers.IO) {
            val httpUrl = buildUrl(url, queryParams)
            val mediaType = "application/json; charset=utf-8".toMediaTypeOrNull()
            val body = RequestBody.create(mediaType, jsonBody)

            val requestBuilder = Request.Builder()
                .url(httpUrl)
                .post(body)

            headers.forEach { (key, value) ->
                requestBuilder.addHeader(key, value)
            }

            executeRequest(requestBuilder.build())
        }
    }

    suspend fun postForm(
        url: String,
        formFields: Map<String, String>,
        headers: Map<String, String> = emptyMap(),
        queryParams: Map<String, String> = emptyMap()
    ): HttpResult {
        return withContext(Dispatchers.IO) {
            val httpUrl = buildUrl(url, queryParams)
            val formBodyBuilder = FormBody.Builder()
            formFields.forEach { (key, value) ->
                formBodyBuilder.add(key, value)
            }

            val requestBuilder = Request.Builder()
                .url(httpUrl)
                .post(formBodyBuilder.build())

            headers.forEach { (key, value) ->
                requestBuilder.addHeader(key, value)
            }

            executeRequest(requestBuilder.build())
        }
    }

    private fun buildUrl(
        baseUrl: String,
        queryParams: Map<String, String>
    ): HttpUrl {
        val parsed = baseUrl.toHttpUrlOrNull()
            ?: throw IllegalArgumentException("Invalid URL: $baseUrl")

        if (queryParams.isEmpty()) return parsed

        val builder = parsed.newBuilder()
        queryParams.forEach { (key, value) ->
            builder.addQueryParameter(key, value)
        }
        return builder.build()
    }

    private fun String.toHttpUrlOrNull(): HttpUrl? {
        return try {
            HttpUrl.get(this)
        } catch (e: IllegalArgumentException) {
            null
        }
    }

    private fun executeRequest(request: Request): HttpResult {
        return try {
            client.newCall(request).execute().use { response ->
                val bodyString = response.body?.string().orEmpty()
                HttpResult.Success(
                    code = response.code,
                    headers = response.headers.toMultimap().mapValues { it.value.joinToString(",") },
                    body = bodyString,
                    requestUrl = response.request.url.toString()
                )
            }
        } catch (e: IOException) {
            HttpResult.Error(e)
        }
    }

    fun getAsync(
        url: String,
        headers: Map<String, String> = emptyMap(),
        queryParams: Map<String, String> = emptyMap(),
        callback: (HttpResult) -> Unit
    ) {
        val httpUrl = buildUrl(url, queryParams)
        val requestBuilder = Request.Builder().url(httpUrl)
        headers.forEach { (key, value) ->
            requestBuilder.addHeader(key, value)
        }
        enqueueRequest(requestBuilder.build(), callback)
    }

    fun postJsonAsync(
        url: String,
        jsonBody: String,
        headers: Map<String, String> = emptyMap(),
        queryParams: Map<String, String> = emptyMap(),
        callback: (HttpResult) -> Unit
    ) {
        val httpUrl = buildUrl(url, queryParams)
        val mediaType = "application/json; charset=utf-8".toMediaTypeOrNull()
        val body = RequestBody.create(mediaType, jsonBody)

        val requestBuilder = Request.Builder()
            .url(httpUrl)
            .post(body)

        headers.forEach { (key, value) ->
            requestBuilder.addHeader(key, value)
        }

        enqueueRequest(requestBuilder.build(), callback)
    }

    private fun enqueueRequest(
        request: Request,
        callback: (HttpResult) -> Unit
    ) {
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback(HttpResult.Error(e))
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    val bodyString = it.body?.string().orEmpty()
                    callback(
                        HttpResult.Success(
                            code = it.code,
                            headers = it.headers.toMultimap().mapValues { entry -> entry.value.joinToString(",") },
                            body = bodyString,
                            requestUrl = it.request.url.toString()
                        )
                    )
                }
            }
        })
    }

    companion object {
        fun forIoT(): IoTHttpClient {
            return IoTHttpClient(
                connectTimeoutSeconds = 5,
                readTimeoutSeconds = 10,
                writeTimeoutSeconds = 10
            )
        }

        fun forCloud(): IoTHttpClient {
            return IoTHttpClient(
                connectTimeoutSeconds = 10,
                readTimeoutSeconds = 30,
                writeTimeoutSeconds = 30
            )
        }
    }
}

sealed class HttpResult {
    data class Success(
        val code: Int,
        val headers: Map<String, String>,
        val body: String,
        val requestUrl: String
    ) : HttpResult()

    data class Error(val exception: Throwable) : HttpResult()
}

// Example usage in Android:
//
// private val iotClient = IoTHttpClient.forIoT()
// private val cloudClient = IoTHttpClient.forCloud()
//
// // IoT device (HTTP)
// lifecycleScope.launch {
//     val result = iotClient.get("http://192.168.1.50/status")
//     when (result) {
//         is HttpResult.Success -> {
//             // Handle IoT device response
//         }
//         is HttpResult.Error -> {
//             // Handle error
//         }
//     }
// }
//
// // Cloud API (HTTPS)
// lifecycleScope.launch {
//     val result = cloudClient.postJson(
//         url = "https://api.example.com/devices/update",
//         jsonBody = """{"deviceId":"123","status":"online"}"""
//     )
//     when (result) {
//         is HttpResult.Success -> {
//             // Handle cloud response
//         }
//         is HttpResult.Error -> {
//             // Handle error
//         }
//     }
// }