package com.example.sharetarget

import android.app.Activity
import android.content.ContentResolver
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Parcelable
import android.provider.OpenableColumns
import android.util.Log
import android.util.Patterns
import android.view.Gravity
import android.view.View
import android.webkit.MimeTypeMap
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.io.File
import java.io.FileOutputStream
import java.text.DateFormat
import java.util.Date
import java.util.Locale

class ShareReceiverActivity : Activity() {

    private lateinit var statusView: TextView
    private lateinit var detailsView: TextView
    private lateinit var previewImage: ImageView
    private lateinit var openUrlButton: Button

    private var lastSharedUrl: Uri? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        createUi()
        handleIncomingIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIncomingIntent(intent)
    }

    private fun createUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(16))
        }

        val titleView = TextView(this).apply {
            text = "Share Target"
            textSize = 24f
            gravity = Gravity.CENTER_HORIZONTAL
        }

        statusView = TextView(this).apply {
            textSize = 18f
            setPadding(0, dp(16), 0, dp(8))
        }

        openUrlButton = Button(this).apply {
            text = "Open URL"
            visibility = View.GONE
            setOnClickListener {
                val url = lastSharedUrl ?: return@setOnClickListener
                startActivity(Intent(Intent.ACTION_VIEW, url))
            }
        }

        previewImage = ImageView(this).apply {
            visibility = View.GONE
            adjustViewBounds = true
            scaleType = ImageView.ScaleType.FIT_CENTER
            setPadding(0, dp(12), 0, dp(12))
        }

        detailsView = TextView(this).apply {
            textSize = 16f
            setTextIsSelectable(true)
        }

        root.addView(titleView)
        root.addView(statusView)
        root.addView(openUrlButton)
        root.addView(previewImage)
        root.addView(detailsView)

        setContentView(ScrollView(this).apply { addView(root) })
    }

    private fun handleIncomingIntent(intent: Intent?) {
        if (intent == null) {
            renderIdleState()
            return
        }

        when (intent.action) {
            Intent.ACTION_SEND -> handleSend(intent)
            Intent.ACTION_SEND_MULTIPLE -> handleSendMultiple(intent)
            Intent.ACTION_MAIN, null -> renderIdleState()
            else -> renderError("Unsupported action: ${intent.action}")
        }
    }

    private fun handleSend(intent: Intent) {
        val type = intent.type.orEmpty()

        when {
            type.startsWith("image/") -> {
                val imageUri = intent.parcelableExtraCompat<Uri>(Intent.EXTRA_STREAM)
                    ?: extractFirstUriFromClipData(intent)
                if (imageUri == null) {
                    renderError("No image was attached to the share intent.")
                    return
                }
                processSharedImages(listOf(imageUri))
            }

            type == "text/plain" || type == "text/uri-list" || type.isBlank() -> {
                val url = extractSharedUrl(intent)
                if (url == null) {
                    renderError("No valid HTTP(S) URL was found in the shared content.")
                    return
                }
                processSharedUrl(url)
            }

            else -> renderError("Unsupported MIME type: $type")
        }
    }

    private fun handleSendMultiple(intent: Intent) {
        val imageUris = linkedSetOf<Uri>()

        intent.parcelableArrayListExtraCompat<Uri>(Intent.EXTRA_STREAM)
            ?.let { imageUris.addAll(it) }

        val clipData = intent.clipData
        if (clipData != null) {
            for (index in 0 until clipData.itemCount) {
                clipData.getItemAt(index).uri?.let(imageUris::add)
            }
        }

        if (imageUris.isEmpty()) {
            val url = extractSharedUrl(intent)
            if (url != null) {
                processSharedUrl(url)
            } else {
                renderError("No shareable images were found.")
            }
            return
        }

        processSharedImages(imageUris.toList())
    }

    private fun processSharedUrl(url: Uri) {
        lastSharedUrl = url
        openUrlButton.visibility = View.VISIBLE
        previewImage.visibility = View.GONE
        previewImage.setImageDrawable(null)

        val processedAt = DateFormat.getDateTimeInstance().format(Date())

        statusView.text = "Received URL"
        detailsView.text = buildString {
            appendLine("Normalized URL:")
            appendLine(url.toString())
            appendLine()
            appendLine("Host: ${url.host.orEmpty()}")
            appendLine("Path: ${url.path.orEmpty()}")
            appendLine("Processed at: $processedAt")
        }.trim()

        Log.i(TAG, "Processed shared URL: $url")
        Toast.makeText(this, "URL received", Toast.LENGTH_SHORT).show()
    }

    private fun processSharedImages(uris: List<Uri>) {
        lastSharedUrl = null
        openUrlButton.visibility = View.GONE

        val cachedImages = uris.mapNotNull { copyContentImageToCache(it) }
        if (cachedImages.isEmpty()) {
            renderError("The shared image content could not be opened.")
            return
        }

        val firstBitmap = BitmapFactory.decodeFile(cachedImages.first().file.absolutePath)
        if (firstBitmap != null) {
            previewImage.setImageBitmap(firstBitmap)
            previewImage.visibility = View.VISIBLE
        } else {
            previewImage.setImageDrawable(null)
            previewImage.visibility = View.GONE
        }

        val processedAt = DateFormat.getDateTimeInstance().format(Date())

        statusView.text = "Received ${cachedImages.size} image(s)"
        detailsView.text = buildString {
            cachedImages.forEachIndexed { index, image ->
                appendLine("${index + 1}. ${image.displayName}")
                appendLine("   MIME type: ${image.mimeType}")
                appendLine("   Size: ${formatBytes(image.file.length())}")
                appendLine("   Cached file: ${image.file.absolutePath}")
                appendLine()
            }
            append("Processed at: $processedAt")
        }.trim()

        Log.i(TAG, "Processed ${cachedImages.size} shared image(s)")
        Toast.makeText(this, "${cachedImages.size} image(s) received", Toast.LENGTH_SHORT).show()
    }

    private fun renderIdleState() {
        lastSharedUrl = null
        openUrlButton.visibility = View.GONE
        previewImage.visibility = View.GONE
        previewImage.setImageDrawable(null)
        statusView.text = "Ready to receive shared content"
        detailsView.text = "Share a URL or image to this app from another app."
    }

    private fun renderError(message: String) {
        lastSharedUrl = null
        openUrlButton.visibility = View.GONE
        previewImage.visibility = View.GONE
        previewImage.setImageDrawable(null)
        statusView.text = "Share failed"
        detailsView.text = message
        Log.w(TAG, message)
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }

    private fun extractSharedUrl(intent: Intent): Uri? {
        val candidates = mutableListOf<String>()

        intent.getStringExtra(Intent.EXTRA_TEXT)?.let(candidates::add)
        intent.getStringExtra(Intent.EXTRA_HTML_TEXT)?.let(candidates::add)
        intent.dataString?.let(candidates::add)

        val clipData = intent.clipData
        if (clipData != null) {
            for (index in 0 until clipData.itemCount) {
                val item = clipData.getItemAt(index)
                item.text?.toString()?.let(candidates::add)
                item.uri?.toString()?.let(candidates::add)
            }
        }

        for (candidate in candidates) {
            findFirstHttpUrl(candidate)?.let { return it }
        }

        return null
    }

    private fun findFirstHttpUrl(text: String): Uri? {
        val trimmed = text.trim()
        if (trimmed.isEmpty()) return null

        normalizeHttpUrl(trimmed)?.let { return it }

        val matcher = Patterns.WEB_URL.matcher(trimmed)
        while (matcher.find()) {
            val match = matcher.group()
            normalizeHttpUrl(match)?.let { return it }
        }

        return trimmed.lineSequence()
            .map { it.trim() }
            .mapNotNull { normalizeHttpUrl(it) }
            .firstOrNull()
    }

    private fun normalizeHttpUrl(value: String): Uri? {
        val cleaned = value.trim().removePrefix("<").removeSuffix(">")
        if (cleaned.isEmpty()) return null

        val prepared = if ("://" !in cleaned && Patterns.WEB_URL.matcher(cleaned).matches()) {
            "https://$cleaned"
        } else {
            cleaned
        }

        val uri = Uri.parse(prepared)
        val scheme = uri.scheme?.lowercase(Locale.US) ?: return null
        if (scheme != "http" && scheme != "https") return null
        if (uri.host.isNullOrBlank()) return null

        return uri.normalizeScheme()
    }

    private fun extractFirstUriFromClipData(intent: Intent): Uri? {
        val clipData = intent.clipData ?: return null
        for (index in 0 until clipData.itemCount) {
            clipData.getItemAt(index).uri?.let { return it }
        }
        return null
    }

    private fun copyContentImageToCache(uri: Uri): CachedImage? {
        if (uri.scheme != ContentResolver.SCHEME_CONTENT) {
            Log.w(TAG, "Rejected non-content URI: $uri")
            return null
        }

        val mimeType = contentResolver.getType(uri)?.lowercase(Locale.US) ?: return null
        if (!mimeType.startsWith("image/")) {
            Log.w(TAG, "Rejected non-image content: $uri ($mimeType)")
            return null
        }

        val displayName = queryDisplayName(uri)
            ?: "shared_${System.currentTimeMillis()}${extensionForMimeType(mimeType)}"

        val safeName = displayName.replace(Regex("[^A-Za-z0-9._-]"), "_")
        val outputFile = File(cacheDir, "${System.currentTimeMillis()}_$safeName")

        val inputStream = contentResolver.openInputStream(uri) ?: return null
        inputStream.use { input ->
            FileOutputStream(outputFile).use { output ->
                input.copyTo(output)
            }
        }

        return CachedImage(outputFile, displayName, mimeType)
    }

    private fun queryDisplayName(uri: Uri): String? {
        contentResolver.query(
            uri,
            arrayOf(OpenableColumns.DISPLAY_NAME),
            null,
            null,
            null
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                val columnIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (columnIndex >= 0) {
                    return cursor.getString(columnIndex)
                }
            }
        }
        return null
    }

    private fun extensionForMimeType(mimeType: String): String {
        val extension = MimeTypeMap.getSingleton().getExtensionFromMimeType(mimeType)
        return if (extension.isNullOrBlank()) ".img" else ".$extension"
    }

    private fun formatBytes(bytes: Long): String {
        val units = arrayOf("B", "KB", "MB", "GB")
        var size = bytes.toDouble()
        var unitIndex = 0
        while (size >= 1024.0 && unitIndex < units.lastIndex) {
            size /= 1024.0
            unitIndex++
        }
        return String.format(Locale.US, "%.1f %s", size, units[unitIndex])
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    @Suppress("DEPRECATION")
    private inline fun <reified T : Parcelable> Intent.parcelableExtraCompat(name: String): T? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            getParcelableExtra(name, T::class.java)
        } else {
            getParcelableExtra(name) as? T
        }
    }

    @Suppress("DEPRECATION")
    private inline fun <reified T : Parcelable> Intent.parcelableArrayListExtraCompat(name: String): ArrayList<T>? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            getParcelableArrayListExtra(name, T::class.java)
        } else {
            getParcelableArrayListExtra(name)
        }
    }

    private data class CachedImage(
        val file: File,
        val displayName: String,
        val mimeType: String
    )

    companion object {
        private const val TAG = "ShareReceiverActivity"
    }
}