import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class ShareReceiverActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleShareIntent(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent != null) {
            handleShareIntent(intent)
        }
    }

    private fun handleShareIntent(intent: Intent) {
        when (intent.action) {
            Intent.ACTION_SEND -> {
                val type = intent.type
                if (type != null) {
                    if (type.startsWith("text/")) {
                        handleTextShare(intent)
                    } else if (type.startsWith("image/")) {
                        handleSingleImageShare(intent)
                    }
                }
            }
            Intent.ACTION_SEND_MULTIPLE -> {
                val type = intent.type
                if (type != null && type.startsWith("image/")) {
                    handleMultipleImagesShare(intent)
                }
            }
        }
        finish()
    }

    private fun handleTextShare(intent: Intent) {
        val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT)
        if (!sharedText.isNullOrBlank()) {
            val url = extractUrl(sharedText)
            if (url != null) {
                processSharedUrl(url)
            } else {
                processSharedText(sharedText)
            }
        }
    }

    private fun handleSingleImageShare(intent: Intent) {
        val imageUri = intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM)
        if (imageUri != null) {
            processSharedImages(listOf(imageUri))
        }
    }

    private fun handleMultipleImagesShare(intent: Intent) {
        val imageUris = intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)
        if (!imageUris.isNullOrEmpty()) {
            processSharedImages(imageUris)
        }
    }

    private fun extractUrl(text: String): String? {
        val regex = Regex("""https?://[^\s]+""")
        return regex.find(text)?.value
    }

    private fun processSharedUrl(url: String) {
        // TODO: Implement your URL processing logic here.
        // Example: open internal Activity, send to server, etc.
    }

    private fun processSharedText(text: String) {
        // TODO: Implement your non-URL text processing logic here.
    }

    private fun processSharedImages(imageUris: List<Uri>) {
        // TODO: Implement your image processing logic here.
        // Example: copy, upload, or display images.
    }
}

------------------------------------------------------------

<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.sharing">

    <application
        android:allowBackup="true"
        android:label="@string/app_name"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.App">

        <activity
            android:name=".ShareReceiverActivity"
            android:exported="true">

            <intent-filter>
                <action android:name="android.intent.action.SEND" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="text/plain" />
            </intent-filter>

            <intent-filter>
                <action android:name="android.intent.action.SEND" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="image/*" />
            </intent-filter>

            <intent-filter>
                <action android:name="android.intent.action.SEND_MULTIPLE" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="image/*" />
            </intent-filter>

        </activity>

    </application>

</manifest>