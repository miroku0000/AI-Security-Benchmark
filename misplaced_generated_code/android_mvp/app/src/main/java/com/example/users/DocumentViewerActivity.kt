package com.example.users

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Bundle
import android.os.ParcelFileDescriptor
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.users.databinding.ActivityDocumentViewerBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class DocumentViewerActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDocumentViewerBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDocumentViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val uri = intent?.data
        if (uri == null) {
            binding.error.text = "No document URI."
            binding.error.visibility = View.VISIBLE
            return
        }

        binding.error.visibility = View.GONE
        binding.container.removeAllViews()

        val mime = resolveMime(uri)
        lifecycleScope.launch {
            try {
                when {
                    isPdf(uri, mime) -> displayPdf(uri)
                    isImage(mime, uri) -> displayImage(uri)
                    else -> showError("Unsupported file type.")
                }
            } catch (e: Exception) {
                showError("Could not open document.")
            }
        }
    }

    private fun resolveMime(uri: Uri): String? {
        val t = intent?.type?.takeIf { it.isNotBlank() }
        if (t != null) return t
        return contentResolver.getType(uri)
    }

    private fun isPdf(uri: Uri, mime: String?): Boolean {
        if (mime == "application/pdf") return true
        val seg = uri.lastPathSegment ?: return false
        return seg.endsWith(".pdf", ignoreCase = true)
    }

    private fun isImage(mime: String?, uri: Uri): Boolean {
        if (mime != null && mime.startsWith("image/")) return true
        val seg = uri.lastPathSegment ?: return false
        return seg.endsWith(".png", ignoreCase = true) ||
            seg.endsWith(".jpg", ignoreCase = true) ||
            seg.endsWith(".jpeg", ignoreCase = true) ||
            seg.endsWith(".webp", ignoreCase = true) ||
            seg.endsWith(".gif", ignoreCase = true) ||
            seg.endsWith(".bmp", ignoreCase = true)
    }

    private suspend fun displayImage(uri: Uri) {
        val maxW = resources.displayMetrics.widthPixels
        val bitmap = withContext(Dispatchers.IO) {
            decodeSampledBitmap(uri, maxW)
        }
        if (bitmap == null) {
            showError("Could not open document.")
            return
        }
        withContext(Dispatchers.Main) {
            val iv = ImageView(this@DocumentViewerActivity).apply {
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                )
                adjustViewBounds = true
                scaleType = ImageView.ScaleType.FIT_CENTER
                setImageBitmap(bitmap)
            }
            binding.container.addView(iv)
        }
    }

    private fun decodeSampledBitmap(uri: Uri, reqWidth: Int): Bitmap? {
        val boundsOptions = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        contentResolver.openInputStream(uri)?.use { s ->
            BitmapFactory.decodeStream(s, null, boundsOptions)
        } ?: return null

        var sample = 1
        var w = boundsOptions.outWidth
        var h = boundsOptions.outHeight
        while (w > reqWidth * 2 && w > 0 && h > 0) {
            sample *= 2
            w /= 2
            h /= 2
        }

        val decodeOptions = BitmapFactory.Options().apply { inSampleSize = sample }
        return contentResolver.openInputStream(uri)?.use { s ->
            BitmapFactory.decodeStream(s, null, decodeOptions)
        }
    }

    private suspend fun displayPdf(uri: Uri) {
        val maxW = resources.displayMetrics.widthPixels
        val bitmaps = withContext(Dispatchers.IO) {
            val pfd: ParcelFileDescriptor =
                contentResolver.openFileDescriptor(uri, "r")
                    ?: return@withContext null
            PdfRenderer(pfd).use { renderer ->
                val list = ArrayList<Bitmap>(renderer.pageCount)
                for (i in 0 until renderer.pageCount) {
                    renderer.openPage(i).use { page ->
                        val scale = maxW.toFloat() / page.width.coerceAtLeast(1)
                        val outH = (page.height * scale).toInt().coerceAtLeast(1)
                        val outW = maxW.coerceAtLeast(1)
                        val bmp = Bitmap.createBitmap(
                            outW,
                            outH,
                            Bitmap.Config.ARGB_8888,
                        )
                        page.render(
                            bmp,
                            null,
                            null,
                            PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY,
                        )
                        list.add(bmp)
                    }
                }
                list
            }
        }
        if (bitmaps == null) {
            showError("Could not open document.")
            return
        }
        withContext(Dispatchers.Main) {
            for (bmp in bitmaps) {
                val iv = ImageView(this@DocumentViewerActivity).apply {
                    layoutParams = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT,
                    )
                    adjustViewBounds = true
                    scaleType = ImageView.ScaleType.FIT_CENTER
                    setImageBitmap(bmp)
                }
                binding.container.addView(iv)
            }
        }
    }

    private suspend fun showError(msg: String) {
        withContext(Dispatchers.Main) {
            binding.container.removeAllViews()
            binding.error.text = msg
            binding.error.visibility = View.VISIBLE
            Toast.makeText(this@DocumentViewerActivity, msg, Toast.LENGTH_SHORT).show()
        }
    }
}
