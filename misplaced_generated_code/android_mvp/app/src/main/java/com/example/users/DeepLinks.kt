package com.example.users

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.net.toUri

class DeepLinkActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val uri = intent?.data
        if (uri == null) {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }

        val destination = DeepLinkRouter.resolve(uri)
        if (destination == null) {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }

        if (!SessionPrefs.isLoggedIn(this) || !SessionPrefs.isAuthenticated(this)) {
            startActivity(
                Intent(this, LoginActivity::class.java)
                    .putExtra(EXTRA_DEEPLINK_URL, uri.toString())
                    .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            )
            finish()
            return
        }

        DeepLinkRouter.navigate(this, destination)
        finish()
    }

    companion object {
        const val EXTRA_DEEPLINK_URL = "com.example.users.extra.DEEPLINK_URL"

        fun start(context: Context, url: String) {
            val uri = try {
                url.toUri()
            } catch (_: Exception) {
                null
            }
            if (uri == null) {
                context.startActivity(Intent(context, MainActivity::class.java))
                return
            }
            context.startActivity(
                Intent(context, DeepLinkActivity::class.java)
                    .setAction(Intent.ACTION_VIEW)
                    .setData(uri)
                    .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            )
        }
    }
}

private object DeepLinkRouter {
    sealed class Destination {
        data class Profile(val userId: String) : Destination()
        data object PaymentConfirm : Destination()
        data object AdminSettings : Destination()
    }

    fun resolve(uri: Uri): Destination? {
        if (!uri.scheme.equals("myapp", ignoreCase = true)) return null

        val host = uri.host.orEmpty()
        val segments = uri.pathSegments ?: emptyList()

        val primary = host.ifBlank { segments.firstOrNull().orEmpty() }.lowercase()
        val tailSegments = if (host.isBlank() && segments.isNotEmpty()) segments.drop(1) else segments

        return when (primary) {
            "profile" -> {
                val id = tailSegments.firstOrNull()?.trim().orEmpty()
                if (id.isBlank()) null else Destination.Profile(id)
            }
            "payment" -> {
                val next = tailSegments.firstOrNull()?.lowercase()
                if (next == "confirm") Destination.PaymentConfirm else null
            }
            "admin" -> {
                val next = tailSegments.firstOrNull()?.lowercase()
                if (next == "settings") Destination.AdminSettings else null
            }
            else -> null
        }
    }

    fun navigate(context: Context, destination: Destination) {
        val intent = when (destination) {
            is Destination.Profile ->
                Intent(context, ProfileActivity::class.java)
                    .putExtra(ProfileActivity.EXTRA_PROFILE_ID, destination.userId)
            Destination.PaymentConfirm -> Intent(context, PaymentConfirmActivity::class.java)
            Destination.AdminSettings -> Intent(context, AdminSettingsActivity::class.java)
        }

        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        context.startActivity(intent)
    }
}

class ProfileActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val id = intent?.getStringExtra(EXTRA_PROFILE_ID).orEmpty()
        setContentView(
            TextView(this).apply {
                gravity = Gravity.CENTER
                text = if (id.isBlank()) "Profile" else "Profile: $id"
                textSize = 20f
            },
        )
    }

    companion object {
        const val EXTRA_PROFILE_ID = "com.example.users.extra.PROFILE_ID"
    }
}

class PaymentConfirmActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(
            TextView(this).apply {
                gravity = Gravity.CENTER
                text = "Payment confirmation"
                textSize = 20f
            },
        )
    }
}

class AdminSettingsActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(
            TextView(this).apply {
                gravity = Gravity.CENTER
                text = "Admin settings"
                textSize = 20f
            },
        )
    }
}

