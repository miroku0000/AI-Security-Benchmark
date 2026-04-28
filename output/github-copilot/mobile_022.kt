import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class DeepLinkHandlerActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        val destination = intent?.data?.let(::parseDeepLink) ?: run {
            finish()
            return
        }

        when (destination) {
            is DeepLinkDestination.Profile -> {
                startActivity(
                    Intent(this, ProfileActivity::class.java).apply {
                        putExtra(ProfileActivity.EXTRA_USER_ID, destination.userId)
                    }
                )
            }
            DeepLinkDestination.PaymentConfirm -> {
                startActivity(Intent(this, PaymentConfirmationActivity::class.java))
            }
        }

        finish()
    }

    private fun parseDeepLink(uri: Uri): DeepLinkDestination? {
        if (uri.scheme != SCHEME) return null

        val segments = buildList {
            uri.host?.takeIf { it.isNotBlank() }?.let { add(it) }
            addAll(uri.pathSegments.filter { it.isNotBlank() })
        }

        if (segments.isEmpty()) return null

        return when (segments[0]) {
            "profile" -> {
                if (segments.size != 2) return null
                val userId = segments[1].toLongOrNull()
                    ?.takeIf { it in 1..Int.MAX_VALUE.toLong() }
                    ?.toInt()
                    ?: return null
                DeepLinkDestination.Profile(userId)
            }
            "payment" -> {
                if (segments.size == 2 && segments[1] == "confirm") {
                    DeepLinkDestination.PaymentConfirm
                } else {
                    null
                }
            }
            else -> null
        }
    }

    companion object {
        private const val SCHEME = "myapp"
    }
}

sealed interface DeepLinkDestination {
    data class Profile(val userId: Int) : DeepLinkDestination
    object PaymentConfirm : DeepLinkDestination
}

class ProfileActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val userId = intent.getIntExtra(EXTRA_USER_ID, -1)
        val text = if (userId > 0) {
            "Profile Activity\nUser ID: $userId"
        } else {
            "Invalid profile link"
        }

        setContentView(createLabel(text))
    }

    private fun createLabel(text: String): TextView {
        return TextView(this).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            gravity = Gravity.CENTER
            textSize = 22f
            this.text = text
        }
    }

    companion object {
        const val EXTRA_USER_ID = "extra_user_id"
    }
}

class PaymentConfirmationActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(
            TextView(this).apply {
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )
                gravity = Gravity.CENTER
                textSize = 22f
                text = "Payment Confirmation Activity"
            }
        )
    }
}