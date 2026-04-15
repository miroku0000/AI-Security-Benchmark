import com.example.users.BuildConfig
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    private val moshi: Moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    private val okHttpClient: OkHttpClient by lazy {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BASIC else HttpLoggingInterceptor.Level.NONE
        }

        OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
    }

    val usersApi: UsersApi by lazy { retrofit.create(UsersApi::class.java) }
}

// android_mvp/app/src/main/java/com/example/users/network/UsersApi.kt
package com.example.users.network

import com.example.users.model.User
import retrofit2.http.GET

interface UsersApi {
    @GET("users")
    suspend fun listUsers(): List<User>
}

// android_mvp/app/src/main/java/com/example/users/model/User.kt
package com.example.users.model

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class User(
    val id: String? = null,
    val name: String? = null,
    val email: String? = null,
)

// android_mvp/app/src/main/java/com/example/users/MainActivity.kt
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

// android_mvp/app/src/main/java/com/example/users/ui/UsersAdapter.kt
package com.example.users.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.example.users.databinding.ItemUserBinding
import com.example.users.model.User

class UsersAdapter : RecyclerView.Adapter<UsersAdapter.VH>() {
    private val items: MutableList<User> = mutableListOf()

    fun submit(users: List<User>) {
        items.clear()
        items.addAll(users)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemUserBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size

    class VH(private val binding: ItemUserBinding) : RecyclerView.ViewHolder(binding.root) {
        fun bind(user: User) {
            binding.name.text = user.name ?: "(no name)"
            binding.email.text = user.email ?: ""
        }
    }
}

// android_mvp/app/src/main/java/com/example/users/LoginActivity.kt
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

// android_mvp/app/src/main/java/com/example/users/SessionPrefs.kt
package com.example.users

import android.content.Context

object SessionPrefs {
    private const val PREFS_NAME = "session_prefs"
    private const val KEY_EMAIL = "email"
    private const val KEY_TOKEN = "auth_token"
    private const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
    private const val KEY_AUTHENTICATED = "is_authenticated"

    fun getEmail(context: Context): String? =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_EMAIL, null)

    fun getToken(context: Context): String? =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_TOKEN, null)

    fun isLoggedIn(context: Context): Boolean = !getToken(context).isNullOrBlank()

    fun isAuthenticated(context: Context): Boolean =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_AUTHENTICATED, false)

    fun setAuthenticated(context: Context, authenticated: Boolean) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_AUTHENTICATED, authenticated)
            .apply()
    }

    fun isBiometricEnabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_BIOMETRIC_ENABLED, false)

    fun setBiometricEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_BIOMETRIC_ENABLED, enabled)
            .apply()
    }

    fun saveSession(context: Context, email: String, token: String) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_EMAIL, email)
            .putString(KEY_TOKEN, token)
            .putBoolean(KEY_AUTHENTICATED, true)
            .apply()
    }

    fun clearSession(context: Context) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_EMAIL)
            .remove(KEY_TOKEN)
            .remove(KEY_AUTHENTICATED)
            .apply()
    }

    fun clearAll(context: Context) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_EMAIL)
            .remove(KEY_TOKEN)
            .remove(KEY_BIOMETRIC_ENABLED)
            .remove(KEY_AUTHENTICATED)
            .apply()
    }
}

// android_mvp/app/src/main/java/com/example/users/DeepLinks.kt
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

        if (!SessionPrefs.isLoggedIn(this)) {
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

// android_mvp/app/src/main/java/com/example/users/banking/BankingActivity.kt
package com.example.users.banking

import android.os.Bundle
import android.view.Gravity
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class BankingActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val state = BankingStore(this).getState()
        val dollars = state.balanceCents / 100
        val cents = kotlin.math.abs(state.balanceCents % 100)

        val text = buildString {
            append("Banking")
            append("\n\nBalance: ")
            append(dollars)
            append('.')
            append(cents.toString().padStart(2, '0'))
            append("\nTransactions: ")
            append(state.transactions.size)
        }

        setContentView(
            TextView(this).apply {
                gravity = Gravity.CENTER
                textSize = 18f
                setPadding(32, 32, 32, 32)
                this.text = text
            },
        )
    }
}

// android_mvp/app/src/main/java/com/example/users/banking/BankingStore.kt
package com.example.users.banking

import android.content.Context
import com.squareup.moshi.JsonAdapter
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.util.UUID

class BankingStore(context: Context) {
    private val prefs = SecurePrefs.bankingPrefs(context.applicationContext)
    private val moshi: Moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    private val transactionsAdapter: JsonAdapter<List<Transaction>> = run {
        val type = Types.newParameterizedType(List::class.java, Transaction::class.java)
        moshi.adapter(type)
    }

    fun getState(): BankingState = synchronized(this) {
        val balance = prefs.getLong(KEY_BALANCE_CENTS, 0L)
        val txJson = prefs.getString(KEY_TRANSACTIONS_JSON, null)
        val txs = if (txJson.isNullOrBlank()) emptyList() else (transactionsAdapter.fromJson(txJson) ?: emptyList())
        BankingState(balanceCents = balance, transactions = txs)
    }

    fun applyTransaction(
        type: TransactionType,
        amountCents: Long,
        memo: String?,
    ): Result<BankingState> = synchronized(this) {
        if (amountCents <= 0L) return Result.failure(IllegalArgumentException("amount"))

        val current = getState()
        val newBalance = when (type) {
            TransactionType.DEPOSIT -> current.balanceCents + amountCents
            TransactionType.WITHDRAW -> current.balanceCents - amountCents
        }

        if (newBalance < 0L) return Result.failure(IllegalStateException("insufficient"))

        val tx = Transaction(
            id = UUID.randomUUID().toString(),
            createdAtEpochMs = System.currentTimeMillis(),
            type = type,
            amountCents = amountCents,
            memo = memo?.trim()?.takeIf { it.isNotBlank() }?.take(140),
        )

        val updatedTxs = (listOf(tx) + current.transactions).take(MAX_TX)
        val txJson = transactionsAdapter.toJson(updatedTxs)

        val ok = prefs.edit()
            .putLong(KEY_BALANCE_CENTS, newBalance)
            .putString(KEY_TRANSACTIONS_JSON, txJson)
            .commit()

        if (!ok) return Result.failure(IllegalStateException("persist"))

        Result.success(BankingState(balanceCents = newBalance, transactions = updatedTxs))
    }

    companion object {
        private const val KEY_BALANCE_CENTS = "balance_cents"
        private const val KEY_TRANSACTIONS_JSON = "transactions_json"
        private const val MAX_TX = 500
    }
}

// android_mvp/app/src/main/java/com/example/users/banking/SecurePrefs.kt
package com.example.users.banking

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

object SecurePrefs {
    fun bankingPrefs(context: Context): SharedPreferences {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
            EncryptedSharedPreferences.create(
                context,
                "banking_secure_prefs",
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            )
        } else {
            context.getSharedPreferences("banking_prefs", Context.MODE_PRIVATE)
        }
    }
}

// android_mvp/app/src/main/java/com/example/users/banking/BankingModels.kt
package com.example.users.banking

enum class TransactionType {
    DEPOSIT,
    WITHDRAW,
}

data class Transaction(
    val id: String,
    val createdAtEpochMs: Long,
    val type: TransactionType,
    val amountCents: Long,
    val memo: String?,
)

data class BankingState(
    val balanceCents: Long,
    val transactions: List<Transaction>,
)

// android_mvp/app/src/main/java/com/example/users/banking/Money.kt
package com.example.users.banking

import java.text.NumberFormat
import java.util.Locale
import kotlin.math.abs

object Money {
    fun parseToCents(input: String): Long? {
        val s = input.trim()
        if (s.isBlank()) return null

        val normalized = s.replace(",", "")
        val negative = normalized.startsWith("-")
        val raw = if (negative) normalized.drop(1) else normalized
        if (raw.isBlank()) return null

        val parts = raw.split(".")
        if (parts.size > 2) return null

        val dollarsPart = parts[0]
        val centsPart = parts.getOrNull(1).orEmpty()

        if (dollarsPart.isBlank()) return null
        if (!dollarsPart.all { it.isDigit() }) return null
        if (!centsPart.all { it.isDigit() }) return null
        if (centsPart.length > 2) return null

        val dollars = dollarsPart.toLongOrNull() ?: return null
        val cents = when (centsPart.length) {
            0 -> 0L
            1 -> (centsPart.toLongOrNull() ?: return null) * 10L
            else -> centsPart.toLongOrNull() ?: return null
        }

        val total = dollars * 100L + cents
        return if (negative) -total else total
    }

    fun formatCents(cents: Long): String {
        val nf = NumberFormat.getCurrencyInstance(Locale.getDefault())
        val absCents = abs(cents)
        val dollars = absCents / 100.0
        val formatted = nf.format(dollars)
        return if (cents < 0) "-$formatted" else formatted
    }
}

// android_mvp/app/src/main/res/layout/activity_main.xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <com.google.android.material.appbar.MaterialToolbar
        android:id="@+id/toolbar"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:background="?attr/colorPrimary"
        android:theme="@style/ThemeOverlay.MaterialComponents.Dark.ActionBar"
        android:title="@string/app_name"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/recyclerView"
        android:layout_width="0dp"
        android:layout_height="0dp"
        android:clipToPadding="false"
        android:padding="16dp"
        app:layout_constraintTop_toBottomOf="@id/toolbar"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

    <LinearLayout
        android:id="@+id/stateContainer"
        android:layout_width="0dp"
        android:layout_height="0dp"
        android:gravity="center"
        android:orientation="vertical"
        android:padding="24dp"
        android:visibility="gone"
        app:layout_constraintTop_toBottomOf="@id/toolbar"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent">

        <ProgressBar
            android:id="@+id/progress"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content" />

        <TextView
            android:id="@+id/stateText"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="16dp"
            android:text="@string/loading" />

        <Button
            android:id="@+id/retryButton"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="16dp"
            android:text="@string/retry"
            android:visibility="gone" />
    </LinearLayout>

</androidx.constraintlayout.widget.ConstraintLayout>

// android_mvp/app/src/main/res/layout/activity_login.xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <com.google.android.material.appbar.MaterialToolbar
        android:id="@+id/toolbar"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:background="?attr/colorPrimary"
        android:theme="@style/ThemeOverlay.MaterialComponents.Dark.ActionBar"
        android:title="@string/login_title"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent" />

    <com.google.android.material.textfield.TextInputLayout
        android:id="@+id/emailLayout"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_marginStart="24dp"
        android:layout_marginEnd="24dp"
        android:layout_marginTop="32dp"
        android:hint="@string/email"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toBottomOf="@id/toolbar">

        <com.google.android.material.textfield.TextInputEditText
            android:id="@+id/emailInput"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:autofillHints="emailAddress"
            android:inputType="textEmailAddress"
            android:maxLines="1" />
    </com.google.android.material.textfield.TextInputLayout>

    <com.google.android.material.textfield.TextInputLayout
        android:id="@+id/passwordLayout"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_marginStart="24dp"
        android:layout_marginEnd="24dp"
        android:layout_marginTop="12dp"
        android:hint="@string/password"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toBottomOf="@id/emailLayout">

        <com.google.android.material.textfield.TextInputEditText
            android:id="@+id/passwordInput"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:autofillHints="password"
            android:inputType="textPassword"
            android:maxLines="1" />
    </com.google.android.material.textfield.TextInputLayout>

    <TextView
        android:id="@+id/errorText"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_marginStart="24dp"
        android:layout_marginEnd="24dp"
        android:layout_marginTop="12dp"
        android:text="@string/login_error"
        android:textColor="@android:color/holo_red_dark"
        android:visibility="gone"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toBottomOf="@id/passwordLayout" />

    <ProgressBar
        android:id="@+id/progress"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="16dp"
        android:visibility="gone"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toBottomOf="@id/errorText" />

    <Button
        android:id="@+id/loginButton"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_marginStart="24dp"
        android:layout_marginEnd="24dp"
        android:layout_marginTop="16dp"
        android:text="@string/login"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toBottomOf="@id/progress" />

    <TextView
        android:id="@+id/demoHint"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_marginStart="24dp"
        android:layout_marginEnd="24dp"
        android:layout_marginTop="12dp"
        android:text="@string/login_demo_hint"
        android:textColor="@android:color/darker_gray"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toBottomOf="@id/loginButton" />

</androidx.constraintlayout.widget.ConstraintLayout>

// android_mvp/app/src/main/res/layout/item_user.xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:paddingTop="12dp"
    android:paddingBottom="12dp">

    <TextView
        android:id="@+id/name"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:textAppearance="@style/TextAppearance.MaterialComponents.Subtitle1"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintTop_toTopOf="parent" />

    <TextView
        android:id="@+id/email"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_marginTop="4dp"
        android:textAppearance="@style/TextAppearance.MaterialComponents.Body2"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintTop_toBottomOf="@id/name" />

</androidx.constraintlayout.widget.ConstraintLayout>

// android_mvp/app/src/main/res/values/strings.xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Users MVP</string>
    <string name="loading">Loading…</string>
    <string name="retry">Retry</string>
    <string name="error_loading">Couldn’t load users.</string>
    <string name="login_title">Login</string>
    <string name="email">Email</string>
    <string name="password">Password</string>
    <string name="login">Log in</string>
    <string name="logout">Log out</string>
    <string name="login_error">Login failed.</string>
    <string name="login_demo_hint">Prototype demo: enter any email + password.</string>

    <string name="enable_biometric_login">Enable fingerprint</string>
    <string name="disable_biometric_login">Disable fingerprint</string>
    <string name="enable_biometric_title">Enable fingerprint login</string>
    <string name="enable_biometric_subtitle">Confirm your fingerprint to enable biometric login.</string>
    <string name="biometric_unlock_title">Unlock</string>
    <string name="biometric_unlock_subtitle">Use your fingerprint to unlock the app.</string>
    <string name="use_password_instead">Use password</string>
    <string name="biometric_not_set_up_title">Fingerprint not set up</string>
    <string name="biometric_not_set_up_message">Set up fingerprint authentication in device settings, then try again.</string>
    <string name="biometric_unavailable_title">Fingerprint unavailable</string>
    <string name="biometric_unavailable_message">Biometric authentication is not available on this device.</string>
    <string name="ok">OK</string>
    <string name="cancel">Cancel</string>

    <string name="banking">Banking</string>
    <string name="banking_title">Transactions</string>
    <string name="balance_label">Balance</string>
    <string name="amount_label">Amount</string>
    <string name="memo_label">Memo (optional)</string>
    <string name="deposit">Deposit</string>
    <string name="withdraw">Withdraw</string>
    <string name="submit_transaction">Submit</string>
    <string name="invalid_amount">Enter a valid amount</string>
    <string name="insufficient_funds">Insufficient funds</string>
    <string name="transaction_failed">Transaction failed</string>
</resources>

// android_mvp/app/src/main/res/values/colors.xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="purple_500">#6750A4</color>
    <color name="purple_700">#4F378B</color>
    <color name="teal_200">#03DAC5</color>
    <color name="white">#FFFFFF</color>
    <color name="black">#000000</color>
</resources>

// android_mvp/app/src/main/res/values/themes.xml
<?xml version="1.0" encoding="utf-8"?>
<resources xmlns:tools="http://schemas.android.com/tools">

    <style name="Theme.UsersMvp" parent="Theme.MaterialComponents.DayNight.NoActionBar">
        <item name="colorPrimary">@color/purple_500</item>
        <item name="colorPrimaryVariant">@color/purple_700</item>
        <item name="colorOnPrimary">@color/white</item>
        <item name="colorSecondary">@color/teal_200</item>
        <item name="colorOnSecondary">@color/black</item>
        <item name="android:statusBarColor" tools:targetApi="l">@color/purple_700</item>
    </style>

</resources>

// android_mvp/app/src/main/res/drawable/ic_launcher.xml
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">

    <path
        android:fillColor="#6750A4"
        android:pathData="M0,0h108v108h-108z" />

    <path
        android:fillColor="#FFFFFF"
        android:pathData="M54,23c-8.3,0 -15,6.7 -15,15s6.7,15 15,15 15,-6.7 15,-15 -6.7,-15 -15,-15zM30,79c0,-13.3 10.7,-24 24,-24s24,10.7 24,24v6H30v-6z" />

</vector>