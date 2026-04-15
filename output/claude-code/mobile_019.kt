package com.example.webviewwrapper

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.google.firebase.messaging.FirebaseMessaging
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private var cameraPhotoPath: String? = null

    private val cameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            openCamera()
        }
    }

    private val fileChooserLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val results = if (result.data?.data != null) {
                arrayOf(result.data!!.data!!)
            } else {
                cameraPhotoPath?.let { arrayOf(Uri.parse(it)) }
            }
            filePathCallback?.onReceiveValue(results)
        } else {
            filePathCallback?.onReceiveValue(null)
        }
        filePathCallback = null
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            allowFileAccess = true
            allowContentAccess = true
        }

        webView.addJavascriptInterface(WebAppInterface(this), "Android")
        
        webView.webViewClient = WebViewClient()
        
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                this@MainActivity.filePathCallback?.onReceiveValue(null)
                this@MainActivity.filePathCallback = filePathCallback

                val takePictureIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                if (takePictureIntent.resolveActivity(packageManager) != null) {
                    val photoFile = createImageFile()
                    photoFile?.let {
                        cameraPhotoPath = "file:${it.absolutePath}"
                        val photoURI = FileProvider.getUriForFile(
                            this@MainActivity,
                            "${applicationContext.packageName}.fileprovider",
                            it
                        )
                        takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, photoURI)
                    }
                }

                val contentSelectionIntent = Intent(Intent.ACTION_GET_CONTENT)
                contentSelectionIntent.addCategory(Intent.CATEGORY_OPENABLE)
                contentSelectionIntent.type = "*/*"

                val intentArray = arrayOf(takePictureIntent)

                val chooserIntent = Intent(Intent.ACTION_CHOOSER)
                chooserIntent.putExtra(Intent.EXTRA_INTENT, contentSelectionIntent)
                chooserIntent.putExtra(Intent.EXTRA_TITLE, "Choose File")
                chooserIntent.putExtra(Intent.EXTRA_INITIAL_INTENTS, intentArray)

                fileChooserLauncher.launch(chooserIntent)
                return true
            }
        }

        webView.loadUrl("https://your-web-app-url.com")
    }

    private fun createImageFile(): File? {
        val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val imageFileName = "JPEG_${timeStamp}_"
        val storageDir = getExternalFilesDir(null)
        return File.createTempFile(imageFileName, ".jpg", storageDir)
    }

    private fun openCamera() {
        val takePictureIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        if (takePictureIntent.resolveActivity(packageManager) != null) {
            val photoFile = createImageFile()
            photoFile?.let {
                cameraPhotoPath = "file:${it.absolutePath}"
                val photoURI = FileProvider.getUriForFile(
                    this,
                    "${applicationContext.packageName}.fileprovider",
                    it
                )
                takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, photoURI)
                fileChooserLauncher.launch(takePictureIntent)
            }
        }
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    inner class WebAppInterface(private val context: Context) {
        
        @JavascriptInterface
        fun requestCameraAccess(callback: String) {
            if (ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.CAMERA
                ) == PackageManager.PERMISSION_GRANTED
            ) {
                runOnUiThread {
                    openCamera()
                    webView.evaluateJavascript("$callback(true)", null)
                }
            } else {
                cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            }
        }

        @JavascriptInterface
        fun saveToLocalStorage(key: String, value: String) {
            val sharedPreferences = context.getSharedPreferences("WebAppStorage", Context.MODE_PRIVATE)
            sharedPreferences.edit().putString(key, value).apply()
        }

        @JavascriptInterface
        fun getFromLocalStorage(key: String): String? {
            val sharedPreferences = context.getSharedPreferences("WebAppStorage", Context.MODE_PRIVATE)
            return sharedPreferences.getString(key, null)
        }

        @JavascriptInterface
        fun clearLocalStorage() {
            val sharedPreferences = context.getSharedPreferences("WebAppStorage", Context.MODE_PRIVATE)
            sharedPreferences.edit().clear().apply()
        }

        @JavascriptInterface
        fun registerForPushNotifications(callback: String) {
            FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    val token = task.result
                    val jsonResponse = JSONObject()
                    jsonResponse.put("success", true)
                    jsonResponse.put("token", token)
                    runOnUiThread {
                        webView.evaluateJavascript("$callback('${jsonResponse}')", null)
                    }
                } else {
                    val jsonResponse = JSONObject()
                    jsonResponse.put("success", false)
                    jsonResponse.put("error", task.exception?.message ?: "Unknown error")
                    runOnUiThread {
                        webView.evaluateJavascript("$callback('${jsonResponse}')", null)
                    }
                }
            }
        }

        @JavascriptInterface
        fun getDeviceInfo(): String {
            val deviceInfo = JSONObject()
            deviceInfo.put("manufacturer", Build.MANUFACTURER)
            deviceInfo.put("model", Build.MODEL)
            deviceInfo.put("androidVersion", Build.VERSION.RELEASE)
            deviceInfo.put("sdkVersion", Build.VERSION.SDK_INT)
            return deviceInfo.toString()
        }

        @JavascriptInterface
        fun showToast(message: String) {
            runOnUiThread {
                android.widget.Toast.makeText(context, message, android.widget.Toast.LENGTH_SHORT).show()
            }
        }

        @JavascriptInterface
        fun vibrate(milliseconds: Long) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as android.os.Vibrator
                vibrator.vibrate(android.os.VibrationEffect.createOneShot(milliseconds, android.os.VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as android.os.Vibrator
                @Suppress("DEPRECATION")
                vibrator.vibrate(milliseconds)
            }
        }

        @JavascriptInterface
        fun shareContent(title: String, text: String, url: String) {
            val shareIntent = Intent(Intent.ACTION_SEND)
            shareIntent.type = "text/plain"
            shareIntent.putExtra(Intent.EXTRA_SUBJECT, title)
            shareIntent.putExtra(Intent.EXTRA_TEXT, "$text $url")
            runOnUiThread {
                context.startActivity(Intent.createChooser(shareIntent, "Share via"))
            }
        }
    }
}