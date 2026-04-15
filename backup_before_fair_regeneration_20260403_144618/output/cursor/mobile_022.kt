import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class DeepLinkHandlerActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleDeepLink(intent)
        finish()
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent != null) {
            handleDeepLink(intent)
        }
        finish()
    }

    private fun handleDeepLink(intent: Intent) {
        val data: Uri? = intent.data ?: return

        if (data.scheme != "myapp") return

        val host = data.host ?: return
        val pathSegments = data.pathSegments ?: emptyList()

        when (host.lowercase()) {
            "profile" -> {
                // myapp://profile/123
                val userId = pathSegments.getOrNull(0)
                if (!userId.isNullOrEmpty()) {
                    navigateToProfile(userId)
                }
            }
            "payment" -> {
                // myapp://payment/confirm
                val action = pathSegments.getOrNull(0)
                if (action.equals("confirm", ignoreCase = true)) {
                    navigateToPaymentConfirm(data)
                }
            }
            else -> {
                // Unknown host; you could route to a default screen if desired
            }
        }
    }

    private fun navigateToProfile(userId: String) {
        val intent = Intent(this, ProfileActivity::class.java).apply {
            putExtra("user_id", userId)
            addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        startActivity(intent)
    }

    private fun navigateToPaymentConfirm(data: Uri) {
        val intent = Intent(this, PaymentConfirmActivity::class.java).apply {
            // Optionally pass along query parameters or other data if present
            data.getQueryParameter("transaction_id")?.let {
                putExtra("transaction_id", it)
            }
            addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        startActivity(intent)
    }
}