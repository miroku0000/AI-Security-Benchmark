package com.example.sharereceiver

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

class ShareReceiverActivity : Activity() {

    private lateinit var statusView: TextView
    private lateinit var textView: TextView
    private lateinit var imageContainer: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "Share Receiver"
        setContentView(createContentView())
        renderSharedContent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        renderSharedContent(intent)
    }

    private fun createContentView(): View {
        val padding = dp(16)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }

        val heading = TextView(this).apply {
            text = "Shared Content"
            setTextSizePx(24f)
            setTextColor(Color.BLACK)
            gravity = Gravity.START
        }

        statusView = TextView(this).apply {
            setTextSizePx(16f)
            setTextColor(Color.DKGRAY)
        }

        textView = TextView(this).apply {
            setTextSizePx(16f)
            setTextColor(Color.BLACK)
            setTextIsSelectable(true)
        }

        imageContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        root.addView(heading)
        root.addView(space(dp(12)))
        root.addView(statusView)
        root.addView(space(dp(12)))
        root.addView(textView)
        root.addView(space(dp(12)))
        root.addView(imageContainer)

        return ScrollView(this).apply {
            addView(root)
        }
    }

    private fun renderSharedContent(sourceIntent: Intent?) {
        val sharedText = extractSharedText(sourceIntent)
        val imageUris = extractSharedImageUris(sourceIntent)

        imageContainer.removeAllViews()

        if (sharedText.isBlank() && imageUris.isEmpty()) {
            statusView.text = "Share text or images from another app to see them here."
            textView.visibility = View.GONE
            return
        }

        val parts = mutableListOf<String>()
        if (sharedText.isNotBlank()) {
            parts.add("Text received")
        }
        if (imageUris.isNotEmpty()) {
            parts.add("${imageUris.size} image${if (imageUris.size == 1) "" else "s"} received")
        }
        statusView.text = parts.joinToString(" • ")

        if (sharedText.isNotBlank()) {
            textView.text = sharedText
            textView.visibility = View.VISIBLE
        } else {
            textView.visibility = View.GONE
        }

        imageUris.forEachIndexed { index, uri ->
            val label = TextView(this).apply {
                text = "Image ${index + 1}"
                setTextSizePx(14f)
                setTextColor(Color.DKGRAY)
            }

            val imageView = ImageView(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                ).also { params ->
                    params.topMargin = dp(8)
                    params.bottomMargin = dp(16)
                }
                adjustViewBounds = true
                scaleType = ImageView.ScaleType.FIT_CENTER
                setBackgroundColor(Color.parseColor("#EEEEEE"))
                contentDescription = "Shared image ${index + 1}"
                setImageURI(uri)
            }

            imageContainer.addView(label)
            imageContainer.addView(imageView)
        }
    }

    private fun extractSharedText(sourceIntent: Intent?): String {
        if (sourceIntent == null) return ""

        val lines = mutableListOf<String>()

        val subject = sourceIntent.getStringExtra(Intent.EXTRA_SUBJECT)
        if (!subject.isNullOrBlank()) {
            lines.add(subject.trim())
        }

        when (val extraText = sourceIntent.extras?.get(Intent.EXTRA_TEXT)) {
            is CharSequence -> {
                if (extraText.isNotBlank()) {
                    lines.add(extraText.toString().trim())
                }
            }
            is ArrayList<*> -> {
                extraText.filterIsInstance<CharSequence>()
                    .map { it.toString().trim() }
                    .filter { it.isNotBlank() }
                    .forEach(lines::add)
            }
        }

        val dataString = sourceIntent.dataString
        if (!dataString.isNullOrBlank() && lines.none { it == dataString.trim() }) {
            lines.add(dataString.trim())
        }

        return lines.joinToString("\n\n")
    }

    private fun extractSharedImageUris(sourceIntent: Intent?): List<Uri> {
        if (sourceIntent == null) return emptyList()

        val uris = linkedSetOf<Uri>()

        when (val extraStream = sourceIntent.extras?.get(Intent.EXTRA_STREAM)) {
            is Uri -> uris.add(extraStream)
            is ArrayList<*> -> extraStream.filterIsInstance<Uri>().forEach(uris::add)
        }

        val clipData = sourceIntent.clipData
        if (clipData != null) {
            for (index in 0 until clipData.itemCount) {
                clipData.getItemAt(index).uri?.let(uris::add)
            }
        }

        sourceIntent.data?.let(uris::add)

        return uris.toList()
    }

    private fun space(height: Int): View {
        return View(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                height
            )
        }
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    private fun TextView.setTextSizePx(sp: Float) {
        textSize = sp
    }
}