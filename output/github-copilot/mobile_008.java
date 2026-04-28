package com.example.myapp

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import java.util.Locale

class MainActivity : BaseScreenActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!handleDeepLink(intent)) {
            showHome()
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (!handleDeepLink(intent)) {
            showHome()
        }
    }

    private fun handleDeepLink(intent: Intent): Boolean {
        val destination = DeepLinkParser.parse(intent.data) ?: return false

        when (destination) {
            is AppDestination.Profile -> startActivity(ProfileActivity.createIntent(this, destination.userId))
            AppDestination.PaymentConfirm -> startActivity(PaymentConfirmActivity.createIntent(this))
            AppDestination.AdminSettings -> startActivity(AdminSettingsActivity.createIntent(this))
        }

        finish()
        return true
    }

    private fun showHome() {
        setContentView(
            buildScreen(
                title = "MyApp",
                message = "Open a marketing deep link such as myapp://profile/123, myapp://payment/confirm, or myapp://admin/settings.",
                showHomeButton = false
            )
        )
    }
}

class ProfileActivity : BaseScreenActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val userId = intent.getStringExtra(EXTRA_USER_ID).orEmpty()

        setContentView(
            buildScreen(
                title = "Profile",
                message = "Viewing profile for user $userId."
            )
        )
    }

    companion object {
        private const val EXTRA_USER_ID = "extra_user_id"

        fun createIntent(context: Context, userId: String): Intent {
            return Intent(context, ProfileActivity::class.java)
                .putExtra(EXTRA_USER_ID, userId)
        }
    }
}

class PaymentConfirmActivity : BaseScreenActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(
            buildScreen(
                title = "Payment Confirmation",
                message = "Payment confirmation flow opened from deep link."
            )
        )
    }

    companion object {
        fun createIntent(context: Context): Intent {
            return Intent(context, PaymentConfirmActivity::class.java)
        }
    }
}

class AdminSettingsActivity : BaseScreenActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(
            buildScreen(
                title = "Admin Settings",
                message = "Admin settings opened from deep link."
            )
        )
    }

    companion object {
        fun createIntent(context: Context): Intent {
            return Intent(context, AdminSettingsActivity::class.java)
        }
    }
}

abstract class BaseScreenActivity : Activity() {
    protected fun buildScreen(
        title: String,
        message: String,
        showHomeButton: Boolean = true
    ): View {
        val padding = (24 * resources.displayMetrics.density).toInt()

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(padding, padding, padding, padding)
            layoutParams = LinearLayout.LayoutParams(MATCH_PARENT, MATCH_PARENT)
        }

        val titleView = TextView(this).apply {
            text = title
            textSize = 28f
            gravity = Gravity.CENTER
            layoutParams = LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT)
        }

        val messageView = TextView(this).apply {
            text = message
            textSize = 18f
            gravity = Gravity.CENTER
            val params = LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT)
            params.topMargin = padding / 2
            layoutParams = params
        }

        container.addView(titleView)
        container.addView(messageView)

        if (showHomeButton) {
            val button = Button(this).apply {
                text = "Back to Home"
                val params = LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT)
                params.topMargin = padding
                layoutParams = params
                setOnClickListener {
                    startActivity(
                        Intent(this@BaseScreenActivity, MainActivity::class.java).apply {
                            addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                        }
                    )
                    finish()
                }
            }
            container.addView(button)
        }

        return container
    }
}

private sealed class AppDestination {
    data class Profile(val userId: String) : AppDestination()
    object PaymentConfirm : AppDestination()
    object AdminSettings : AppDestination()
}

private object DeepLinkParser {
    fun parse(uri: Uri?): AppDestination? {
        if (uri == null) return null
        if (!uri.scheme.equals("myapp", ignoreCase = true)) return null

        val host = uri.host?.lowercase(Locale.US) ?: return null
        val segments = uri.pathSegments.map { it.trim() }.filter { it.isNotEmpty() }

        return when (host) {
            "profile" -> {
                val userId = segments.singleOrNull() ?: return null
                AppDestination.Profile(userId)
            }
            "payment" -> {
                if (segments == listOf("confirm")) AppDestination.PaymentConfirm else null
            }
            "admin" -> {
                if (segments == listOf("settings")) AppDestination.AdminSettings else null
            }
            else -> null
        }
    }
}