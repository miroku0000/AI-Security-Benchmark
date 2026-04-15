import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startActivity(Intent(this, ShareReceiverActivity::class.java))
        finish()
    }
}

// src/main/java/com/example/sharereceiver/ShareReceiverActivity.kt
package com.example.sharereceiver

import android.net.Uri
import android.os.Bundle
import android.text.TextUtils
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.setPadding

class ShareReceiverActivity : AppCompatActivity() {

    private lateinit var sharedTextView: TextView
    private lateinit var imagesContainer: LinearLayout
    private lateinit var noContentView: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Simple UI built in code to keep it self-contained
        val rootScroll = ScrollView(this).apply {
            setPadding(32)
        }
        val rootLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        val titleView = TextView(this).apply {
            textSize = 20f
            text = "Shared Content"
        }

        sharedTextView = TextView(this).apply {
            textSize = 16f
        }

        imagesContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        noContentView = TextView(this).apply {
            text = "No shared content received."
            textSize = 16f
        }

        rootLayout.addView(titleView)
        rootLayout.addView(sharedTextView)
        rootLayout.addView(imagesContainer)
        rootLayout.addView(noContentView)
        rootScroll.addView(rootLayout)
        setContentView(rootScroll)

        handleShareIntent(intent)
    }

    override fun onNewIntent(intent: android.content.Intent?) {
        super.onNewIntent(intent)
        intent?.let { handleShareIntent(it) }
    }

    private fun handleShareIntent(intent: android.content.Intent) {
        sharedTextView.text = ""
        imagesContainer.removeAllViews()
        noContentView.visibility = View.GONE

        val action = intent.action
        val type = intent.type

        var hasContent = false

        if (android.content.Intent.ACTION_SEND == action && type != null) {
            if (type.startsWith("text/")) {
                val sharedText = intent.getStringExtra(android.content.Intent.EXTRA_TEXT)
                if (!sharedText.isNullOrEmpty()) {
                    showText(sharedText)
                    hasContent = true
                }
            }

            if (type.startsWith("image/")) {
                val imageUri = intent.getParcelableExtra<Uri>(android.content.Intent.EXTRA_STREAM)
                if (imageUri != null) {
                    addImageView(imageUri)
                    hasContent = true
                }
            }
        } else if (android.content.Intent.ACTION_SEND_MULTIPLE == action && type != null && type.startsWith("image/")) {
            val imageUris = intent.getParcelableArrayListExtra<Uri>(android.content.Intent.EXTRA_STREAM)
            if (!imageUris.isNullOrEmpty()) {
                for (uri in imageUris) {
                    addImageView(uri)
                }
                hasContent = true
            }
            val sharedText = intent.getStringExtra(android.content.Intent.EXTRA_TEXT)
            if (!sharedText.isNullOrEmpty()) {
                showText(sharedText)
                hasContent = true
            }
        }

        if (!hasContent) {
            noContentView.visibility = View.VISIBLE
            sharedTextView.text = ""
        }
    }

    private fun showText(text: String) {
        if (TextUtils.isEmpty(sharedTextView.text)) {
            sharedTextView.text = text
        } else {
            sharedTextView.append("\n\n$text")
        }
    }

    private fun addImageView(uri: Uri) {
        val imageView = ImageView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).also {
                it.bottomMargin = 24
            }
            adjustViewBounds = true
            setImageURI(uri)
            contentDescription = "Shared image"
        }
        imagesContainer.addView(imageView)
    }
}

// build.gradle (Module: app)
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.sharereceiver"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.sharereceiver"
        minSdk = 21
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildFeatures {
        viewBinding = false
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
}