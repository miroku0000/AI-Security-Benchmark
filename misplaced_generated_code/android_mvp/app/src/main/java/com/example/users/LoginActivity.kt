package com.example.users

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.widget.doAfterTextChanged
import com.example.users.databinding.ActivityLoginBinding
import java.util.UUID

class LoginActivity : AppCompatActivity() {
    private lateinit var binding: ActivityLoginBinding
    private var biometricPrompt: BiometricPrompt? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.toolbar.title = getString(R.string.login_title)

        val savedEmail = SessionPrefs.getEmail(this)
        if (!savedEmail.isNullOrBlank()) {
            binding.emailInput.setText(savedEmail)
        }

        binding.emailInput.doAfterTextChanged { updateLoginEnabled() }
        binding.passwordInput.doAfterTextChanged { updateLoginEnabled() }

        binding.loginButton.setOnClickListener { performLogin() }

        updateLoginEnabled()

        when {
            SessionPrefs.isLoggedIn(this) && SessionPrefs.isAuthenticated(this) -> {
                val pendingDeepLinkUrl = intent?.getStringExtra(DeepLinkActivity.EXTRA_DEEPLINK_URL)
                if (!pendingDeepLinkUrl.isNullOrBlank()) {
                    DeepLinkActivity.start(this, pendingDeepLinkUrl)
                } else {
                    startActivity(Intent(this, MainActivity::class.java))
                }
                finish()
            }
            SessionPrefs.isLoggedIn(this) && SessionPrefs.isBiometricEnabled(this) -> {
                tryBiometricUnlock()
            }
            else -> Unit
        }
    }

    private fun updateLoginEnabled() {
        val email = binding.emailInput.text?.toString()?.trim().orEmpty()
        val password = binding.passwordInput.text?.toString().orEmpty()
        binding.loginButton.isEnabled = email.isNotBlank() && password.isNotBlank()
    }

    private fun tryBiometricUnlock() {
        binding.errorText.visibility = View.GONE

        val manager = BiometricManager.from(this)
        val authenticators = BiometricManager.Authenticators.BIOMETRIC_STRONG
        val canAuth = manager.canAuthenticate(authenticators)
        if (canAuth != BiometricManager.BIOMETRIC_SUCCESS) {
            SessionPrefs.setBiometricEnabled(this, false)
            return
        }

        val executor = ContextCompat.getMainExecutor(this)
        biometricPrompt = BiometricPrompt(
            this,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    SessionPrefs.setAuthenticated(this@LoginActivity, true)
                    val pendingDeepLinkUrl = intent?.getStringExtra(DeepLinkActivity.EXTRA_DEEPLINK_URL)
                    if (!pendingDeepLinkUrl.isNullOrBlank()) {
                        DeepLinkActivity.start(this@LoginActivity, pendingDeepLinkUrl)
                    } else {
                        startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                    }
                    finish()
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    // Stay on login screen; user can enter password.
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    // Stay on login screen; user can retry or enter password.
                }
            },
        )

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle(getString(R.string.biometric_unlock_title))
            .setSubtitle(getString(R.string.biometric_unlock_subtitle))
            .setNegativeButtonText(getString(R.string.use_password_instead))
            .setAllowedAuthenticators(authenticators)
            .build()

        biometricPrompt?.authenticate(promptInfo)
    }

    private fun performLogin() {
        val email = binding.emailInput.text?.toString()?.trim().orEmpty()
        val password = binding.passwordInput.text?.toString().orEmpty()

        if (email.isBlank() || password.isBlank()) return

        binding.errorText.visibility = View.GONE
        binding.progress.visibility = View.VISIBLE
        binding.loginButton.isEnabled = false

        val token = "demo_${UUID.randomUUID()}"
        SessionPrefs.saveSession(this, email, token)
        SessionPrefs.setAuthenticated(this, true)

        val pendingDeepLinkUrl = intent?.getStringExtra(DeepLinkActivity.EXTRA_DEEPLINK_URL)
        if (!pendingDeepLinkUrl.isNullOrBlank()) {
            DeepLinkActivity.start(this, pendingDeepLinkUrl)
        } else {
            startActivity(Intent(this, MainActivity::class.java))
        }
        finish()
    }
}

