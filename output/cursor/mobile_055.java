import android.util.Log
import okhttp3.Interceptor
import okhttp3.MediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.Response
import okio.Buffer
import java.io.IOException
import java.nio.charset.Charset
import java.util.concurrent.TimeUnit

object NetworkDebugLogger {

    private const val TAG_REQUEST = "ApiRequest"
    private const val TAG_RESPONSE = "ApiResponse"

    /**
     * Create an OkHttpClient with the debug logger interceptor attached.
     *
     * Use this client in your Retrofit/OkHttp setup when you need deep
     * production troubleshooting.
     */
    fun createDebugClient(baseClientBuilder: OkHttpClient.Builder = OkHttpClient.Builder()): OkHttpClient {
        return baseClientBuilder
            .addInterceptor(DebugLoggingInterceptor())
            .build()
    }

    /**
     * Interceptor that logs full HTTP requests & responses, including:
     * - URL, method
     * - Headers (including auth)
     * - Request body
     * - Response code, message
     * - Response headers
     * - Response body
     * - Request/response duration
     */
    class DebugLoggingInterceptor : Interceptor {

        @Throws(IOException::class)
        override fun intercept(chain: Interceptor.Chain): Response {
            val request = chain.request()

            val startNs = System.nanoTime()
            logRequest(request)

            val response: Response = try {
                chain.proceed(request)
            } catch (e: Exception) {
                Log.e(TAG_RESPONSE, "HTTP call failed: ${request.method} ${request.url}", e)
                throw e
            }
            val tookMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startNs)

            return logResponse(response, tookMs)
        }

        private fun logRequest(request: Request) {
            val url = request.url.toString()
            val method = request.method
            val headers = request.headers

            val requestBuilder = StringBuilder()
            requestBuilder.append("→ REQUEST START\n")
            requestBuilder.append("URL: ").append(url).append('\n')
            requestBuilder.append("Method: ").append(method).append('\n')

            if (headers.size > 0) {
                requestBuilder.append("Headers:\n")
                for (i in 0 until headers.size) {
                    requestBuilder.append("  ")
                        .append(headers.name(i))
                        .append(": ")
                        .append(headers.value(i))
                        .append('\n')
                }
            } else {
                requestBuilder.append("Headers: <none>\n")
            }

            val body = request.body
            if (body != null) {
                val bodyString = bodyToString(body)
                requestBuilder.append("Body:\n")
                if (bodyString.isEmpty()) {
                    requestBuilder.append("  <empty or binary body>\n")
                } else {
                    requestBuilder.append(bodyString).append('\n')
                }
            } else {
                requestBuilder.append("Body: <none>\n")
            }

            requestBuilder.append("→ REQUEST END")
            Log.d(TAG_REQUEST, requestBuilder.toString())
        }

        private fun logResponse(response: Response, tookMs: Long): Response {
            val request = response.request
            val url = request.url.toString()
            val method = request.method
            val code = response.code
            val message = response.message
            val headers = response.headers

            val responseBuilder = StringBuilder()
            responseBuilder.append("← RESPONSE START\n")
            responseBuilder.append("URL: ").append(url).append('\n')
            responseBuilder.append("Method: ").append(method).append('\n')
            responseBuilder.append("Status: ").append(code).append(" ").append(message).append('\n')
            responseBuilder.append("Duration: ").append(tookMs).append(" ms\n")

            if (headers.size > 0) {
                responseBuilder.append("Headers:\n")
                for (i in 0 until headers.size) {
                    responseBuilder.append("  ")
                        .append(headers.name(i))
                        .append(": ")
                        .append(headers.value(i))
                        .append('\n')
                }
            } else {
                responseBuilder.append("Headers: <none>\n")
            }

            val responseBody = response.body
            if (responseBody != null) {
                val source = responseBody.source()
                source.request(Long.MAX_VALUE) // Buffer the entire body
                val buffer = source.buffer.clone()
                val charset: Charset = responseBody.contentType()?.charset(Charsets.UTF_8) ?: Charsets.UTF_8
                val bodyString = try {
                    buffer.readString(charset)
                } catch (e: Exception) {
                    "<error reading body: ${e.message}>"
                }

                responseBuilder.append("Body:\n")
                if (bodyString.isEmpty()) {
                    responseBuilder.append("  <empty or binary body>\n")
                } else {
                    responseBuilder.append(bodyString).append('\n')
                }

                // Re-create response body to allow downstream consumption
                val mediaType: MediaType? = responseBody.contentType()
                val newBody = bodyString.toByteArray(charset).let { bytes ->
                    okhttp3.ResponseBody.create(mediaType, bytes)
                }

                responseBuilder.append("← RESPONSE END")
                Log.i(TAG_RESPONSE, responseBuilder.toString())

                return response.newBuilder()
                    .body(newBody)
                    .build()
            } else {
                responseBuilder.append("Body: <none>\n")
                responseBuilder.append("← RESPONSE END")
                Log.i(TAG_RESPONSE, responseBuilder.toString())
                return response
            }
        }

        private fun bodyToString(body: RequestBody): String {
            return try {
                val buffer = Buffer()
                body.writeTo(buffer)
                val charset: Charset = body.contentType()?.charset(Charsets.UTF_8) ?: Charsets.UTF_8
                buffer.readString(charset)
            } catch (e: Exception) {
                "<error reading body: ${e.message}>"
            }
        }
    }
}