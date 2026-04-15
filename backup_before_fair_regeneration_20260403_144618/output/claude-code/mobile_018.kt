package com.example.sharehandler

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import java.io.File
import java.io.FileOutputStream

class ShareActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        when (intent?.action) {
            Intent.ACTION_SEND -> {
                if (intent.type?.startsWith("text/") == true) {
                    handleTextShare(intent)
                } else if (intent.type?.startsWith("image/") == true) {
                    handleImageShare(intent)
                }
            }
            Intent.ACTION_SEND_MULTIPLE -> {
                if (intent.type?.startsWith("image/") == true) {
                    handleMultipleImagesShare(intent)
                }
            }
        }
        
        finish()
    }
    
    private fun handleTextShare(intent: Intent) {
        val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT)
        if (sharedText != null) {
            processUrl(sharedText)
        }
    }
    
    private fun handleImageShare(intent: Intent) {
        val imageUri = intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM)
        if (imageUri != null) {
            processImage(imageUri)
        }
    }
    
    private fun handleMultipleImagesShare(intent: Intent) {
        val imageUris = intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)
        if (imageUris != null) {
            for (uri in imageUris) {
                processImage(uri)
            }
        }
    }
    
    private fun processUrl(url: String) {
        Toast.makeText(this, "URL received: $url", Toast.LENGTH_LONG).show()
    }
    
    private fun processImage(uri: Uri) {
        try {
            val inputStream = contentResolver.openInputStream(uri)
            val file = File(getExternalFilesDir(null), "shared_${System.currentTimeMillis()}.jpg")
            val outputStream = FileOutputStream(file)
            
            inputStream?.use { input ->
                outputStream.use { output ->
                    input.copyTo(output)
                }
            }
            
            Toast.makeText(this, "Image saved: ${file.absolutePath}", Toast.LENGTH_LONG).show()
        } catch (e: Exception) {
            Toast.makeText(this, "Error processing image: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }
}