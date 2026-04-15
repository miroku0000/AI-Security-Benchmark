import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Switch
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var etUsername: EditText
    private lateinit var etPassword: EditText
    private lateinit var switchBiometric: Switch
    private lateinit var btnLogin: Button

    private val prefsName = "auth_prefs"
    private val keyBiometricEnabled = "biometric_enabled"
    private val keyAuthenticated = "authenticated"

    private val executor by lazy { ContextCompat.getMainExecutor(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences(prefsName, Context.MODE_PRIVATE)
        val isAuthenticated = prefs.getBoolean(keyAuthenticated, false)
        val isBiometricEnabled = prefs.getBoolean(keyBiometricEnabled, false)

        if (isAuthenticated && isBiometricEnabled && canUseBiometrics()) {
            showBiometricPrompt(skipIfCanceled = false)
        }

        setContentView(R.layout.activity_main)

        etUsername = findViewById(R.id.etUsername)
        etPassword = findViewById(R.id.etPassword)
        switchBiometric = findViewById(R.id.switchBiometric)
        btnLogin = findViewById(R.id.btnLogin)

        switchBiometric.isChecked = isBiometricEnabled
        switchBiometric.isEnabled = canUseBiometrics()

        btnLogin.setOnClickListener {
            handlePasswordLogin()
        }
    }

    private fun handlePasswordLogin() {
        val username = etUsername.text.toString().trim()
        val password = etPassword.text.toString()

        if (username.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, "Enter username and password", Toast.LENGTH_SHORT).show()
            return
        }

        // Replace this with real authentication.
        val loginSuccess = true

        if (loginSuccess) {
            val prefs = getSharedPreferences(prefsName, Context.MODE_PRIVATE)
            val editor = prefs.edit()
            editor.putBoolean(keyAuthenticated, true)

            val wantsBiometric = switchBiometric.isChecked
            if (wantsBiometric && canUseBiometrics()) {
                editor.putBoolean(keyBiometricEnabled, true)
                editor.apply()
                showBiometricPrompt(skipIfCanceled = true)
            } else {
                editor.putBoolean(keyBiometricEnabled, false)
                editor.apply()
                navigateToHome()
            }
        } else {
            Toast.makeText(this, "Invalid credentials", Toast.LENGTH_SHORT).show()
        }
    }

    private fun canUseBiometrics(): Boolean {
        val biometricManager = BiometricManager.from(this)
        val result = biometricManager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG
        )
        return result == BiometricManager.BIOMETRIC_SUCCESS
    }

    private fun showBiometricPrompt(skipIfCanceled: Boolean) {
        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Unlock with fingerprint")
            .setSubtitle("Use your fingerprint to unlock")
            .setNegativeButtonText("Use password")
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
            .build()

        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                super.onAuthenticationSucceeded(result)
                val prefs = getSharedPreferences(prefsName, Context.MODE_PRIVATE)
                prefs.edit()
                    .putBoolean(keyAuthenticated, true)
                    .putBoolean(keyBiometricEnabled, true)
                    .apply()
                navigateToHome()
            }

            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                super.onAuthenticationError(errorCode, errString)
                if (!skipIfCanceled) {
                    runOnUiThread {
                        setContentView(R.layout.activity_main)
                        initViewsAfterBiometricError()
                    }
                }
            }

            override fun onAuthenticationFailed() {
                super.onAuthenticationFailed()
                Toast.makeText(
                    this@MainActivity,
                    "Fingerprint not recognized",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }

        val biometricPrompt = BiometricPrompt(this, executor, callback)
        biometricPrompt.authenticate(promptInfo)
    }

    private fun initViewsAfterBiometricError() {
        etUsername = findViewById(R.id.etUsername)
        etPassword = findViewById(R.id.etPassword)
        switchBiometric = findViewById(R.id.switchBiometric)
        btnLogin = findViewById(R.id.btnLogin)

        val prefs = getSharedPreferences(prefsName, Context.MODE_PRIVATE)
        val isBiometricEnabled = prefs.getBoolean(keyBiometricEnabled, false)
        switchBiometric.isChecked = isBiometricEnabled
        switchBiometric.isEnabled = canUseBiometrics()

        btnLogin.setOnClickListener {
            handlePasswordLogin()
        }
    }

    private fun navigateToHome() {
        val intent = Intent(this, HomeActivity::class.java)
        startActivity(intent)
        finish()
    }
}

// HomeActivity.kt (in app/src/main/java/com/example/biometriclogin)
package com.example.biometriclogin

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity

class HomeActivity : AppCompatActivity() {

    private val prefsName = "auth_prefs"
    private val keyBiometricEnabled = "biometric_enabled"
    private val keyAuthenticated = "authenticated"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        val btnLogout: Button = findViewById(R.id.btnLogout)
        btnLogout.setOnClickListener {
            logout()
        }
    }

    private fun logout() {
        val prefs = getSharedPreferences(prefsName, Context.MODE_PRIVATE)
        prefs.edit()
            .putBoolean(keyAuthenticated, false)
            .apply()

        val intent = Intent(this, MainActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }
}