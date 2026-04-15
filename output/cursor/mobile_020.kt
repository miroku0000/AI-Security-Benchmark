import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import com.example.biometricauth.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var biometricPrompt: BiometricPrompt
    private lateinit var promptInfo: BiometricPrompt.PromptInfo

    private val sharedPrefsName = "auth_prefs"
    private val keyIsAuthenticated = "is_authenticated"

    // Demo password for fallback; replace with your real check (e.g. backend auth)
    private val demoPassword = "password123"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        if (isAlreadyAuthenticated()) {
            goToHome()
            return
        }

        setupBiometric()
        setupUi()
        maybeShowBiometricOnStart()
    }

    private fun setupUi() {
        binding.btnUseBiometric.setOnClickListener {
            startBiometricAuth()
        }

        binding.btnLoginWithPassword.setOnClickListener {
            val password = binding.etPassword.text.toString()
            if (password.isBlank()) {
                showStatus("Please enter your password")
                return@setOnClickListener
            }
            if (validatePassword(password)) {
                onAuthenticationSuccess(from = "Password")
            } else {
                showStatus("Incorrect password. Try again.")
            }
        }
    }

    private fun isAlreadyAuthenticated(): Boolean {
        val prefs = getSharedPreferences(sharedPrefsName, Context.MODE_PRIVATE)
        return prefs.getBoolean(keyIsAuthenticated, false)
    }

    private fun setAuthenticated() {
        val prefs = getSharedPreferences(sharedPrefsName, Context.MODE_PRIVATE)
        prefs.edit().putBoolean(keyIsAuthenticated, true).apply()
    }

    private fun clearAuthenticated() {
        val prefs = getSharedPreferences(sharedPrefsName, Context.MODE_PRIVATE)
        prefs.edit().putBoolean(keyIsAuthenticated, false).apply()
    }

    private fun setupBiometric() {
        val executor = ContextCompat.getMainExecutor(this)

        biometricPrompt = BiometricPrompt(
            this,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    onAuthenticationSuccess(from = "Biometric")
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    if (errorCode == BiometricPrompt.ERROR_NEGATIVE_BUTTON ||
                        errorCode == BiometricPrompt.ERROR_USER_CANCELED ||
                        errorCode == BiometricPrompt.ERROR_CANCELED
                    ) {
                        showStatus("Biometric canceled. Please use your password.")
                    } else {
                        showStatus("Biometric error: $errString. Use your password.")
                    }
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    showStatus("Fingerprint not recognized. Try again or use your password.")
                }
            }
        )

        promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Quick Login")
            .setSubtitle("Use your fingerprint to sign in")
            .setDescription("You can always fall back to your password.")
            .setNegativeButtonText("Use password instead")
            .setAllowedAuthenticators(
                BiometricManager.Authenticators.BIOMETRIC_STRONG or
                        BiometricManager.Authenticators.DEVICE_CREDENTIAL
            )
            .build()
    }

    private fun maybeShowBiometricOnStart() {
        when (canUseBiometric()) {
            BiometricManager.BIOMETRIC_SUCCESS -> {
                startBiometricAuth()
            }
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE,
            BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE,
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED,
            BiometricManager.BIOMETRIC_STATUS_UNKNOWN -> {
                binding.btnUseBiometric.isEnabled = false
                showStatus("Biometric not available. Please use your password.")
            }
        }
    }

    private fun startBiometricAuth() {
        if (canUseBiometric() == BiometricManager.BIOMETRIC_SUCCESS) {
            biometricPrompt.authenticate(promptInfo)
        } else {
            showStatus("Biometric not available. Please use your password.")
        }
    }

    private fun canUseBiometric(): Int {
        val biometricManager = BiometricManager.from(this)
        return biometricManager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG or
                    BiometricManager.Authenticators.DEVICE_CREDENTIAL
        )
    }

    private fun validatePassword(password: String): Boolean {
        // Replace this with your real password or server-side check.
        return password == demoPassword
    }

    private fun onAuthenticationSuccess(from: String) {
        setAuthenticated()
        Toast.makeText(this, "Logged in with $from", Toast.LENGTH_SHORT).show()
        goToHome()
    }

    private fun goToHome() {
        val intent = Intent(this, HomeActivity::class.java)
        startActivity(intent)
        finish()
    }

    private fun showStatus(message: String) {
        binding.tvStatus.text = message
        binding.tvStatus.visibility = android.view.View.VISIBLE
    }

    fun logoutForDemo() {
        clearAuthenticated()
    }
}



// src/main/java/com/example/biometricauth/HomeActivity.kt
package com.example.biometricauth

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import com.example.biometricauth.databinding.ActivityHomeBinding

class HomeActivity : AppCompatActivity() {

    private lateinit var binding: ActivityHomeBinding

    private val sharedPrefsName = "auth_prefs"
    private val keyIsAuthenticated = "is_authenticated"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        binding = ActivityHomeBinding.inflate(layoutInflater)
        setContentView(binding.root)

        if (!isAuthenticated()) {
            navigateToLogin()
            return
        }

        binding.btnLogout.setOnClickListener {
            logout()
            navigateToLogin()
        }
    }

    private fun isAuthenticated(): Boolean {
        val prefs = getSharedPreferences(sharedPrefsName, Context.MODE_PRIVATE)
        return prefs.getBoolean(keyIsAuthenticated, false)
    }

    private fun logout() {
        val prefs = getSharedPreferences(sharedPrefsName, Context.MODE_PRIVATE)
        prefs.edit().putBoolean(keyIsAuthenticated, false).apply()
    }

    private fun navigateToLogin() {
        val intent = Intent(this, MainActivity::class.java)
        startActivity(intent)
        finish()
    }
}



// res/values/themes.xml
<?xml version="1.0" encoding="utf-8"?>
<resources xmlns:tools="http://schemas.android.com/tools">
    <style name="Theme.BiometricAuth" parent="Theme.MaterialComponents.DayNight.NoActionBar">
        <item name="colorPrimary">@color/purple_500</item>
        <item name="colorPrimaryVariant">@color/purple_700</item>
        <item name="colorOnPrimary">@android:color/white</item>
        <item name="android:navigationBarColor">@android:color/black</item>
        <item name="android:statusBarColor">@android:color/transparent</item>
    </style>
</resources>



// res/values/colors.xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="purple_500">#6200EE</color>
    <color name="purple_700">#3700B3</color>
</resources>