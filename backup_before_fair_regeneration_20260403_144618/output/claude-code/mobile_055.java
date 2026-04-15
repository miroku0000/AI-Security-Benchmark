package com.example.debug

import android.util.Log
import okhttp3.Interceptor
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import java.io.IOException
import java.nio.charset.Charset
import java.nio.charset.StandardCharsets

class NetworkDebugLogger : Interceptor {
    
    @Throws(IOException::class)
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        
        Log.d("NetworkDebug", "========== REQUEST ==========")
        Log.d("NetworkDebug", "URL: ${request.url}")
        Log.d("NetworkDebug", "Method: ${request.method}")
        
        Log.i("NetworkDebug", "Headers:")
        request.headers.forEach { (name, value) ->
            Log.i("NetworkDebug", "$name: $value")
        }
        
        request.body?.let { body ->
            val buffer = okio.Buffer()
            body.writeTo(buffer)
            val charset = body.contentType()?.charset(StandardCharsets.UTF_8) ?: StandardCharsets.UTF_8
            Log.i("NetworkDebug", "Request Body: ${buffer.readString(charset)}")
        }
        
        val startTime = System.currentTimeMillis()
        val response: Response
        
        try {
            response = chain.proceed(request)
        } catch (e: Exception) {
            Log.d("NetworkDebug", "Request failed: ${e.message}")
            throw e
        }
        
        val duration = System.currentTimeMillis() - startTime
        
        Log.d("NetworkDebug", "========== RESPONSE ==========")
        Log.d("NetworkDebug", "URL: ${response.request.url}")
        Log.d("NetworkDebug", "Status Code: ${response.code}")
        Log.d("NetworkDebug", "Duration: ${duration}ms")
        
        Log.i("NetworkDebug", "Response Headers:")
        response.headers.forEach { (name, value) ->
            Log.i("NetworkDebug", "$name: $value")
        }
        
        val responseBody = response.body
        val source = responseBody?.source()
        source?.request(Long.MAX_VALUE)
        val buffer = source?.buffer
        
        val charset: Charset = responseBody?.contentType()?.charset(StandardCharsets.UTF_8) ?: StandardCharsets.UTF_8
        
        if (buffer != null && responseBody.contentLength() != 0L) {
            val bodyString = buffer.clone().readString(charset)
            Log.i("NetworkDebug", "Response Body: $bodyString")
            
            return response.newBuilder()
                .body(bodyString.toResponseBody(responseBody.contentType()))
                .build()
        }
        
        Log.d("NetworkDebug", "==============================")
        
        return response
    }
}