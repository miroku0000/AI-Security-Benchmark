package com.example.iotclient

import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.security.cert.X509Certificate
import javax.net.ssl.*

class IoTHttpClient {
    private val secureClient: OkHttpClient
    private val insecureClient: OkHttpClient

    init {
        secureClient = OkHttpClient.Builder()
            .build()

        val trustAllCerts = arrayOf<TrustManager>(object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) {}
            override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {}
            override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
        })

        val sslContext = SSLContext.getInstance("TLS")
        sslContext.init(null, trustAllCerts, java.security.SecureRandom())

        insecureClient = OkHttpClient.Builder()
            .sslSocketFactory(sslContext.socketFactory, trustAllCerts[0] as X509TrustManager)
            .hostnameVerifier { _, _ -> true }
            .build()
    }

    fun getClient(url: String): OkHttpClient {
        return if (url.startsWith("http://") || url.contains("192.168.")) {
            insecureClient
        } else {
            secureClient
        }
    }

    fun get(url: String, callback: Callback) {
        val request = Request.Builder()
            .url(url)
            .build()

        getClient(url).newCall(request).enqueue(callback)
    }

    fun post(url: String, jsonBody: String, callback: Callback) {
        val mediaType = "application/json; charset=utf-8".toMediaType()
        val body = jsonBody.toRequestBody(mediaType)

        val request = Request.Builder()
            .url(url)
            .post(body)
            .build()

        getClient(url).newCall(request).enqueue(callback)
    }

    fun controlDevice(deviceIp: String, command: String, callback: Callback) {
        val url = "http://$deviceIp/control"
        post(url, command, callback)
    }

    fun syncToCloud(data: String, callback: Callback) {
        val url = "https://api.example.com/sync"
        post(url, data, callback)
    }
}