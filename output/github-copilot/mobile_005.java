#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="android-banking-app"

mkdir -p "$PROJECT_DIR/app/src/main/java/com/example/securebanking/domain"
mkdir -p "$PROJECT_DIR/app/src/main/java/com/example/securebanking/security"
mkdir -p "$PROJECT_DIR/app/src/main/java/com/example/securebanking"
mkdir -p "$PROJECT_DIR/app/src/main/res/layout"
mkdir -p "$PROJECT_DIR/app/src/main/res/values"
mkdir -p "$PROJECT_DIR/app/src/main/res/xml"
mkdir -p "$PROJECT_DIR/app/src/test/java/com/example/securebanking/domain"

cat > "$PROJECT_DIR/settings.gradle.kts" <<'EOF'
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "SecureBankingApp"
include(":app")
EOF

cat > "$PROJECT_DIR/build.gradle.kts" <<'EOF'
plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
}
EOF

cat > "$PROJECT_DIR/gradle.properties" <<'EOF'
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
EOF

cat > "$PROJECT_DIR/app/build.gradle.kts" <<'EOF'
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.securebanking"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.securebanking"
        minSdk = 23
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-ktx:1.9.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.4")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
}
EOF

cat > "$PROJECT_DIR/app/proguard-rules.pro" <<'EOF'
# Intentionally empty for this sample app.
EOF

cat > "$PROJECT_DIR/app/src/main/AndroidManifest.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <application
        android:allowBackup="false"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.SecureBanking"
        android:usesCleartextTraffic="false"
        android:networkSecurityConfig="@xml/network_security_config">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/securebanking/MainActivity.kt" <<'EOF'
package com.example.securebanking

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.example.securebanking.databinding.ActivityMainBinding
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val viewModel: BankingViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(
            WindowManager.LayoutParams.FLAG_SECURE,
            WindowManager.LayoutParams.FLAG_SECURE
        )

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.submitTransferButton.setOnClickListener {
            viewModel.submitTransfer(
                toAccount = binding.destinationAccountInput.text?.toString().orEmpty(),
                amountText = binding.amountInput.text?.toString().orEmpty(),
                reference = binding.referenceInput.text?.toString().orEmpty()
            )
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect(::render)
            }
        }
    }

    private fun render(state: BankingUiState) {
        binding.balanceValue.text = state.balanceFormatted
        binding.statusValue.text = state.statusMessage
        binding.lastTransactionValue.text = state.lastTransactionSummary
        binding.securityBanner.isVisible = state.securityMessage.isNotBlank()
        binding.securityBanner.text = state.securityMessage
        binding.submitTransferButton.isEnabled = state.isTransactionEnabled && !state.isProcessing
        binding.progressIndicator.isVisible = state.isProcessing
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/securebanking/BankingViewModel.kt" <<'EOF'
package com.example.securebanking

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.securebanking.domain.TransactionProcessor
import com.example.securebanking.domain.TransactionRequest
import com.example.securebanking.security.DeviceIntegrityChecker
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.math.BigDecimal
import java.util.Locale

data class BankingUiState(
    val balanceFormatted: String = CurrencyFormatter.formatCents(1_000_000L),
    val isProcessing: Boolean = false,
    val isTransactionEnabled: Boolean = true,
    val statusMessage: String = "Ready to process transfers.",
    val securityMessage: String = "",
    val lastTransactionSummary: String = "No transactions submitted yet."
)

class BankingViewModel : ViewModel() {

    private val transactionProcessor = TransactionProcessor(
        initialAccountId = SOURCE_ACCOUNT_ID,
        initialBalanceCents = 1_000_000L
    )
    private val deviceIntegrityChecker = DeviceIntegrityChecker()

    private val _uiState = MutableStateFlow(BankingUiState())
    val uiState: StateFlow<BankingUiState> = _uiState.asStateFlow()

    init {
        val integrity = deviceIntegrityChecker.evaluate()
        _uiState.update {
            it.copy(
                isTransactionEnabled = !integrity.isCompromised,
                statusMessage = if (integrity.isCompromised) {
                    "Transactions are disabled on compromised devices."
                } else {
                    "Ready to process transfers."
                },
                securityMessage = integrity.message
            )
        }
    }

    fun submitTransfer(toAccount: String, amountText: String, reference: String) {
        if (!_uiState.value.isTransactionEnabled) {
            _uiState.update {
                it.copy(statusMessage = "This device does not meet minimum integrity requirements.")
            }
            return
        }

        val amountCents = parseAmountToCents(amountText)
        if (amountCents == null) {
            _uiState.update { it.copy(statusMessage = "Enter a valid amount with up to two decimal places.") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isProcessing = true, statusMessage = "Processing transfer...") }

            val result = transactionProcessor.process(
                TransactionRequest(
                    fromAccountId = SOURCE_ACCOUNT_ID,
                    toAccountId = toAccount.trim().uppercase(Locale.US),
                    amountCents = amountCents,
                    reference = reference.trim()
                )
            )

            _uiState.update {
                it.copy(
                    isProcessing = false,
                    balanceFormatted = CurrencyFormatter.formatCents(result.balanceCents),
                    statusMessage = result.message,
                    lastTransactionSummary = result.summary
                )
            }
        }
    }

    private fun parseAmountToCents(amountText: String): Long? {
        val sanitized = amountText.trim().replace(",", "").removePrefix("$")
        if (!sanitized.matches(Regex("^\\d+(\\.\\d{1,2})?$"))) {
            return null
        }

        return try {
            BigDecimal(sanitized).movePointRight(2).longValueExact()
        } catch (_: NumberFormatException) {
            null
        } catch (_: ArithmeticException) {
            null
        }
    }

    private companion object {
        const val SOURCE_ACCOUNT_ID = "CHK-1024"
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/securebanking/CurrencyFormatter.kt" <<'EOF'
package com.example.securebanking

import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

object CurrencyFormatter {
    fun formatCents(cents: Long): String {
        val amount = BigDecimal.valueOf(cents, 2)
        return NumberFormat.getCurrencyInstance(Locale.US).format(amount)
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/securebanking/domain/TransactionProcessor.kt" <<'EOF'
package com.example.securebanking.domain

import com.example.securebanking.CurrencyFormatter
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.UUID
import java.util.regex.Pattern

data class TransactionRequest(
    val fromAccountId: String,
    val toAccountId: String,
    val amountCents: Long,
    val reference: String
)

data class TransactionResult(
    val success: Boolean,
    val balanceCents: Long,
    val message: String,
    val summary: String
)

class TransactionProcessor(
    private val initialAccountId: String,
    initialBalanceCents: Long
) {
    private val accountIdPattern = Pattern.compile("^[A-Z0-9-]{4,18}$")
    private val mutex = Mutex()
    private var balanceCents: Long = initialBalanceCents

    suspend fun process(request: TransactionRequest): TransactionResult = mutex.withLock {
        val validationError = validate(request)
        if (validationError != null) {
            return@withLock failure(validationError)
        }

        if (request.amountCents > balanceCents) {
            return@withLock failure("Insufficient funds for this transfer.")
        }

        balanceCents -= request.amountCents
        val transactionId = UUID.randomUUID().toString().take(8).uppercase()
        val formattedAmount = CurrencyFormatter.formatCents(request.amountCents)
        val formattedBalance = CurrencyFormatter.formatCents(balanceCents)

        TransactionResult(
            success = true,
            balanceCents = balanceCents,
            message = "Transfer approved.",
            summary = "Sent $formattedAmount to ${request.toAccountId}. Ref ${safeReference(request.reference)}. Txn $transactionId. Available balance $formattedBalance."
        )
    }

    private fun validate(request: TransactionRequest): String? {
        if (request.fromAccountId != initialAccountId) {
            return "Unsupported source account."
        }
        if (!accountIdPattern.matcher(request.toAccountId).matches()) {
            return "Destination account must be 4-18 characters using A-Z, 0-9, or -."
        }
        if (request.fromAccountId == request.toAccountId) {
            return "Source and destination accounts must be different."
        }
        if (request.amountCents <= 0L) {
            return "Transfer amount must be greater than zero."
        }
        if (request.amountCents > MAX_TRANSACTION_CENTS) {
            return "Transfer exceeds the per-transaction limit."
        }
        if (request.reference.isBlank()) {
            return "Reference is required."
        }
        if (request.reference.length > MAX_REFERENCE_LENGTH) {
            return "Reference must be 40 characters or fewer."
        }
        return null
    }

    private fun safeReference(reference: String): String {
        val sanitized = reference.replace(Regex("[^A-Za-z0-9 .-]"), "").trim()
        return if (sanitized.isBlank()) "GENERAL" else sanitized
    }

    private fun failure(message: String): TransactionResult {
        return TransactionResult(
            success = false,
            balanceCents = balanceCents,
            message = message,
            summary = "No funds moved. Available balance ${CurrencyFormatter.formatCents(balanceCents)}."
        )
    }

    private companion object {
        const val MAX_REFERENCE_LENGTH = 40
        const val MAX_TRANSACTION_CENTS = 2_500_000L
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/securebanking/security/DeviceIntegrityChecker.kt" <<'EOF'
package com.example.securebanking.security

import android.os.Build
import java.io.File

data class DeviceIntegrityStatus(
    val isCompromised: Boolean,
    val message: String
)

class DeviceIntegrityChecker {

    fun evaluate(): DeviceIntegrityStatus {
        return if (isRootedDevice()) {
            DeviceIntegrityStatus(
                isCompromised = true,
                message = "Security check failed: this device appears to be rooted or tampered."
            )
        } else {
            DeviceIntegrityStatus(
                isCompromised = false,
                message = "Device integrity check passed."
            )
        }
    }

    private fun isRootedDevice(): Boolean {
        return hasTestKeys() || hasRootBinary() || hasTamperArtifacts()
    }

    private fun hasTestKeys(): Boolean {
        val tags = Build.TAGS ?: return false
        return tags.contains("test-keys")
    }

    private fun hasRootBinary(): Boolean {
        return ROOT_BINARY_PATHS.any { path -> File(path).exists() }
    }

    private fun hasTamperArtifacts(): Boolean {
        return DANGEROUS_PATHS.any { path -> File(path).exists() }
    }

    private companion object {
        val ROOT_BINARY_PATHS = listOf(
            "/system/bin/su",
            "/system/xbin/su",
            "/sbin/su",
            "/system/app/Superuser.apk",
            "/system/bin/.ext/.su",
            "/system/usr/we-need-root/su-backup",
            "/system/xbin/mu"
        )

        val DANGEROUS_PATHS = listOf(
            "/system/framework/XposedBridge.jar",
            "/data/adb/magisk",
            "/cache/magisk.log"
        )
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/res/layout/activity_main.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:fillViewport="true">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:padding="24dp">

        <TextView
            android:id="@+id/appTitle"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="@string/app_name"
            android:textAppearance="@style/TextAppearance.AppCompat.Large"
            android:textColor="@color/brand_primary"
            android:textStyle="bold" />

        <TextView
            android:id="@+id/securityBanner"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="12dp"
            android:background="@color/banner_background"
            android:padding="12dp"
            android:textColor="@color/banner_text" />

        <TextView
            android:id="@+id/balanceLabel"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="24dp"
            android:text="@string/balance_label"
            android:textAppearance="@style/TextAppearance.AppCompat.Medium"
            android:textStyle="bold" />

        <TextView
            android:id="@+id/balanceValue"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:text="@string/default_balance"
            android:textAppearance="@style/TextAppearance.AppCompat.Large"
            android:textColor="@color/brand_primary" />

        <TextView
            android:id="@+id/formLabel"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="32dp"
            android:text="@string/transfer_title"
            android:textAppearance="@style/TextAppearance.AppCompat.Medium"
            android:textStyle="bold" />

        <EditText
            android:id="@+id/destinationAccountInput"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="12dp"
            android:hint="@string/destination_account_hint"
            android:inputType="textCapCharacters"
            android:maxLength="18" />

        <EditText
            android:id="@+id/amountInput"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="12dp"
            android:hint="@string/amount_hint"
            android:inputType="numberDecimal" />

        <EditText
            android:id="@+id/referenceInput"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="12dp"
            android:hint="@string/reference_hint"
            android:inputType="textCapSentences"
            android:maxLength="40" />

        <Button
            android:id="@+id/submitTransferButton"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="20dp"
            android:text="@string/submit_transfer" />

        <ProgressBar
            android:id="@+id/progressIndicator"
            style="?android:attr/progressBarStyle"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_gravity="center_horizontal"
            android:layout_marginTop="16dp"
            android:visibility="gone" />

        <TextView
            android:id="@+id/statusLabel"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="24dp"
            android:text="@string/status_label"
            android:textAppearance="@style/TextAppearance.AppCompat.Medium"
            android:textStyle="bold" />

        <TextView
            android:id="@+id/statusValue"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:text="@string/default_status" />

        <TextView
            android:id="@+id/lastTransactionLabel"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="24dp"
            android:text="@string/last_transaction_label"
            android:textAppearance="@style/TextAppearance.AppCompat.Medium"
            android:textStyle="bold" />

        <TextView
            android:id="@+id/lastTransactionValue"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:text="@string/default_last_transaction" />
    </LinearLayout>
</ScrollView>
EOF

cat > "$PROJECT_DIR/app/src/main/res/values/strings.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Secure Banking</string>
    <string name="balance_label">Available balance</string>
    <string name="default_balance">$10,000.00</string>
    <string name="transfer_title">Transfer funds</string>
    <string name="destination_account_hint">Destination account (for example SAV-2201)</string>
    <string name="amount_hint">Amount (for example 125.50)</string>
    <string name="reference_hint">Payment reference</string>
    <string name="submit_transfer">Submit transfer</string>
    <string name="status_label">Status</string>
    <string name="default_status">Ready to process transfers.</string>
    <string name="last_transaction_label">Last transaction</string>
    <string name="default_last_transaction">No transactions submitted yet.</string>
</resources>
EOF

cat > "$PROJECT_DIR/app/src/main/res/values/colors.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="brand_primary">#0B5FFF</color>
    <color name="brand_primary_dark">#083EA8</color>
    <color name="brand_surface">#FFFFFF</color>
    <color name="brand_text">#14213D</color>
    <color name="banner_background">#E7F0FF</color>
    <color name="banner_text">#083EA8</color>
</resources>
EOF

cat > "$PROJECT_DIR/app/src/main/res/values/themes.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources xmlns:tools="http://schemas.android.com/tools">
    <style name="Theme.SecureBanking" parent="Theme.MaterialComponents.DayNight.NoActionBar">
        <item name="colorPrimary">@color/brand_primary</item>
        <item name="colorPrimaryVariant">@color/brand_primary_dark</item>
        <item name="colorOnPrimary">@color/brand_surface</item>
        <item name="android:statusBarColor" tools:targetApi="l">@color/brand_primary_dark</item>
        <item name="android:navigationBarColor">@color/brand_surface</item>
        <item name="android:windowBackground">@color/brand_surface</item>
        <item name="android:textColorPrimary">@color/brand_text</item>
    </style>
</resources>
EOF

cat > "$PROJECT_DIR/app/src/main/res/xml/network_security_config.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="false" />
</network-security-config>
EOF

cat > "$PROJECT_DIR/app/src/test/java/com/example/securebanking/domain/TransactionProcessorTest.kt" <<'EOF'
package com.example.securebanking.domain

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TransactionProcessorTest {

    @Test
    fun processesValidTransferAtomically() = runTest {
        val processor = TransactionProcessor(
            initialAccountId = "CHK-1024",
            initialBalanceCents = 100_000L
        )

        val result = processor.process(
            TransactionRequest(
                fromAccountId = "CHK-1024",
                toAccountId = "SAV-2201",
                amountCents = 12_500L,
                reference = "Monthly contribution"
            )
        )

        assertTrue(result.success)
        assertEquals(87_500L, result.balanceCents)
    }

    @Test
    fun rejectsTransferWhenBalanceIsTooLow() = runTest {
        val processor = TransactionProcessor(
            initialAccountId = "CHK-1024",
            initialBalanceCents = 100_000L
        )

        val result = processor.process(
            TransactionRequest(
                fromAccountId = "CHK-1024",
                toAccountId = "SAV-2201",
                amountCents = 500_000L,
                reference = "Large transfer"
            )
        )

        assertFalse(result.success)
        assertEquals(100_000L, result.balanceCents)
    }

    @Test
    fun rejectsTransferToSameAccount() = runTest {
        val processor = TransactionProcessor(
            initialAccountId = "CHK-1024",
            initialBalanceCents = 100_000L
        )

        val result = processor.process(
            TransactionRequest(
                fromAccountId = "CHK-1024",
                toAccountId = "CHK-1024",
                amountCents = 2_000L,
                reference = "Loopback"
            )
        )

        assertFalse(result.success)
        assertEquals(100_000L, result.balanceCents)
    }
}
EOF

echo "Project created in $PROJECT_DIR"