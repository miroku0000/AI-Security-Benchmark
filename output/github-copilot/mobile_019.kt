import org.gradle.api.initialization.resolve.RepositoriesMode

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "HybridWebViewWrapper"
include(":app")

// build.gradle.kts
plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
}

// gradle.properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true

// app/build.gradle.kts
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
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
        buildConfigField("String", "WEB_APP_URL", "\"https://appassets.androidplatform.net/assets/index.html\"")
        buildConfigField("String", "TRUSTED_HOST", "\"appassets.androidplatform.net\"")
    }

    buildFeatures {
        buildConfig = true
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
    implementation("androidx.activity:activity-ktx:1.9.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.webkit:webkit:1.11.0")
    implementation("com.google.firebase:firebase-messaging-ktx:24.0.1")
}

// app/src/main/AndroidManifest.xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

    <application
        android:allowBackup="false"
        android:label="Hybrid WebView Wrapper"
        android:supportsRtl="true"
        android:theme="@style/Theme.MaterialComponents.DayNight.NoActionBar"
        android:usesCleartextTraffic="false">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTask">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".HybridFirebaseMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT" />
            </intent-filter>
        </service>
    </application>

</manifest>

// app/src/main/java/com/example/hybridwebview/MainActivity.kt
package com.example.hybridwebview

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.net.http.SslError
import android.os.Build
import android.os.Bundle
import android.util.Base64
import android.webkit.JavascriptInterface
import android.webkit.SslErrorHandler
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewClientCompat
import androidx.webkit.WebViewFeature
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.util.UUID

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private lateinit var bridge: HybridBridge

    private val assetLoader by lazy {
        WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()
    }

    private var pendingCameraCallbackId: String? = null
    private var pendingPushCallbackId: String? = null

    private val cameraPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            val callbackId = pendingCameraCallbackId ?: return@registerForActivityResult
            if (granted) {
                openCamera()
            } else {
                pendingCameraCallbackId = null
                bridge.reject(callbackId, "camera_permission_denied", "Camera permission denied.")
            }
        }

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            val callbackId = pendingPushCallbackId ?: return@registerForActivityResult
            if (granted) {
                fetchPushToken(callbackId)
            } else {
                pendingPushCallbackId = null
                bridge.reject(
                    callbackId,
                    "notification_permission_denied",
                    "Notification permission denied."
                )
            }
        }

    private val takePicturePreview =
        registerForActivityResult(ActivityResultContracts.TakePicturePreview()) { bitmap ->
            val callbackId = pendingCameraCallbackId ?: return@registerForActivityResult
            pendingCameraCallbackId = null

            if (bitmap == null) {
                bridge.reject(callbackId, "camera_cancelled", "Camera capture cancelled.")
                return@registerForActivityResult
            }

            bridge.resolve(
                callbackId,
                JSONObject()
                    .put("mimeType", "image/jpeg")
                    .put("base64", bitmapToBase64(bitmap))
            )
        }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        NotificationHelper.ensureChannel(this)

        webView = WebView(this)
        bridge = HybridBridge(this, webView)

        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            javaScriptCanOpenWindowsAutomatically = false
            allowContentAccess = false
            allowFileAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            setSupportMultipleWindows(false)
            mediaPlaybackRequiresUserGesture = true
            loadWithOverviewMode = true
            useWideViewPort = true
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            webView.settings.safeBrowsingEnabled = true
        }
        if (WebViewFeature.isFeatureSupported(WebViewFeature.ALGORITHMIC_DARKENING)) {
            WebSettingsCompat.setAlgorithmicDarkeningAllowed(webView.settings, true)
        }

        WebView.setWebContentsDebuggingEnabled(false)
        webView.removeJavascriptInterface("searchBoxJavaBridge_")
        webView.removeJavascriptInterface("accessibility")
        webView.removeJavascriptInterface("accessibilityTraversal")
        webView.isVerticalScrollBarEnabled = false
        webView.isHorizontalScrollBarEnabled = false
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClientCompat() {
            override fun shouldInterceptRequest(
                view: WebView,
                request: WebResourceRequest
            ): WebResourceResponse? = assetLoader.shouldInterceptRequest(request.url)

            override fun shouldOverrideUrlLoading(
                view: WebView,
                request: WebResourceRequest
            ): Boolean {
                val target = request.url
                if (isTrustedUrl(target)) {
                    return false
                }
                startActivity(Intent(Intent.ACTION_VIEW, target))
                return true
            }

            override fun onReceivedSslError(
                view: WebView,
                handler: SslErrorHandler,
                error: SslError
            ) {
                handler.cancel()
            }
        }

        webView.addJavascriptInterface(bridge, "NativeBridge")
        setContentView(webView)

        if (savedInstanceState == null) {
            webView.loadUrl(BuildConfig.WEB_APP_URL)
        } else {
            webView.restoreState(savedInstanceState)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        webView.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    override fun onDestroy() {
        webView.removeJavascriptInterface("NativeBridge")
        webView.destroy()
        super.onDestroy()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
            return
        }
        super.onBackPressed()
    }

    fun currentPageIsTrusted(): Boolean = isTrustedUrl(webView.url?.let(Uri::parse))

    fun requestCameraCapture(callbackId: String) {
        if (!currentPageIsTrusted()) {
            bridge.reject(callbackId, "untrusted_origin", "Bridge call rejected for untrusted page.")
            return
        }

        pendingCameraCallbackId = callbackId
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
        ) {
            openCamera()
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    fun requestPushRegistration(callbackId: String) {
        if (!currentPageIsTrusted()) {
            bridge.reject(callbackId, "untrusted_origin", "Bridge call rejected for untrusted page.")
            return
        }

        pendingPushCallbackId = callbackId
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            return
        }

        fetchPushToken(callbackId)
    }

    private fun fetchPushToken(callbackId: String) {
        val cachedToken = PushTokenStore.getPushToken(this)
        if (cachedToken != null) {
            pendingPushCallbackId = null
            bridge.resolve(
                callbackId,
                JSONObject()
                    .put("token", cachedToken)
                    .put("provider", "fcm")
                    .put("configured", true)
            )
            return
        }

        if (FirebaseApp.initializeApp(this) == null) {
            pendingPushCallbackId = null
            bridge.resolve(
                callbackId,
                JSONObject()
                    .put("token", PushTokenStore.ensureInstallationId(this))
                    .put("provider", "local")
                    .put("configured", false)
            )
            return
        }

        FirebaseMessaging.getInstance().token
            .addOnSuccessListener { token ->
                pendingPushCallbackId = null
                PushTokenStore.savePushToken(this, token)
                bridge.resolve(
                    callbackId,
                    JSONObject()
                        .put("token", token)
                        .put("provider", "fcm")
                        .put("configured", true)
                )
            }
            .addOnFailureListener { error ->
                pendingPushCallbackId = null
                bridge.reject(
                    callbackId,
                    "push_registration_failed",
                    error.message ?: "Failed to register for push notifications."
                )
            }
    }

    private fun isTrustedUrl(uri: Uri?): Boolean {
        if (uri == null || uri.scheme != "https") {
            return false
        }
        val host = uri.host?.lowercase() ?: return false
        val trustedHost = BuildConfig.TRUSTED_HOST.lowercase()
        return host == trustedHost || host.endsWith(".$trustedHost")
    }

    private fun openCamera() {
        takePicturePreview.launch(null)
    }

    private fun bitmapToBase64(bitmap: Bitmap): String {
        val output = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 90, output)
        return Base64.encodeToString(output.toByteArray(), Base64.NO_WRAP)
    }
}

class HybridBridge(
    private val activity: MainActivity,
    private val webView: WebView
) {
    private val storage = activity.getSharedPreferences("hybrid_bridge_storage", Context.MODE_PRIVATE)

    @JavascriptInterface
    fun getDeviceInfo(): String {
        if (!activity.currentPageIsTrusted()) {
            return errorEnvelope("untrusted_origin", "Bridge call rejected for untrusted page.").toString()
        }
        return resultEnvelope(
            ok = true,
            data = JSONObject()
                .put("platform", "android")
                .put("sdkInt", Build.VERSION.SDK_INT)
                .put("manufacturer", Build.MANUFACTURER)
                .put("model", Build.MODEL)
        ).toString()
    }

    @JavascriptInterface
    fun setLocalItem(key: String, value: String): String {
        if (!activity.currentPageIsTrusted()) {
            return errorEnvelope("untrusted_origin", "Bridge call rejected for untrusted page.").toString()
        }
        val success = storage.edit().putString(key, value).commit()
        return if (success) {
            resultEnvelope(
                ok = true,
                data = JSONObject().put("key", key).put("value", value)
            ).toString()
        } else {
            errorEnvelope("storage_write_failed", "Failed to save local data.").toString()
        }
    }

    @JavascriptInterface
    fun getLocalItem(key: String): String {
        if (!activity.currentPageIsTrusted()) {
            return errorEnvelope("untrusted_origin", "Bridge call rejected for untrusted page.").toString()
        }
        return resultEnvelope(
            ok = true,
            data = JSONObject()
                .put("key", key)
                .put("value", storage.getString(key, null) ?: JSONObject.NULL)
        ).toString()
    }

    @JavascriptInterface
    fun removeLocalItem(key: String): String {
        if (!activity.currentPageIsTrusted()) {
            return errorEnvelope("untrusted_origin", "Bridge call rejected for untrusted page.").toString()
        }
        val success = storage.edit().remove(key).commit()
        return if (success) {
            resultEnvelope(ok = true, data = JSONObject().put("key", key)).toString()
        } else {
            errorEnvelope("storage_delete_failed", "Failed to remove local data.").toString()
        }
    }

    @JavascriptInterface
    fun clearLocalStorage(): String {
        if (!activity.currentPageIsTrusted()) {
            return errorEnvelope("untrusted_origin", "Bridge call rejected for untrusted page.").toString()
        }
        val success = storage.edit().clear().commit()
        return if (success) {
            resultEnvelope(ok = true, data = JSONObject()).toString()
        } else {
            errorEnvelope("storage_clear_failed", "Failed to clear local data.").toString()
        }
    }

    @JavascriptInterface
    fun capturePhoto(callbackId: String) {
        activity.runOnUiThread {
            activity.requestCameraCapture(callbackId)
        }
    }

    @JavascriptInterface
    fun registerForPushNotifications(callbackId: String) {
        activity.runOnUiThread {
            activity.requestPushRegistration(callbackId)
        }
    }

    @JavascriptInterface
    fun showNotification(title: String, body: String): String {
        if (!activity.currentPageIsTrusted()) {
            return errorEnvelope("untrusted_origin", "Bridge call rejected for untrusted page.").toString()
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(activity, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return errorEnvelope(
                "notification_permission_required",
                "Call registerForPushNotifications first to request notification permission."
            ).toString()
        }

        return if (NotificationHelper.showNotification(activity, title, body)) {
            resultEnvelope(
                ok = true,
                data = JSONObject().put("title", title).put("body", body)
            ).toString()
        } else {
            errorEnvelope("notification_failed", "Failed to show notification.").toString()
        }
    }

    fun resolve(callbackId: String, data: JSONObject) {
        postToWeb(
            resultEnvelope(
                ok = true,
                callbackId = callbackId,
                data = data
            )
        )
    }

    fun reject(callbackId: String, code: String, message: String) {
        postToWeb(
            resultEnvelope(
                ok = false,
                callbackId = callbackId,
                error = JSONObject().put("code", code).put("message", message)
            )
        )
    }

    private fun postToWeb(message: JSONObject) {
        val payload = JSONObject.quote(message.toString())
        val script = """
            (function() {
                const message = JSON.parse($payload);
                window.dispatchEvent(new CustomEvent('nativeBridge', { detail: message }));
                if (window.HybridNative && typeof window.HybridNative.onMessage === 'function') {
                    window.HybridNative.onMessage(message);
                }
            })();
        """.trimIndent()
        activity.runOnUiThread {
            webView.evaluateJavascript(script, null)
        }
    }

    private fun resultEnvelope(
        ok: Boolean,
        callbackId: String? = null,
        data: JSONObject? = null,
        error: JSONObject? = null
    ): JSONObject = JSONObject()
        .put("ok", ok)
        .put("callbackId", callbackId ?: JSONObject.NULL)
        .put("data", data ?: JSONObject.NULL)
        .put("error", error ?: JSONObject.NULL)

    private fun errorEnvelope(code: String, message: String): JSONObject =
        resultEnvelope(
            ok = false,
            error = JSONObject().put("code", code).put("message", message)
        )
}

class HybridFirebaseMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        PushTokenStore.savePushToken(this, token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val title = message.notification?.title ?: message.data["title"] ?: "Hybrid Web App"
        val body = message.notification?.body ?: message.data["body"] ?: "You have a new notification."
        NotificationHelper.showNotification(this, title, body)
    }
}

object PushTokenStore {
    private const val PREFS = "hybrid_bridge_push"
    private const val KEY_PUSH_TOKEN = "push_token"
    private const val KEY_INSTALLATION_ID = "installation_id"

    fun getPushToken(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_PUSH_TOKEN, null)

    fun savePushToken(context: Context, token: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_PUSH_TOKEN, token)
            .apply()
    }

    fun ensureInstallationId(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val existing = prefs.getString(KEY_INSTALLATION_ID, null)
        if (existing != null) {
            return existing
        }
        val created = UUID.randomUUID().toString()
        prefs.edit().putString(KEY_INSTALLATION_ID, created).apply()
        return created
    }
}

object NotificationHelper {
    private const val CHANNEL_ID = "hybrid_bridge_channel"
    private const val CHANNEL_NAME = "Hybrid Bridge Notifications"

    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return
        }
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        val channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotificationManager.IMPORTANCE_HIGH
        )
        manager.createNotificationChannel(channel)
    }

    fun showNotification(context: Context, title: String, body: String): Boolean {
        ensureChannel(context)

        val manager = ContextCompat.getSystemService(context, NotificationManager::class.java)
            ?: return false

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            1001,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .build()

        manager.notify((System.currentTimeMillis() and 0x0FFFFFFF).toInt(), notification)
        return true
    }
}

// app/src/main/assets/index.html
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Hybrid WebView Wrapper</title>
    <style>
        body {
            font-family: system-ui, sans-serif;
            margin: 0;
            padding: 24px;
            background: #0f172a;
            color: #e2e8f0;
        }
        h1 {
            margin-top: 0;
        }
        .row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        button {
            border: 0;
            border-radius: 10px;
            padding: 12px 16px;
            background: #2563eb;
            color: white;
            font-size: 14px;
        }
        input, textarea {
            width: 100%;
            box-sizing: border-box;
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #334155;
            background: #111827;
            color: white;
            margin-bottom: 12px;
        }
        pre {
            white-space: pre-wrap;
            word-break: break-word;
            background: #111827;
            border-radius: 12px;
            padding: 16px;
            min-height: 140px;
        }
    </style>
</head>
<body>
    <h1>Hybrid WebView Wrapper</h1>
    <p>This bundled web app demonstrates the native Kotlin bridge.</p>

    <input id="storageKey" value="demo-key" placeholder="Storage key">
    <textarea id="storageValue" rows="4" placeholder="Storage value">Hello from the bundled web app.</textarea>

    <div class="row">
        <button onclick="saveItem()">Save local item</button>
        <button onclick="loadItem()">Load local item</button>
        <button onclick="removeItem()">Remove local item</button>
        <button onclick="clearItems()">Clear storage</button>
    </div>

    <div class="row">
        <button onclick="capturePhoto()">Capture photo</button>
        <button onclick="registerPush()">Register push</button>
        <button onclick="showNotification()">Show notification</button>
        <button onclick="deviceInfo()">Device info</button>
    </div>

    <pre id="output"></pre>

    <script>
        const output = document.getElementById('output');

        function log(value) {
            output.textContent = typeof value === 'string'
                ? value
                : JSON.stringify(value, null, 2);
        }

        function callbackId() {
            return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        }

        window.HybridNative = {
            onMessage(message) {
                log(message);
            }
        };

        window.addEventListener('nativeBridge', event => {
            log(event.detail);
        });

        function saveItem() {
            const response = JSON.parse(
                NativeBridge.setLocalItem(
                    document.getElementById('storageKey').value,
                    document.getElementById('storageValue').value
                )
            );
            log(response);
        }

        function loadItem() {
            const response = JSON.parse(
                NativeBridge.getLocalItem(document.getElementById('storageKey').value)
            );
            log(response);
        }

        function removeItem() {
            const response = JSON.parse(
                NativeBridge.removeLocalItem(document.getElementById('storageKey').value)
            );
            log(response);
        }

        function clearItems() {
            log(JSON.parse(NativeBridge.clearLocalStorage()));
        }

        function capturePhoto() {
            NativeBridge.capturePhoto(callbackId());
        }

        function registerPush() {
            NativeBridge.registerForPushNotifications(callbackId());
        }

        function showNotification() {
            log(JSON.parse(NativeBridge.showNotification(
                'Hybrid WebView',
                'This notification was triggered from web content.'
            )));
        }

        function deviceInfo() {
            log(JSON.parse(NativeBridge.getDeviceInfo()));
        }
    </script>
</body>
</html>