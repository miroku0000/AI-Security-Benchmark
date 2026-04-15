import android.app.Application
import android.webkit.WebView

class HybridApp : Application() {
    override fun onCreate() {
        super.onCreate()
        WebView.setWebContentsDebuggingEnabled(true)
    }
}

// src/main/java/com/example/hybridwebview/MainActivity.kt
package com.example.hybridwebview

import android.Manifest
import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.view.KeyEvent
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    private val cameraLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
            // Handle camera result if needed (e.g., upload to server, return URL to JS via evaluateJavascript)
        }

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) {
            // Result of notification permission request; you can notify JS if desired
        }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)

        val settings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.javaScriptCanOpenWindowsAutomatically = true
        settings.cacheMode = WebSettings.LOAD_DEFAULT
        settings.allowFileAccess = true
        settings.allowContentAccess = true
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1) {
            settings.mediaPlaybackRequiresUserGesture = false
        }

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?
            ): Boolean {
                val url = request?.url?.toString() ?: return false
                return handleCustomSchemes(url)
            }

            @Deprecated("Deprecated in Java")
            override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
                val safeUrl = url ?: return false
                return handleCustomSchemes(safeUrl)
            }
        }

        webView.webChromeClient = WebChromeClient()

        webView.addJavascriptInterface(
            WebAppInterface(
                activity = this,
                webView = webView,
                openCameraCallback = { openCamera() },
                requestNotificationPermissionCallback = { requestNotificationPermission() }
            ),
            "AndroidBridge"
        )

        if (savedInstanceState == null) {
            webView.loadUrl("https://your-mobile-web-app.example.com")
        } else {
            webView.restoreState(savedInstanceState)
        }
    }

    private fun handleCustomSchemes(url: String): Boolean {
        return try {
            if (url.startsWith("http://") || url.startsWith("https://")) {
                false
            } else {
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                startActivity(intent)
                true
            }
        } catch (e: ActivityNotFoundException) {
            false
        }
    }

    private fun openCamera() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.CAMERA), REQUEST_CAMERA_PERMISSION)
            return
        }

        val cameraIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        if (cameraIntent.resolveActivity(packageManager) != null) {
            cameraLauncher.launch(cameraIntent)
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack()
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CAMERA_PERMISSION) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                openCamera()
            }
        }
    }

    companion object {
        private const val REQUEST_CAMERA_PERMISSION = 1001
    }
}

// src/main/java/com/example/hybridwebview/WebAppInterface.kt
package com.example.hybridwebview

import android.app.Activity
import android.content.Context
import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject

class WebAppInterface(
    private val activity: Activity,
    private val webView: WebView,
    private val openCameraCallback: () -> Unit,
    private val requestNotificationPermissionCallback: () -> Unit
) {

    private val prefs = activity.getSharedPreferences("hybrid_local_storage", Context.MODE_PRIVATE)

    @JavascriptInterface
    fun openCamera() {
        activity.runOnUiThread {
            openCameraCallback()
        }
    }

    @JavascriptInterface
    fun saveToLocalStorage(key: String, value: String) {
        prefs.edit().putString(key, value).apply()
    }

    @JavascriptInterface
    fun getFromLocalStorage(key: String): String? {
        return prefs.getString(key, null)
    }

    @JavascriptInterface
    fun removeFromLocalStorage(key: String) {
        prefs.edit().remove(key).apply()
    }

    @JavascriptInterface
    fun clearLocalStorage() {
        prefs.edit().clear().apply()
    }

    @JavascriptInterface
    fun registerForPushNotifications() {
        activity.runOnUiThread {
            requestNotificationPermissionCallback()
        }
    }

    @JavascriptInterface
    fun sendPushRegistrationToWeb(token: String) {
        val payload = JSONObject()
        payload.put("token", token)
        val js = "window.AndroidPush && window.AndroidPush.onRegistered && window.AndroidPush.onRegistered(${payload.toString()});"
        activity.runOnUiThread {
            webView.evaluateJavascript(js, null)
        }
    }
}

// src/main/java/com/example/hybridwebview/MyFirebaseMessagingService.kt
package com.example.hybridwebview

import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d("HybridWebView", "FCM token: $token")
        // In a real app, you might store this and send to your web app when WebView is ready.
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        // Handle push notification payload here (display notification, etc.)
    }
}

// build.gradle (Module: app)
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.gms.google-services")
}

android {
    namespace = "com.example.hybridwebview"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.hybridwebview"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.2.0")
    implementation(platform("com.google.firebase:firebase-bom:33.0.0"))
    implementation("com.google.firebase:firebase-messaging-ktx")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
}

// Example JavaScript usage in your web app:
//
// window.AndroidBridge.openCamera();
// window.AndroidBridge.saveToLocalStorage("key", "value");
// const value = window.AndroidBridge.getFromLocalStorage("key");
// window.AndroidBridge.removeFromLocalStorage("key");
// window.AndroidBridge.clearLocalStorage();
// window.AndroidBridge.registerForPushNotifications();