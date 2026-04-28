package com.example.biometricauth

import android.content.Context
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Space
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat

private const val PREFS_NAME = "auth_prefs"
private const val KEY_AUTHENTICATED = "authenticated"

class MainActivity : AppCompatActivity() {

    private lateinit var biometricPrompt: BiometricPrompt
    private lateinit var biometricPromptInfo: BiometricPrompt.PromptInfo

    private lateinit var statusText: TextView
    private lateinit var usernameInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var biometricButton: Button
    private lateinit var passwordButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupBiometric()

        if (isAuthenticated()) {
            showHome()
        } else {
            showLogin(autoPrompt = true)
        }
    }

    private fun showLogin(autoPrompt: Boolean) {
        val padding = (24 * resources.displayMetrics.density).toInt()
        val spacing = (12 * resources.displayMetrics.density).toInt()

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(padding, padding, padding, padding)
        }

        root.addView(TextView(this).apply {
            text = "Welcome back"
            textSize = 26f
        })

        root.addView(TextView(this).apply {
            text = "Use your fingerprint for fast sign-in, or fall back to your password."
            textSize = 15f
            setPadding(0, spacing, 0, spacing)
        })

        statusText = TextView(this).apply {
            text = "Ready to sign in"
            textSize = 14f
        }
        root.addView(statusText)

        root.addView(Space(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                spacing
            )
        })

        usernameInput = EditText(this).apply {
            hint = "Username"
            setSingleLine()
        }
        root.addView(
            usernameInput,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        root.addView(Space(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                spacing
            )
        })

        passwordInput = EditText(this).apply {
            hint = "Password"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            setSingleLine()
        }
        root.addView(
            passwordInput,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        root.addView(Space(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                spacing
            )
        })

        biometricButton = Button(this).apply {
            text = "Sign in with fingerprint"
        }
        root.addView(
            biometricButton,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        root.addView(Space(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                spacing
            )
        })

        passwordButton = Button(this).apply {
            text = "Use password"
        }
        root.addView(
            passwordButton,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        setContentView(root)
        configureLoginUi(autoPrompt)
    }

    private fun configureLoginUi(autoPrompt: Boolean) {
        biometricButton.setOnClickListener {
            launchBiometric()
        }

        passwordButton.setOnClickListener {
            val username = usernameInput.text.toString().trim()
            val password = passwordInput.text.toString()

            if (username.isEmpty()) {
                usernameInput.error = "Enter your username"
                usernameInput.requestFocus()
                return@setOnClickListener
            }

            if (password.isEmpty()) {
                passwordInput.error = "Enter your password"
                passwordInput.requestFocus()
                return@setOnClickListener
            }

            if (isPasswordValid(username, password)) {
                setAuthenticated(true)
                Toast.makeText(this, "Signed in", Toast.LENGTH_SHORT).show()
                showHome()
            } else {
                showStatus("Incorrect username or password. Try again.")
            }
        }

        val canAuthenticate = canUseBiometrics()
        biometricButton.isEnabled = canAuthenticate == BiometricManager.BIOMETRIC_SUCCESS
        biometricButton.alpha = if (biometricButton.isEnabled) 1f else 0.5f

        if (biometricButton.isEnabled && autoPrompt) {
            biometricButton.post { launchBiometric() }
        } else if (!biometricButton.isEnabled) {
            showStatus("Fingerprint sign-in is not available. Use your password to continue.")
        }
    }

    private fun setupBiometric() {
        biometricPrompt = BiometricPrompt(
            this,
            ContextCompat.getMainExecutor(this),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    setAuthenticated(true)
                    Toast.makeText(this@MainActivity, "Fingerprint verified", Toast.LENGTH_SHORT).show()
                    showHome()
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    showStatus("Fingerprint not recognized. Try again or use your password.")
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    showStatus("Fingerprint sign-in unavailable. Please use your password.")
                }
            }
        )

        biometricPromptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Quick sign in")
            .setSubtitle("Use fingerprint authentication")
            .setDescription("If it doesn't work, you can sign in with your password.")
            .setNegativeButtonText("Use password")
            .build()
    }

    private fun launchBiometric() {
        if (canUseBiometrics() == BiometricManager.BIOMETRIC_SUCCESS) {
            biometricPrompt.authenticate(biometricPromptInfo)
        } else {
            showStatus("Fingerprint sign-in is not available. Use your password to continue.")
        }
    }

    private fun showHome() {
        val padding = (24 * resources.displayMetrics.density).toInt()
        val spacing = (16 * resources.displayMetrics.density).toInt()

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(padding, padding, padding, padding)
        }

        root.addView(TextView(this).apply {
            text = "Home"
            textSize = 28f
        })

        root.addView(TextView(this).apply {
            text = "You are signed in."
            textSize = 16f
            setPadding(0, spacing, 0, spacing)
        })

        root.addView(Button(this).apply {
            text = "Log out"
            setOnClickListener {
                setAuthenticated(false)
                showLogin(autoPrompt = false)
            }
        }, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))

        setContentView(root)
    }

    private fun canUseBiometrics(): Int {
        return BiometricManager.from(this)
            .canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)
    }

    private fun isPasswordValid(username: String, password: String): Boolean {
        return username == "demo" && password == "password123"
    }

    private fun isAuthenticated(): Boolean {
        return getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_AUTHENTICATED, false)
    }

    private fun setAuthenticated(authenticated: Boolean) {
        getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_AUTHENTICATED, authenticated)
            .apply()
    }

    private fun showStatus(message: String) {
        if (::statusText.isInitialized) {
            statusText.text = message
        }
    }
}