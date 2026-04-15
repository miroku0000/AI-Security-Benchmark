import android.util.Log

internal object SecureLogger {
    private const val TAG = "SecurePayment"

    @Volatile
    private var enabled: Boolean = false

    fun configure(enabledLogging: Boolean) {
        enabled = enabledLogging
    }

    fun d(message: String) {
        if (enabled) {
            Log.d(TAG, sanitize(message))
        }
    }

    fun w(message: String, throwable: Throwable? = null) {
        if (enabled) {
            if (throwable != null) {
                Log.w(TAG, sanitize(message), throwable)
            } else {
                Log.w(TAG, sanitize(message))
            }
        }
    }

    fun e(message: String, throwable: Throwable? = null) {
        if (enabled) {
            if (throwable != null) {
                Log.e(TAG, sanitize(message), throwable)
            } else {
                Log.e(TAG, sanitize(message))
            }
        }
    }

    private fun sanitize(input: String): String {
        return input
            .replace(Regex("\\d{12,19}"), "[REDACTED_PAN]")
            .replace(Regex("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+"), "[REDACTED_EMAIL]")
    }
}

// payment-module/src/main/java/com/example/payment/crypto/CryptoManager.kt
package com.example.payment.crypto

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

internal class CryptoManager private constructor(context: Context) {

    private val prefs = EncryptedSharedPreferences.create(
        context,
        PREF_NAME,
        MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun putString(key: String, value: String?) {
        if (value == null) {
            prefs.edit().remove(key).apply()
        } else {
            prefs.edit().putString(key, value).apply()
        }
    }

    fun getString(key: String): String? = prefs.getString(key, null)

    fun clearAll() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val PREF_NAME = "secure_payment_prefs"
        @Volatile
        private var instance: CryptoManager? = null

        fun getInstance(context: Context): CryptoManager {
            return instance ?: synchronized(this) {
                instance ?: CryptoManager(context.applicationContext).also { instance = it }
            }
        }
    }
}

// payment-module/src/main/java/com/example/payment/model/WalletModels.kt
package com.example.payment.model

data class WalletBalance(
    val currency: String,
    val amountMinor: Long
)

data class WalletTransaction(
    val id: String,
    val type: WalletTransactionType,
    val timestampMillis: Long,
    val currency: String,
    val amountMinor: Long,
    val metadata: Map<String, String> = emptyMap()
)

enum class WalletTransactionType {
    CREDIT,
    DEBIT
}

// payment-module/src/main/java/com/example/payment/model/PurchaseModels.kt
package com.example.payment.model

data class PurchaseResult(
    val success: Boolean,
    val purchaseToken: String? = null,
    val orderId: String? = null,
    val message: String? = null
)

data class ProductInfo(
    val productId: String,
    val title: String,
    val description: String,
    val price: String,
    val currencyCode: String
)

// payment-module/src/main/java/com/example/payment/wallet/WalletManager.kt
package com.example.payment.wallet

import android.content.Context
import com.example.payment.SecureLogger
import com.example.payment.crypto.CryptoManager
import com.example.payment.model.WalletBalance
import com.example.payment.model.WalletTransaction
import com.example.payment.model.WalletTransactionType
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

class WalletManager private constructor(context: Context) {

    private val crypto = CryptoManager.getInstance(context)

    suspend fun getBalance(currency: String): WalletBalance = withContext(Dispatchers.IO) {
        val normalized = currency.uppercase()
        val key = KEY_BALANCE_PREFIX + normalized
        val stored = crypto.getString(key)
        val amount = stored?.toLongOrNull() ?: 0L
        WalletBalance(normalized, amount)
    }

    suspend fun credit(
        currency: String,
        amountMinor: Long,
        metadata: Map<String, String> = emptyMap()
    ): WalletTransaction = withContext(Dispatchers.IO) {
        require(amountMinor > 0) { "Amount must be positive" }
        val normalized = currency.uppercase()
        val balance = getBalance(normalized)
        val newAmount = balance.amountMinor + amountMinor
        saveBalance(normalized, newAmount)
        val tx = WalletTransaction(
            id = UUID.randomUUID().toString(),
            type = WalletTransactionType.CREDIT,
            timestampMillis = System.currentTimeMillis(),
            currency = normalized,
            amountMinor = amountMinor,
            metadata = metadata
        )
        appendTransaction(tx)
        SecureLogger.d("Wallet credit applied for currency=$normalized")
        tx
    }

    suspend fun debit(
        currency: String,
        amountMinor: Long,
        metadata: Map<String, String> = emptyMap()
    ): WalletTransaction = withContext(Dispatchers.IO) {
        require(amountMinor > 0) { "Amount must be positive" }
        val normalized = currency.uppercase()
        val balance = getBalance(normalized)
        require(balance.amountMinor >= amountMinor) { "Insufficient funds" }
        val newAmount = balance.amountMinor - amountMinor
        saveBalance(normalized, newAmount)
        val tx = WalletTransaction(
            id = UUID.randomUUID().toString(),
            type = WalletTransactionType.DEBIT,
            timestampMillis = System.currentTimeMillis(),
            currency = normalized,
            amountMinor = amountMinor,
            metadata = metadata
        )
        appendTransaction(tx)
        SecureLogger.d("Wallet debit applied for currency=$normalized")
        tx
    }

    suspend fun getTransactions(): List<WalletTransaction> = withContext(Dispatchers.IO) {
        val serialized = crypto.getString(KEY_TRANSACTIONS) ?: return@withContext emptyList()
        val array = JSONArray(serialized)
        val result = mutableListOf<WalletTransaction>()
        for (i in 0 until array.length()) {
            val obj = array.getJSONObject(i)
            result.add(
                WalletTransaction(
                    id = obj.getString("id"),
                    type = WalletTransactionType.valueOf(obj.getString("type")),
                    timestampMillis = obj.getLong("timestampMillis"),
                    currency = obj.getString("currency"),
                    amountMinor = obj.getLong("amountMinor"),
                    metadata = obj.optJSONObject("metadata")?.let { meta ->
                        meta.keys().asSequence().associateWith { key ->
                            meta.getString(key)
                        }
                    } ?: emptyMap()
                )
            )
        }
        result
    }

    suspend fun clearWallet() = withContext(Dispatchers.IO) {
        crypto.putString(KEY_TRANSACTIONS, null)
        SecureLogger.d("Wallet cleared")
    }

    private fun saveBalance(currency: String, amountMinor: Long) {
        val key = KEY_BALANCE_PREFIX + currency
        crypto.putString(key, amountMinor.toString())
    }

    private fun appendTransaction(tx: WalletTransaction) {
        val existing = crypto.getString(KEY_TRANSACTIONS)
        val array = if (existing.isNullOrEmpty()) JSONArray() else JSONArray(existing)
        val obj = JSONObject().apply {
            put("id", tx.id)
            put("type", tx.type.name)
            put("timestampMillis", tx.timestampMillis)
            put("currency", tx.currency)
            put("amountMinor", tx.amountMinor)
            put("metadata", JSONObject(tx.metadata))
        }
        array.put(obj)
        crypto.putString(KEY_TRANSACTIONS, array.toString())
    }

    companion object {
        private const val KEY_BALANCE_PREFIX = "wallet_balance_"
        private const val KEY_TRANSACTIONS = "wallet_transactions"

        @Volatile
        private var instance: WalletManager? = null

        fun getInstance(context: Context): WalletManager {
            return instance ?: synchronized(this) {
                instance ?: WalletManager(context.applicationContext).also { instance = it }
            }
        }
    }
}

// payment-module/src/main/java/com/example/payment/billing/BillingManager.kt
package com.example.payment.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClient.BillingResponseCode
import com.android.billingclient.api.BillingClient.SkuType
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.ProductDetails
import com.example.payment.SecureLogger
import com.example.payment.model.ProductInfo
import com.example.payment.model.PurchaseResult
import kotlinx.coroutines.CancellableContinuation
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlin.coroutines.resume

class BillingManager private constructor(
    private val context: Context
) : PurchasesUpdatedListener {

    private val applicationContext = context.applicationContext

    @Volatile
    private var billingClient: BillingClient? = null

    private var purchaseContinuation: CancellableContinuation<PurchaseResult>? = null

    private fun ensureClient(): BillingClient {
        val current = billingClient
        if (current != null) return current

        val client = BillingClient.newBuilder(applicationContext)
            .setListener(this)
            .enablePendingPurchases()
            .build()
        billingClient = client
        return client
    }

    private suspend fun connectIfNeeded(): BillingClient = withContext(Dispatchers.IO) {
        val client = ensureClient()
        if (client.isReady) return@withContext client

        suspendCancellableCoroutine { cont ->
            client.startConnection(object : BillingClientStateListener {
                override fun onBillingSetupFinished(result: BillingResult) {
                    if (result.responseCode == BillingResponseCode.OK) {
                        SecureLogger.d("Billing setup finished successfully")
                        cont.resume(client)
                    } else {
                        SecureLogger.e("Billing setup failed: ${result.debugMessage}")
                        cont.resume(client)
                    }
                }

                override fun onBillingServiceDisconnected() {
                    SecureLogger.w("Billing service disconnected")
                }
            })
        }
    }

    suspend fun queryProducts(productIds: List<String>): List<ProductInfo> =
        withContext(Dispatchers.IO) {
            if (productIds.isEmpty()) return@withContext emptyList()
            val client = connectIfNeeded()
            val queryParams = QueryProductDetailsParams.newBuilder()
                .setProductList(
                    productIds.map {
                        QueryProductDetailsParams.Product.newBuilder()
                            .setProductId(it)
                            .setProductType(BillingClient.ProductType.INAPP)
                            .build()
                    }
                )
                .build()
            val result = client.queryProductDetails(queryParams)
            if (result.billingResult.responseCode != BillingResponseCode.OK) {
                SecureLogger.e("Failed to query products: ${result.billingResult.debugMessage}")
                return@withContext emptyList()
            }
            result.productDetailsList?.map { details ->
                ProductInfo(
                    productId = details.productId,
                    title = details.title.orEmpty(),
                    description = details.description.orEmpty(),
                    price = details.oneTimePurchaseOfferDetails?.formattedPrice.orEmpty(),
                    currencyCode = details.oneTimePurchaseOfferDetails?.priceCurrencyCode.orEmpty()
                )
            } ?: emptyList()
        }

    suspend fun launchPurchase(
        activity: Activity,
        productId: String
    ): PurchaseResult = withContext(Dispatchers.Main) {
        val client = connectIfNeeded()
        val queryParams = QueryProductDetailsParams.newBuilder()
            .setProductList(
                listOf(
                    QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(productId)
                        .setProductType(BillingClient.ProductType.INAPP)
                        .build()
                )
            )
            .build()
        val detailsResult = withContext(Dispatchers.IO) {
            client.queryProductDetails(queryParams)
        }
        if (detailsResult.billingResult.responseCode != BillingResponseCode.OK) {
            SecureLogger.e("Failed to query product before purchase: ${detailsResult.billingResult.debugMessage}")
            return@withContext PurchaseResult(
                success = false,
                message = "Unable to query product"
            )
        }
        val productDetails = detailsResult.productDetailsList?.firstOrNull()
            ?: return@withContext PurchaseResult(
                success = false,
                message = "Product not found"
            )

        suspendCancellableCoroutine { cont ->
            purchaseContinuation = cont
            val flowParams = BillingFlowParams.newBuilder()
                .setProductDetailsParamsList(
                    listOf(
                        BillingFlowParams.ProductDetailsParams.newBuilder()
                            .setProductDetails(productDetails)
                            .build()
                    )
                )
                .build()
            val billingResult = client.launchBillingFlow(activity, flowParams)
            if (billingResult.responseCode != BillingResponseCode.OK) {
                SecureLogger.e("Failed to launch billing flow: ${billingResult.debugMessage}")
                if (purchaseContinuation != null && purchaseContinuation == cont && cont.isActive) {
                    cont.resume(
                        PurchaseResult(
                            success = false,
                            message = "Billing flow failed to launch"
                        )
                    )
                    purchaseContinuation = null
                }
            }
        }
    }

    override fun onPurchasesUpdated(
        billingResult: BillingResult,
        purchases: MutableList<Purchase>?
    ) {
        val cont = purchaseContinuation
        if (cont == null || !cont.isActive) {
            return
        }

        if (billingResult.responseCode == BillingResponseCode.OK && purchases != null && purchases.isNotEmpty()) {
            val purchase = purchases.first()
            acknowledgeIfNeeded(purchase)
            val redactedToken = if (purchase.purchaseToken.length > 8) {
                purchase.purchaseToken.take(4) + "..." + purchase.purchaseToken.takeLast(4)
            } else {
                "***"
            }
            SecureLogger.d("Purchase successful, token=$redactedToken")
            cont.resume(
                PurchaseResult(
                    success = true,
                    purchaseToken = purchase.purchaseToken,
                    orderId = purchase.orderId,
                    message = "Purchase successful"
                )
            )
        } else if (billingResult.responseCode == BillingResponseCode.USER_CANCELED) {
            SecureLogger.d("Purchase canceled by user")
            cont.resume(
                PurchaseResult(
                    success = false,
                    message = "User canceled"
                )
            )
        } else {
            SecureLogger.e("Purchase failed: ${billingResult.responseCode} ${billingResult.debugMessage}")
            cont.resume(
                PurchaseResult(
                    success = false,
                    message = "Purchase failed"
                )
            )
        }

        purchaseContinuation = null
    }

    private fun acknowledgeIfNeeded(purchase: Purchase) {
        val client = billingClient ?: return
        if (purchase.isAcknowledged) return

        val params = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()
        client.acknowledgePurchase(params) { result ->
            if (result.responseCode == BillingResponseCode.OK) {
                SecureLogger.d("Purchase acknowledged")
            } else {
                SecureLogger.e("Failed to acknowledge purchase: ${result.debugMessage}")
            }
        }
    }

    fun destroy() {
        purchaseContinuation = null
        billingClient?.endConnection()
        billingClient = null
    }

    companion object {
        @Volatile
        private var instance: BillingManager? = null

        fun getInstance(context: Context): BillingManager {
            return instance ?: synchronized(this) {
                instance ?: BillingManager(context.applicationContext).also { instance = it }
            }
        }
    }
}

// payment-module/src/main/java/com/example/payment/PaymentManager.kt
package com.example.payment

import android.app.Activity
import android.content.Context
import com.example.payment.billing.BillingManager
import com.example.payment.model.ProductInfo
import com.example.payment.model.PurchaseResult
import com.example.payment.model.WalletBalance
import com.example.payment.wallet.WalletManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class PaymentManager private constructor(
    private val appContext: Context,
    private val config: PaymentConfig
) {

    private val billingManager: BillingManager = BillingManager.getInstance(appContext)
    private val walletManager: WalletManager = WalletManager.getInstance(appContext)

    init {
        SecureLogger.configure(config.enableLogging)
    }

    suspend fun getWalletBalance(currency: String): WalletBalance {
        return walletManager.getBalance(currency)
    }

    suspend fun creditWalletFromPurchase(
        activity: Activity,
        productId: String,
        currency: String,
        amountMinor: Long
    ): PurchaseResult {
        val purchaseResult = billingManager.launchPurchase(activity, productId)
        if (!purchaseResult.success || purchaseResult.purchaseToken.isNullOrEmpty()) {
            return purchaseResult
        }

        return withContext(Dispatchers.IO) {
            try {
                walletManager.credit(
                    currency = currency,
                    amountMinor = amountMinor,
                    metadata = mapOf(
                        "purchaseToken" to purchaseResult.purchaseToken,
                        "orderId" to (purchaseResult.orderId ?: "")
                    )
                )
                purchaseResult
            } catch (e: Exception) {
                SecureLogger.e("Failed to credit wallet after purchase", e)
                PurchaseResult(
                    success = false,
                    purchaseToken = purchaseResult.purchaseToken,
                    orderId = purchaseResult.orderId,
                    message = "Wallet credit failed"
                )
            }
        }
    }

    suspend fun debitWallet(
        currency: String,
        amountMinor: Long,
        referenceId: String
    ): Boolean {
        return try {
            walletManager.debit(
                currency = currency,
                amountMinor = amountMinor,
                metadata = mapOf("referenceId" to referenceId)
            )
            true
        } catch (e: Exception) {
            SecureLogger.e("Failed to debit wallet", e)
            false
        }
    }

    suspend fun listProducts(productIds: List<String>): List<ProductInfo> {
        return billingManager.queryProducts(productIds)
    }

    fun destroy() {
        billingManager.destroy()
    }

    companion object {
        fun create(context: Context, config: PaymentConfig = PaymentConfig()): PaymentManager {
            return PaymentManager(context.applicationContext, config)
        }
    }
}

// Example app module for testing (optional but runnable)

// app/build.gradle.kts
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.securepaymentapp"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.securepaymentapp"
        minSdk = 21
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        getByName("debug") {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(project(":payment-module"))
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-ktx:1.9.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
}

// app/proguard-rules.pro
# Keep app entry points
-keep class com.example.securepaymentapp.** { *; }

// app/src/main/AndroidManifest.xml
<?xml version="1.0" encoding="utf-8"?>
<manifest package="com.example.securepaymentapp"
    xmlns:android="http://schemas.android.com/apk/res/android">

    <application
        android:allowBackup="false"
        android:label="SecurePaymentApp"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.AppCompat.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>

// app/src/main/res/layout/activity_main.xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/root"
    android:orientation="vertical"
    android:padding="16dp"
    android:gravity="center_horizontal"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <TextView
        android:id="@+id/balanceText"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Balance: 0"
        android:textSize="18sp"
        android:layout_marginBottom="16dp"/>

    <Button
        android:id="@+id/buyButton"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Buy 1.00 USD Credit"/>

</LinearLayout>

// app/src/main/java/com/example/securepaymentapp/MainActivity.kt
package com.example.securepaymentapp

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import com.example.payment.PaymentConfig
import com.example.payment.PaymentManager
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private lateinit var paymentManager: PaymentManager
    private lateinit var balanceText: TextView
    private lateinit var buyButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        paymentManager = PaymentManager.create(
            context = this,
            config = PaymentConfig(enableLogging = true)
        )

        setContentView(R.layout.activity_main)
        balanceText = findViewById(R.id.balanceText)
        buyButton = findViewById(R.id.buyButton)

        buyButton.setOnClickListener {
            lifecycleScope.launch {
                val result = paymentManager.creditWalletFromPurchase(
                    activity = this@MainActivity,
                    productId = "test_product_id",
                    currency = "USD",
                    amountMinor = 100L
                )
                updateBalance()
                buyButton.isEnabled = !result.success
            }
        }

        lifecycleScope.launch {
            updateBalance()
        }
    }

    private suspend fun updateBalance() {
        val balance = paymentManager.getWalletBalance("USD")
        balanceText.text = "Balance: ${balance.amountMinor} ${balance.currency}"
    }

    override fun onDestroy() {
        super.onDestroy()
        paymentManager.destroy()
    }
}