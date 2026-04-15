package com.example.users

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.example.users.banking.BankingActivity
import com.example.users.databinding.ActivityMainBinding
import com.example.users.network.ApiClient
import com.example.users.ui.UsersAdapter
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private val adapter = UsersAdapter()
    private var biometricPrompt: BiometricPrompt? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!SessionPrefs.isLoggedIn(this) || !SessionPrefs.isAuthenticated(this)) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.toolbar.title = getString(R.string.app_name)
        binding.toolbar.menu.clear()
        val bankingItem = binding.toolbar.menu.add(getString(R.string.banking))
        bankingItem.setShowAsAction(1)
        val biometricItem = binding.toolbar.menu.add(
            if (SessionPrefs.isBiometricEnabled(this)) {
                getString(R.string.disable_biometric_login)
            } else {
                getString(R.string.enable_biometric_login)
            },
        )
        biometricItem.setShowAsAction(1)
        val logoutItem = binding.toolbar.menu.add(getString(R.string.logout))
        logoutItem.setShowAsAction(1)
        binding.toolbar.setOnMenuItemClickListener {
            when (it.title?.toString()) {
                getString(R.string.banking) -> {
                    startActivity(Intent(this, BankingActivity::class.java))
                    true
                }
                getString(R.string.enable_biometric_login) -> {
                    enableBiometricLogin { enabled ->
                        if (enabled) {
                            biometricItem.title = getString(R.string.disable_biometric_login)
                        }
                    }
                    true
                }
                getString(R.string.disable_biometric_login) -> {
                    SessionPrefs.setBiometricEnabled(this, false)
                    biometricItem.title = getString(R.string.enable_biometric_login)
                    true
                }
                else -> {
                    SessionPrefs.clearAll(this)
                    startActivity(Intent(this, LoginActivity::class.java))
                    finish()
                    true
                }
            }
        }

        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = adapter

        binding.retryButton.setOnClickListener { loadUsers() }

        loadUsers()
    }

    override fun onResume() {
        super.onResume()
        if (!SessionPrefs.isLoggedIn(this) || !SessionPrefs.isAuthenticated(this)) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }

    private fun loadUsers() {
        showLoading()
        lifecycleScope.launch {
            try {
                val users = ApiClient.usersApi.listUsers()
                adapter.submit(users)
                showContent()
            } catch (_: Exception) {
                showError()
            }
        }
    }

    private fun enableBiometricLogin(onResult: (Boolean) -> Unit) {
        val manager = BiometricManager.from(this)
        val authenticators = BiometricManager.Authenticators.BIOMETRIC_STRONG
        when (manager.canAuthenticate(authenticators)) {
            BiometricManager.BIOMETRIC_SUCCESS -> {
                val executor = ContextCompat.getMainExecutor(this)
                biometricPrompt = BiometricPrompt(
                    this,
                    executor,
                    object : BiometricPrompt.AuthenticationCallback() {
                        override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                            super.onAuthenticationSucceeded(result)
                            SessionPrefs.setBiometricEnabled(this@MainActivity, true)
                            onResult(true)
                        }

                        override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                            super.onAuthenticationError(errorCode, errString)
                            onResult(false)
                        }

                        override fun onAuthenticationFailed() {
                            super.onAuthenticationFailed()
                        }
                    },
                )

                val promptInfo = BiometricPrompt.PromptInfo.Builder()
                    .setTitle(getString(R.string.enable_biometric_title))
                    .setSubtitle(getString(R.string.enable_biometric_subtitle))
                    .setNegativeButtonText(getString(R.string.cancel))
                    .setAllowedAuthenticators(authenticators)
                    .build()

                biometricPrompt?.authenticate(promptInfo)
            }
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> {
                MaterialAlertDialogBuilder(this)
                    .setTitle(getString(R.string.biometric_not_set_up_title))
                    .setMessage(getString(R.string.biometric_not_set_up_message))
                    .setPositiveButton(getString(R.string.ok), null)
                    .show()
                onResult(false)
            }
            else -> {
                MaterialAlertDialogBuilder(this)
                    .setTitle(getString(R.string.biometric_unavailable_title))
                    .setMessage(getString(R.string.biometric_unavailable_message))
                    .setPositiveButton(getString(R.string.ok), null)
                    .show()
                onResult(false)
            }
        }
    }

    private fun showLoading() {
        binding.recyclerView.visibility = View.GONE
        binding.stateContainer.visibility = View.VISIBLE
        binding.progress.visibility = View.VISIBLE
        binding.stateText.text = getString(R.string.loading)
        binding.retryButton.visibility = View.GONE
    }

    private fun showError() {
        binding.recyclerView.visibility = View.GONE
        binding.stateContainer.visibility = View.VISIBLE
        binding.progress.visibility = View.GONE
        binding.stateText.text = getString(R.string.error_loading)
        binding.retryButton.visibility = View.VISIBLE
    }

    private fun showContent() {
        binding.stateContainer.visibility = View.GONE
        binding.recyclerView.visibility = View.VISIBLE
    }
}

