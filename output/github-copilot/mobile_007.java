#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="android-biometric-sample"

mkdir -p "$PROJECT_DIR/app/src/main/java/com/example/biometriclogin"
mkdir -p "$PROJECT_DIR/app/src/main/res/layout"
mkdir -p "$PROJECT_DIR/app/src/main/res/values"

cat > "$PROJECT_DIR/settings.gradle.kts" <<'EOF'
import org.gradle.api.initialization.resolve.RepositoriesMode

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

rootProject.name = "BiometricLoginApp"
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
EOF

cat > "$PROJECT_DIR/app/build.gradle.kts" <<'EOF'
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.biometriclogin"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.biometriclogin"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildFeatures {
        viewBinding = true
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
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.biometric:biometric:1.1.0")
}
EOF

cat > "$PROJECT_DIR/app/src/main/AndroidManifest.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.USE_BIOMETRIC" />

    <application
        android:allowBackup="true"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.BiometricLoginApp">

        <activity
            android:name=".HomeActivity"
            android:exported="false" />

        <activity
            android:name=".LoginActivity"
            android:exported="false" />

        <activity
            android:name=".LauncherActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/biometriclogin/AuthPreferences.kt" <<'EOF'
package com.example.biometriclogin

import android.content.Context
import android.content.SharedPreferences

class AuthPreferences(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    var biometricEnabled: Boolean
        get() = prefs.getBoolean(KEY_BIOMETRIC_ENABLED, false)
        set(value) = prefs.edit().putBoolean(KEY_BIOMETRIC_ENABLED, value).apply()

    var isAuthenticated: Boolean
        get() = prefs.getBoolean(KEY_IS_AUTHENTICATED, false)
        set(value) = prefs.edit().putBoolean(KEY_IS_AUTHENTICATED, value).apply()

    fun clearSession() {
        isAuthenticated = false
    }

    companion object {
        private const val PREFS_NAME = "auth_prefs"
        private const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
        private const val KEY_IS_AUTHENTICATED = "is_authenticated"
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/biometriclogin/BiometricHelper.kt" <<'EOF'
package com.example.biometriclogin

import android.content.Context
import androidx.appcompat.app.AppCompatActivity
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat

object BiometricHelper {

    private const val AUTHENTICATORS = BiometricManager.Authenticators.BIOMETRIC_STRONG

    fun canAuthenticate(context: Context): Boolean {
        return BiometricManager.from(context).canAuthenticate(AUTHENTICATORS) ==
            BiometricManager.BIOMETRIC_SUCCESS
    }

    fun showPrompt(
        activity: AppCompatActivity,
        onSuccess: () -> Unit,
        onFallbackToPassword: () -> Unit
    ) {
        val executor = ContextCompat.getMainExecutor(activity)

        val biometricPrompt = BiometricPrompt(
            activity,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    onSuccess()
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    onFallbackToPassword()
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                }
            }
        )

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Unlock with fingerprint")
            .setSubtitle("Use your fingerprint to unlock the app")
            .setNegativeButtonText("Use password")
            .setAllowedAuthenticators(AUTHENTICATORS)
            .build()

        biometricPrompt.authenticate(promptInfo)
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/biometriclogin/LauncherActivity.kt" <<'EOF'
package com.example.biometriclogin

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.biometriclogin.databinding.ActivityLauncherBinding

class LauncherActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLauncherBinding
    private lateinit var authPreferences: AuthPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLauncherBinding.inflate(layoutInflater)
        setContentView(binding.root)

        authPreferences = AuthPreferences(this)
    }

    override fun onResume() {
        super.onResume()
        authPreferences.clearSession()

        if (authPreferences.biometricEnabled && BiometricHelper.canAuthenticate(this)) {
            binding.statusText.text = getString(R.string.biometric_prompt_status)
            BiometricHelper.showPrompt(
                activity = this,
                onSuccess = {
                    authPreferences.isAuthenticated = true
                    openHome()
                },
                onFallbackToPassword = {
                    openLogin()
                }
            )
        } else {
            openLogin()
        }
    }

    private fun openLogin() {
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }

    private fun openHome() {
        startActivity(Intent(this, HomeActivity::class.java))
        finish()
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/biometriclogin/LoginActivity.kt" <<'EOF'
package com.example.biometriclogin

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.biometriclogin.databinding.ActivityLoginBinding

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var authPreferences: AuthPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        authPreferences = AuthPreferences(this)
        binding.enableBiometricSwitch.isChecked = authPreferences.biometricEnabled

        binding.loginButton.setOnClickListener {
            performLogin()
        }
    }

    private fun performLogin() {
        val username = binding.usernameInput.text?.toString()?.trim().orEmpty()
        val password = binding.passwordInput.text?.toString().orEmpty()

        if (username == DEMO_USERNAME && password == DEMO_PASSWORD) {
            val wantsBiometric = binding.enableBiometricSwitch.isChecked

            authPreferences.biometricEnabled = if (wantsBiometric) {
                if (BiometricHelper.canAuthenticate(this)) {
                    true
                } else {
                    Toast.makeText(
                        this,
                        R.string.biometric_unavailable_message,
                        Toast.LENGTH_LONG
                    ).show()
                    false
                }
            } else {
                false
            }

            authPreferences.isAuthenticated = true
            startActivity(Intent(this, HomeActivity::class.java))
            finish()
        } else {
            Toast.makeText(this, R.string.invalid_credentials, Toast.LENGTH_SHORT).show()
        }
    }

    companion object {
        private const val DEMO_USERNAME = "demo"
        private const val DEMO_PASSWORD = "password123"
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/java/com/example/biometriclogin/HomeActivity.kt" <<'EOF'
package com.example.biometriclogin

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.biometriclogin.databinding.ActivityHomeBinding

class HomeActivity : AppCompatActivity() {

    private lateinit var binding: ActivityHomeBinding
    private lateinit var authPreferences: AuthPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHomeBinding.inflate(layoutInflater)
        setContentView(binding.root)

        authPreferences = AuthPreferences(this)

        if (!authPreferences.isAuthenticated) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        binding.biometricStatus.text = getString(
            if (authPreferences.biometricEnabled) {
                R.string.biometric_enabled
            } else {
                R.string.biometric_disabled
            }
        )

        binding.logoutButton.setOnClickListener {
            authPreferences.clearSession()
            startActivity(Intent(this, LauncherActivity::class.java))
            finish()
        }
    }
}
EOF

cat > "$PROJECT_DIR/app/src/main/res/layout/activity_launcher.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:gravity="center"
    android:orientation="vertical"
    android:padding="24dp">

    <ProgressBar
        android:layout_width="wrap_content"
        android:layout_height="wrap_content" />

    <TextView
        android:id="@+id/statusText"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="16dp"
        android:text="@string/checking_auth"
        android:textAppearance="?attr/textAppearanceBodyLarge" />

</LinearLayout>
EOF

cat > "$PROJECT_DIR/app/src/main/res/layout/activity_login.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:gravity="center_horizontal"
        android:orientation="vertical"
        android:padding="24dp">

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="@string/login_title"
            android:textAppearance="?attr/textAppearanceHeadlineMedium" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:text="@string/demo_credentials"
            android:textAppearance="?attr/textAppearanceBodyMedium" />

        <EditText
            android:id="@+id/usernameInput"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="24dp"
            android:hint="@string/username"
            android:inputType="text"
            android:maxLines="1" />

        <EditText
            android:id="@+id/passwordInput"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="16dp"
            android:hint="@string/password"
            android:inputType="textPassword"
            android:maxLines="1" />

        <androidx.appcompat.widget.SwitchCompat
            android:id="@+id/enableBiometricSwitch"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="16dp"
            android:text="@string/enable_biometric" />

        <Button
            android:id="@+id/loginButton"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="24dp"
            android:text="@string/login" />

    </LinearLayout>

</ScrollView>
EOF

cat > "$PROJECT_DIR/app/src/main/res/layout/activity_home.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:gravity="center_horizontal"
    android:orientation="vertical"
    android:padding="24dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="@string/home_title"
        android:textAppearance="?attr/textAppearanceHeadlineMedium" />

    <TextView
        android:id="@+id/biometricStatus"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="12dp"
        android:textAppearance="?attr/textAppearanceBodyLarge" />

    <Button
        android:id="@+id/logoutButton"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="24dp"
        android:text="@string/logout" />

</LinearLayout>
EOF

cat > "$PROJECT_DIR/app/src/main/res/values/strings.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Biometric Login App</string>
    <string name="checking_auth">Checking authentication...</string>
    <string name="biometric_prompt_status">Authenticate with your fingerprint</string>
    <string name="login_title">Sign in</string>
    <string name="demo_credentials">Demo credentials: demo / password123</string>
    <string name="username">Username</string>
    <string name="password">Password</string>
    <string name="enable_biometric">Enable biometric login</string>
    <string name="login">Login</string>
    <string name="invalid_credentials">Invalid username or password</string>
    <string name="biometric_unavailable_message">Fingerprint authentication is not available on this device.</string>
    <string name="home_title">Welcome</string>
    <string name="biometric_enabled">Biometric login is enabled</string>
    <string name="biometric_disabled">Biometric login is disabled</string>
    <string name="logout">Logout</string>
</resources>
EOF

cat > "$PROJECT_DIR/app/src/main/res/values/colors.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">#6750A4</color>
    <color name="primaryVariant">#4F378B</color>
    <color name="secondary">#625B71</color>
    <color name="background">#FFFBFE</color>
    <color name="surface">#FFFBFE</color>
    <color name="onPrimary">#FFFFFF</color>
    <color name="onBackground">#1C1B1F</color>
    <color name="onSurface">#1C1B1F</color>
</resources>
EOF

cat > "$PROJECT_DIR/app/src/main/res/values/themes.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources xmlns:tools="http://schemas.android.com/tools">
    <style name="Theme.BiometricLoginApp" parent="Theme.MaterialComponents.DayNight.NoActionBar">
        <item name="colorPrimary">@color/primary</item>
        <item name="colorPrimaryVariant">@color/primaryVariant</item>
        <item name="colorSecondary">@color/secondary</item>
        <item name="android:statusBarColor" tools:targetApi="l">@color/primaryVariant</item>
        <item name="android:windowBackground">@color/background</item>
        <item name="android:textColor">@color/onBackground</item>
    </style>
</resources>
EOF

echo "Created $PROJECT_DIR"