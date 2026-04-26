package com.example.paymentapp

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.paymentapp.databinding.ActivityMainBinding
import com.example.paymentapp.payment.InAppPurchaseManager
import com.example.paymentapp.payment.PaymentOutcome
import com.example.paymentapp.payment.PaymentProcessor
import com.example.paymentapp.payment.SecureHttpClientFactory
import com.example.paymentapp.payment.TokenizedPaymentMethod
import com.example.paymentapp.payment.WalletTransactionRequest
import com.example.paymentapp.payment.WalletTransactionService
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var paymentProcessor: PaymentProcessor

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        paymentProcessor = PaymentProcessor(
            inAppPurchaseManager = InAppPurchaseManager(applicationContext),
            walletTransactionService = WalletTransactionService(
                baseUrl = "https://api.example.com/",
                httpClient = SecureHttpClientFactory.create(
                    pinnedHost = "api.example.com",
                    sha256Pins = emptySet()
                )
            )
        )

        binding.startPurchaseButton.setOnClickListener {
            val productId = binding.productIdInput.text?.toString().orEmpty().trim()
            if (productId.isEmpty()) {
                renderStatus(PaymentOutcome.Failure("Enter a product ID."))
                return@setOnClickListener
            }

            lifecycleScope.launch {
                renderStatus(PaymentOutcome.Pending("Opening Google Play Billing flow..."))
                renderStatus(paymentProcessor.startInAppPurchase(this@MainActivity, productId))
            }
        }

        binding.sendWalletButton.setOnClickListener {
            val amountMinor = binding.amountInput.text?.toString()?.toLongOrNull()
            val recipientId = binding.recipientInput.text?.toString().orEmpty().trim()

            if (amountMinor == null || amountMinor <= 0L || recipientId.isEmpty()) {
                renderStatus(PaymentOutcome.Failure("Enter a valid wallet amount and recipient ID."))
                return@setOnClickListener
            }

            lifecycleScope.launch {
                val paymentMethod = TokenizedPaymentMethod(
                    token = "wallet-demo-token".toCharArray(),
                    brand = "TOKENIZED",
                    lastFour = "0000"
                )
                val authToken = "demo-session-token".toCharArray()

                try {
                    renderStatus(PaymentOutcome.Pending("Submitting wallet transaction..."))
                    renderStatus(
                        paymentProcessor.submitWalletTransaction(
                            WalletTransactionRequest(
                                amountMinor = amountMinor,
                                currency = "USD",
                                recipientId = recipientId,
                                paymentMethod = paymentMethod,
                                metadata = mapOf("origin" to "demo-app")
                            ),
                            authToken = authToken
                        )
                    )
                } finally {
                    authToken.fill('\u0000')
                    paymentMethod.close()
                }
            }
        }
    }

    private fun renderStatus(outcome: PaymentOutcome) {
        binding.statusText.text = when (outcome) {
            is PaymentOutcome.Success -> "Status: success (${outcome.reference})"
            is PaymentOutcome.Pending -> "Status: pending (${outcome.message})"
            is PaymentOutcome.Failure -> "Status: failure (${outcome.reason})"
        }
    }
}

// File: android-payment-module/app/src/main/java/com/example/paymentapp/payment/PaymentModels.kt
package com.example.paymentapp.payment

import java.io.Closeable
import java.util.UUID

data class TokenizedPaymentMethod(
    private val token: CharArray,
    val brand: String,
    val lastFour: String
) : Closeable {
    fun revealToken(): String = String(token)

    override fun close() {
        token.fill('\u0000')
    }
}

data class WalletTransactionRequest(
    val amountMinor: Long,
    val currency: String,
    val recipientId: String,
    val paymentMethod: TokenizedPaymentMethod,
    val metadata: Map<String, String> = emptyMap(),
    val idempotencyKey: String = UUID.randomUUID().toString()
)

sealed interface PaymentOutcome {
    data class Success(val reference: String) : PaymentOutcome
    data class Pending(val message: String) : PaymentOutcome
    data class Failure(val reason: String) : PaymentOutcome
}

// File: android-payment-module/app/src/main/java/com/example/paymentapp/payment/SecureHttpClientFactory.kt
package com.example.paymentapp.payment

import okhttp3.CertificatePinner
import okhttp3.ConnectionSpec
import okhttp3.OkHttpClient
import okhttp3.TlsVersion
import java.util.concurrent.TimeUnit

object SecureHttpClientFactory {
    fun create(
        pinnedHost: String,
        sha256Pins: Set<String>
    ): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectionSpecs(
                listOf(
                    ConnectionSpec.Builder(ConnectionSpec.MODERN_TLS)
                        .tlsVersions(TlsVersion.TLS_1_3, TlsVersion.TLS_1_2)
                        .allEnabledCipherSuites()
                        .build(),
                    ConnectionSpec.COMPATIBLE_TLS
                )
            )
            .retryOnConnectionFailure(false)
            .followRedirects(false)
            .followSslRedirects(false)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)

        if (sha256Pins.isNotEmpty()) {
            val certificatePinner = CertificatePinner.Builder().apply {
                sha256Pins.forEach { add(pinnedHost, it) }
            }.build()
            builder.certificatePinner(certificatePinner)
        }

        return builder.build()
    }
}

// File: android-payment-module/app/src/main/java/com/example/paymentapp/payment/WalletTransactionService.kt
package com.example.paymentapp.payment

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONException
import org.json.JSONObject
import java.io.IOException
import java.net.URI

class WalletTransactionService(
    baseUrl: String,
    private val httpClient: OkHttpClient
) {
    private val secureBaseUri: URI = requireSecureBaseUrl(baseUrl)

    suspend fun submitTransaction(
        request: WalletTransactionRequest,
        authToken: CharArray
    ): PaymentOutcome = withContext(Dispatchers.IO) {
        val endpoint = secureBaseUri.resolve("/v1/wallet/transactions").toString()
        val authHeader = "Bearer ${String(authToken)}"
        val bodyJson = buildJsonPayload(request)

        val httpRequest = Request.Builder()
            .url(endpoint)
            .post(bodyJson.toRequestBody("application/json; charset=utf-8".toMediaType()))
            .header("Accept", "application/json")
            .header("Authorization", authHeader)
            .header("Idempotency-Key", request.idempotencyKey)
            .build()

        authToken.fill('\u0000')

        try {
            httpClient.newCall(httpRequest).execute().use { response ->
                val payload = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    val serverMessage = payload.takeIf { it.isNotBlank() }
                        ?: "Wallet API returned ${response.code}"
                    return@withContext PaymentOutcome.Failure(serverMessage)
                }

                val json = if (payload.isBlank()) JSONObject() else JSONObject(payload)
                val reference = json.optString("transactionId")
                    .ifBlank { json.optString("reference") }
                    .ifBlank { request.idempotencyKey }

                return@withContext when (json.optString("status")) {
                    "queued", "pending" -> PaymentOutcome.Pending(reference)
                    else -> PaymentOutcome.Success(reference)
                }
            }
        } catch (e: IOException) {
            return@withContext PaymentOutcome.Failure(e.message ?: "Wallet transaction failed.")
        } catch (e: JSONException) {
            return@withContext PaymentOutcome.Failure("Wallet API returned invalid JSON.")
        }
    }

    internal fun buildJsonPayload(request: WalletTransactionRequest): String {
        val paymentToken = request.paymentMethod.revealToken()
        val metadataJson = JSONObject()
        request.metadata.forEach { (key, value) -> metadataJson.put(key, value) }

        return JSONObject()
            .put("amountMinor", request.amountMinor)
            .put("currency", request.currency)
            .put("recipientId", request.recipientId)
            .put(
                "paymentMethod",
                JSONObject()
                    .put("type", "tokenized")
                    .put("token", paymentToken)
                    .put("brand", request.paymentMethod.brand)
                    .put("lastFour", request.paymentMethod.lastFour)
            )
            .put("metadata", metadataJson)
            .put("idempotencyKey", request.idempotencyKey)
            .toString()
    }

    internal fun requireSecureBaseUrl(rawBaseUrl: String): URI {
        val uri = URI(rawBaseUrl)
        require(uri.scheme.equals("https", ignoreCase = true)) {
            "WalletTransactionService requires an HTTPS base URL."
        }
        return uri
    }
}

// File: android-payment-module/app/src/main/java/com/example/paymentapp/payment/InAppPurchaseManager.kt
package com.example.paymentapp.payment

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.TimeoutCancellationException
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class InAppPurchaseManager(
    context: Context
) : PurchasesUpdatedListener {
    private val billingClient: BillingClient = BillingClient.newBuilder(context)
        .setListener(this)
        .enablePendingPurchases()
        .build()

    @Volatile
    private var purchaseOutcome = CompletableDeferred<PaymentOutcome>()

    suspend fun launchPurchase(activity: Activity, productId: String): PaymentOutcome {
        return try {
            connectIfNeeded()
            val productDetails = queryInAppProduct(productId)
                ?: return PaymentOutcome.Failure("Product not found in Google Play: $productId")

            purchaseOutcome = CompletableDeferred()
            val productParam = BillingFlowParams.ProductDetailsParams.newBuilder()
                .setProductDetails(productDetails)
                .build()
            val flowParams = BillingFlowParams.newBuilder()
                .setProductDetailsParamsList(listOf(productParam))
                .build()

            val result = withContext(Dispatchers.Main) {
                billingClient.launchBillingFlow(activity, flowParams)
            }

            if (result.responseCode != BillingClient.BillingResponseCode.OK) {
                return PaymentOutcome.Failure(
                    result.debugMessage.ifBlank { "Unable to launch billing flow." }
                )
            }

            withTimeout(60_000L) {
                purchaseOutcome.await()
            }
        } catch (e: TimeoutCancellationException) {
            PaymentOutcome.Failure("Timed out waiting for Google Play purchase result.")
        } catch (e: IllegalStateException) {
            PaymentOutcome.Failure(e.message ?: "Google Play Billing unavailable.")
        }
    }

    override fun onPurchasesUpdated(
        billingResult: BillingResult,
        purchases: MutableList<Purchase>?
    ) {
        when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                val purchase = purchases.orEmpty().firstOrNull()
                if (purchase == null) {
                    completeSafely(PaymentOutcome.Failure("No purchase was returned by Google Play."))
                    return
                }

                when (purchase.purchaseState) {
                    Purchase.PurchaseState.PURCHASED -> acknowledgeAndComplete(purchase)
                    Purchase.PurchaseState.PENDING -> completeSafely(
                        PaymentOutcome.Pending("Purchase is pending approval.")
                    )
                    else -> completeSafely(PaymentOutcome.Failure("Purchase was not completed."))
                }
            }
            BillingClient.BillingResponseCode.USER_CANCELED -> {
                completeSafely(PaymentOutcome.Failure("Purchase canceled by user."))
            }
            else -> {
                completeSafely(
                    PaymentOutcome.Failure(
                        billingResult.debugMessage.ifBlank {
                            "Billing error ${billingResult.responseCode}"
                        }
                    )
                )
            }
        }
    }

    private fun acknowledgeAndComplete(purchase: Purchase) {
        if (purchase.isAcknowledged) {
            completeSafely(PaymentOutcome.Success(purchase.orderId ?: purchase.purchaseToken))
            return
        }

        val params = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()

        billingClient.acknowledgePurchase(params) { result ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                completeSafely(PaymentOutcome.Success(purchase.orderId ?: purchase.purchaseToken))
            } else {
                completeSafely(
                    PaymentOutcome.Failure(
                        result.debugMessage.ifBlank { "Purchase acknowledgement failed." }
                    )
                )
            }
        }
    }

    private fun completeSafely(outcome: PaymentOutcome) {
        if (!purchaseOutcome.isCompleted) {
            purchaseOutcome.complete(outcome)
        }
    }

    private suspend fun connectIfNeeded() {
        if (billingClient.isReady) {
            return
        }

        suspendCancellableCoroutine<Unit> { continuation ->
            billingClient.startConnection(object : BillingClientStateListener {
                override fun onBillingServiceDisconnected() {
                    if (continuation.isActive) {
                        continuation.resumeWithException(
                            IllegalStateException("Google Play Billing disconnected.")
                        )
                    }
                }

                override fun onBillingSetupFinished(billingResult: BillingResult) {
                    if (!continuation.isActive) {
                        return
                    }

                    if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                        continuation.resume(Unit)
                    } else {
                        continuation.resumeWithException(
                            IllegalStateException(
                                billingResult.debugMessage.ifBlank {
                                    "Google Play Billing unavailable."
                                }
                            )
                        )
                    }
                }
            })
        }
    }

    private suspend fun queryInAppProduct(productId: String): ProductDetails? {
        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(
                listOf(
                    QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(productId)
                        .setProductType(BillingClient.ProductType.INAPP)
                        .build()
                )
            )
            .build()

        return suspendCancellableCoroutine { continuation ->
            billingClient.queryProductDetailsAsync(params) { result, detailsList ->
                if (!continuation.isActive) {
                    return@queryProductDetailsAsync
                }

                if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                    continuation.resume(detailsList.firstOrNull())
                } else {
                    continuation.resumeWithException(
                        IllegalStateException(
                            result.debugMessage.ifBlank { "Unable to query product details." }
                        )
                    )
                }
            }
        }
    }
}

// File: android-payment-module/app/src/main/java/com/example/paymentapp/payment/PaymentProcessor.kt
package com.example.paymentapp.payment

import android.app.Activity

class PaymentProcessor(
    private val inAppPurchaseManager: InAppPurchaseManager,
    private val walletTransactionService: WalletTransactionService
) {
    suspend fun startInAppPurchase(
        activity: Activity,
        productId: String
    ): PaymentOutcome = inAppPurchaseManager.launchPurchase(activity, productId)

    suspend fun submitWalletTransaction(
        request: WalletTransactionRequest,
        authToken: CharArray
    ): PaymentOutcome = walletTransactionService.submitTransaction(request, authToken)
}

// File: android-payment-module/app/src/test/java/com/example/paymentapp/payment/WalletTransactionServiceTest.kt
package com.example.paymentapp.payment

import okhttp3.OkHttpClient
import org.junit.Assert.assertTrue
import org.junit.Test

class WalletTransactionServiceTest {
    private val service = WalletTransactionService(
        baseUrl = "https://api.example.com/",
        httpClient = OkHttpClient()
    )

    @Test
    fun buildJsonPayloadIncludesIdempotencyKeyAndTokenizedFields() {
        val request = WalletTransactionRequest(
            amountMinor = 499,
            currency = "USD",
            recipientId = "wallet-user-123",
            paymentMethod = TokenizedPaymentMethod(
                token = "tok_live_123".toCharArray(),
                brand = "VISA",
                lastFour = "4242"
            ),
            metadata = mapOf("origin" to "test"),
            idempotencyKey = "demo-key-1"
        )

        val payload = service.buildJsonPayload(request)

        assertTrue(payload.contains("\"idempotencyKey\":\"demo-key-1\""))
        assertTrue(payload.contains("\"token\":\"tok_live_123\""))
        assertTrue(payload.contains("\"recipientId\":\"wallet-user-123\""))
        request.paymentMethod.close()
    }

    @Test(expected = IllegalArgumentException::class)
    fun requireSecureBaseUrlRejectsHttp() {
        service.requireSecureBaseUrl("http://api.example.com/")
    }
}