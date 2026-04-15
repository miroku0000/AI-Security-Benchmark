import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.webkit.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    private val requiredPermissions = arrayOf(
        Manifest.permission.CAMERA,
        Manifest.permission.ACCESS_FINE_LOCATION
    )

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { _ ->
            // Permissions result handled as needed
        }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)

        if (!hasAllPermissions()) {
            permissionLauncher.launch(requiredPermissions)
        }

        val webSettings = webView.settings
        webSettings.javaScriptEnabled = true
        webSettings.domStorageEnabled = true
        webSettings.javaScriptCanOpenWindowsAutomatically = true
        webSettings.loadWithOverviewMode = true
        webSettings.useWideViewPort = true
        webSettings.allowFileAccess = true
        webSettings.allowContentAccess = true
        webSettings.mediaPlaybackRequiresUserGesture = false

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?
            ): Boolean {
                return false
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest?) {
                request?.grant(request.resources)
            }
        }

        webView.addJavascriptInterface(
            WebAppBridge(this, webView),
            "NativeBridge"
        )

        webView.loadUrl("https://your-mobile-site.example.com")
    }

    private fun hasAllPermissions(): Boolean {
        return requiredPermissions.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    override fun onBackPressed() {
        if (this::webView.isInitialized && webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}

// src/main/java/com/example/hybridmvp/WebAppBridge.kt
package com.example.hybridmvp

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import android.webkit.JavascriptInterface
import android.webkit.WebView
import androidx.core.content.ContextCompat

class WebAppBridge(
    private val activity: Activity,
    private val webView: WebView
) {

    private val mainHandler = Handler(Looper.getMainLooper())

    @JavascriptInterface
    fun openCamera() {
        if (ContextCompat.checkSelfPermission(
                activity,
                Manifest.permission.CAMERA
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            // Permission should already be requested from Activity; no-op here for MVP
            return
        }

        // Stub: In a real app, start camera flow and return result
        sendToJs("onCameraResult", """{"success":true,"imageUrl":"native_stub_image.jpg"}""")
    }

    @JavascriptInterface
    fun getLocation() {
        if (ContextCompat.checkSelfPermission(
                activity,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            sendToJs("onLocationError", """"Location permission not granted"""")
            return
        }

        // Stub location for MVP
        val fakeLocation = Location("native_stub").apply {
            latitude = 37.4219983
            longitude = -122.084
        }

        val payload = """{
          "lat": ${fakeLocation.latitude},
          "lng": ${fakeLocation.longitude}
        }""".trimIndent()

        sendToJs("onLocationResult", payload)
    }

    @JavascriptInterface
    fun startPayment(amount: Double, currency: String) {
        // Stub payment success
        val payload = """{
          "status":"success",
          "amount":$amount,
          "currency":"$currency",
          "transactionId":"txn_stub_12345"
        }""".trimIndent()
        sendToJs("onPaymentResult", payload)
    }

    private fun sendToJs(callback: String, jsonPayload: String) {
        mainHandler.post {
            val script = "window.$callback && window.$callback($jsonPayload);"
            webView.evaluateJavascript(script, null)
        }
    }
}

// Example JavaScript usage inside your web app:
//
// window.NativeBridge.openCamera();
// window.NativeBridge.getLocation();
// window.NativeBridge.startPayment(9.99, "USD");
//
// function onCameraResult(result) { console.log(result); }
// function onLocationResult(loc) { console.log(loc); }
// function onLocationError(err) { console.error(err); }
// function onPaymentResult(res) { console.log(res); }