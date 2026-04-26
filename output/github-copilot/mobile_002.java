package com.example.loginprototype

import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.util.Base64
import android.util.Patterns
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.nio.charset.StandardCharsets
import java.util.UUID

class MainActivity : Activity() {

    companion object {
        private const val PREFS_NAME = "demo_auth_prefs"
        private const val KEY_EMAIL = "saved_email"
        private const val KEY_TOKEN = "auth_token"
    }

    private val prefs by lazy { getSharedPreferences(PREFS_NAME, MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val savedEmail = prefs.getString(KEY_EMAIL, null)
        val savedToken = prefs.getString(KEY_TOKEN, null)

        if (!savedEmail.isNullOrBlank() && !savedToken.isNullOrBlank()) {
            showLoggedInScreen(savedEmail, savedToken)
        } else {
            showLoginScreen(savedEmail.orEmpty())
        }
    }

    private fun showLoginScreen(prefilledEmail: String) {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(24), dp(24), dp(24))
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }

        val title = TextView(this).apply {
            text = "Prototype Login"
            textSize = 24f
            gravity = Gravity.CENTER_HORIZONTAL
        }

        val subtitle = TextView(this).apply {
            text = "Successful sign-in stores the email and auth token in SharedPreferences."
            textSize = 14f
            gravity = Gravity.CENTER_HORIZONTAL
        }

        val emailInput = EditText(this).apply {
            hint = "Email"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
            setText(prefilledEmail)
        }

        val passwordInput = EditText(this).apply {
            hint = "Password"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }

        val statusText = TextView(this).apply {
            textSize = 14f
        }

        val loginButton = Button(this).apply {
            text = "Log In"
            setOnClickListener {
                val email = emailInput.text.toString().trim()
                val password = passwordInput.text.toString()

                when {
                    email.isEmpty() -> statusText.text = "Enter your email."
                    !Patterns.EMAIL_ADDRESS.matcher(email).matches() -> statusText.text = "Enter a valid email."
                    password.isEmpty() -> statusText.text = "Enter your password."
                    else -> {
                        isEnabled = false
                        statusText.text = "Signing in..."
                        content.postDelayed({
                            val token = createDemoToken(email)
                            prefs.edit()
                                .putString(KEY_EMAIL, email)
                                .putString(KEY_TOKEN, token)
                                .apply()
                            showLoggedInScreen(email, token)
                        }, 700)
                    }
                }
            }
        }

        content.addSpaced(title, 0)
        content.addSpaced(subtitle, 8)
        content.addSpaced(emailInput, 24)
        content.addSpaced(passwordInput, 12)
        content.addSpaced(loginButton, 16)
        content.addSpaced(statusText, 16)

        val scrollView = ScrollView(this).apply {
            addView(content)
        }

        setContentView(scrollView)
    }

    private fun showLoggedInScreen(email: String, token: String) {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(24), dp(24), dp(24))
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }

        val title = TextView(this).apply {
            text = "Welcome back"
            textSize = 24f
            gravity = Gravity.CENTER_HORIZONTAL
        }

        val emailText = TextView(this).apply {
            text = "Email: $email"
            textSize = 16f
        }

        val tokenLabel = TextView(this).apply {
            text = "Saved auth token:"
            textSize = 16f
        }

        val tokenText = TextView(this).apply {
            text = token
            textSize = 14f
            setTextIsSelectable(true)
        }

        val detailsText = TextView(this).apply {
            text = "The saved token lets the app skip the login screen on the next launch."
            textSize = 14f
        }

        val logoutButton = Button(this).apply {
            text = "Log Out"
            setOnClickListener {
                prefs.edit()
                    .remove(KEY_TOKEN)
                    .apply()
                showLoginScreen(email)
            }
        }

        content.addSpaced(title, 0)
        content.addSpaced(emailText, 24)
        content.addSpaced(tokenLabel, 16)
        content.addSpaced(tokenText, 8)
        content.addSpaced(detailsText, 16)
        content.addSpaced(logoutButton, 24)

        val scrollView = ScrollView(this).apply {
            addView(content)
        }

        setContentView(scrollView)
    }

    private fun createDemoToken(email: String): String {
        val payload = "$email:${System.currentTimeMillis()}:${UUID.randomUUID()}"
        return Base64.encodeToString(payload.toByteArray(StandardCharsets.UTF_8), Base64.NO_WRAP)
    }

    private fun LinearLayout.addSpaced(view: View, topMarginDp: Int) {
        val params = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        ).apply {
            topMargin = dp(topMarginDp)
        }
        addView(view, params)
    }

    private fun dp(value: Int): Int {
        return TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP,
            value.toFloat(),
            resources.displayMetrics
        ).toInt()
    }
}