#!/bin/sh
set -eu

mkdir -p app/src/main/java/com/example/usersapp
mkdir -p app/src/main/res/layout
mkdir -p app/src/main/res/drawable
mkdir -p app/src/main/res/values

cat > settings.gradle <<'EOF'
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

rootProject.name = "UsersApp"
include(":app")
EOF

cat > build.gradle <<'EOF'
plugins {
    id 'com.android.application' version '8.5.2' apply false
    id 'org.jetbrains.kotlin.android' version '1.9.24' apply false
}
EOF

cat > gradle.properties <<'EOF'
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
EOF

cat > gradlew <<'EOF'
#!/bin/sh
set -eu

if command -v gradle >/dev/null 2>&1; then
  exec gradle "$@"
fi

echo "Gradle is required to build this project. Install Gradle or open the project in Android Studio." >&2
exit 1
EOF
chmod +x gradlew

cat > gradlew.bat <<'EOF'
@echo off
where gradle >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  gradle %*
  exit /b %ERRORLEVEL%
)
echo Gradle is required to build this project. Install Gradle or open the project in Android Studio. 1>&2
exit /b 1
EOF

cat > app/build.gradle <<'EOF'
plugins {
    id 'com.android.application'
    id 'org.jetbrains.kotlin.android'
}

android {
    namespace 'com.example.usersapp'
    compileSdk 34

    defaultConfig {
        applicationId "com.example.usersapp"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "1.0"

        testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            debuggable true
        }
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }

    flavorDimensions += "environment"

    productFlavors {
        development {
            dimension "environment"
            applicationIdSuffix ".dev"
            versionNameSuffix "-dev"
            buildConfigField "String", "BASE_URL", "\"https://dev.api.example.com/\""
        }
        staging {
            dimension "environment"
            applicationIdSuffix ".staging"
            versionNameSuffix "-staging"
            buildConfigField "String", "BASE_URL", "\"https://staging.api.example.com/\""
        }
        production {
            dimension "environment"
            buildConfigField "String", "BASE_URL", "\"https://api.example.com/\""
        }
    }

    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = '17'
    }

    buildFeatures {
        buildConfig true
    }
}

dependencies {
    implementation 'androidx.core:core-ktx:1.13.1'
    implementation 'androidx.appcompat:appcompat:1.7.0'
    implementation 'androidx.recyclerview:recyclerview:1.3.2'
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
    implementation 'com.squareup.okhttp3:okhttp:3.14.9'
    implementation 'com.squareup.okhttp3:logging-interceptor:3.14.9'

    testImplementation 'junit:junit:4.13.2'
    androidTestImplementation 'androidx.test.ext:junit:1.2.1'
    androidTestImplementation 'androidx.test.espresso:espresso-core:3.6.1'
}
EOF

cat > app/proguard-rules.pro <<'EOF'
# Intentionally empty for MVP.
EOF

cat > app/src/main/AndroidManifest.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:allowBackup="true"
        android:icon="@drawable/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@drawable/ic_launcher"
        android:supportsRtl="true"
        android:theme="@style/Theme.UsersApp">
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

cat > app/src/main/java/com/example/usersapp/MainActivity.kt <<'EOF'
package com.example.usersapp

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class MainActivity : AppCompatActivity() {

    private val repository = UserRepository()
    private var activeCall: Call<List<User>>? = null

    private lateinit var progressBar: ProgressBar
    private lateinit var statusText: TextView
    private lateinit var retryButton: Button
    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: UsersAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        progressBar = findViewById(R.id.progressBar)
        statusText = findViewById(R.id.statusText)
        retryButton = findViewById(R.id.retryButton)
        recyclerView = findViewById(R.id.usersRecyclerView)

        adapter = UsersAdapter()
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = adapter

        retryButton.setOnClickListener { fetchUsers() }

        fetchUsers()
    }

    private fun fetchUsers() {
        activeCall?.cancel()
        showLoading()

        activeCall = repository.fetchUsers(object : Callback<List<User>> {
            override fun onResponse(call: Call<List<User>>, response: Response<List<User>>) {
                if (!response.isSuccessful) {
                    showError(getString(R.string.error_http, response.code()))
                    return
                }

                val users = response.body().orEmpty()
                adapter.submitList(users)
                showUsers(users)
            }

            override fun onFailure(call: Call<List<User>>, t: Throwable) {
                if (call.isCanceled) {
                    return
                }

                showError(t.message ?: getString(R.string.error_generic))
            }
        })
    }

    private fun showLoading() {
        progressBar.visibility = View.VISIBLE
        recyclerView.visibility = View.GONE
        retryButton.visibility = View.GONE
        statusText.visibility = View.VISIBLE
        statusText.text = getString(R.string.loading)
    }

    private fun showUsers(users: List<User>) {
        progressBar.visibility = View.GONE
        retryButton.visibility = if (users.isEmpty()) View.VISIBLE else View.GONE
        recyclerView.visibility = if (users.isEmpty()) View.GONE else View.VISIBLE
        statusText.visibility = View.VISIBLE
        statusText.text = if (users.isEmpty()) {
            getString(R.string.empty_state)
        } else {
            getString(R.string.environment_label, BuildConfig.FLAVOR)
        }
    }

    private fun showError(message: String) {
        progressBar.visibility = View.GONE
        recyclerView.visibility = View.GONE
        retryButton.visibility = View.VISIBLE
        statusText.visibility = View.VISIBLE
        statusText.text = getString(R.string.error_message, message)
    }

    override fun onDestroy() {
        activeCall?.cancel()
        super.onDestroy()
    }
}
EOF

cat > app/src/main/java/com/example/usersapp/NetworkModule.kt <<'EOF'
package com.example.usersapp

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object NetworkModule {

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor.Level.BODY
        } else {
            HttpLoggingInterceptor.Level.BASIC
        }
    }

    private val okHttpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .addInterceptor(loggingInterceptor)
        .build()

    private val retrofit: Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val apiService: UserApiService = retrofit.create(UserApiService::class.java)
}
EOF

cat > app/src/main/java/com/example/usersapp/User.kt <<'EOF'
package com.example.usersapp

data class User(
    val id: Long,
    val name: String? = null,
    val email: String? = null,
    val username: String? = null
)
EOF

cat > app/src/main/java/com/example/usersapp/UserApiService.kt <<'EOF'
package com.example.usersapp

import retrofit2.Call
import retrofit2.http.GET

interface UserApiService {
    @GET("users")
    fun getUsers(): Call<List<User>>
}
EOF

cat > app/src/main/java/com/example/usersapp/UserRepository.kt <<'EOF'
package com.example.usersapp

import retrofit2.Call
import retrofit2.Callback

class UserRepository(
    private val apiService: UserApiService = NetworkModule.apiService
) {
    fun fetchUsers(callback: Callback<List<User>>): Call<List<User>> {
        val call = apiService.getUsers()
        call.enqueue(callback)
        return call
    }
}
EOF

cat > app/src/main/java/com/example/usersapp/UsersAdapter.kt <<'EOF'
package com.example.usersapp

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class UsersAdapter : RecyclerView.Adapter<UsersAdapter.UserViewHolder>() {

    private val items = mutableListOf<User>()

    fun submitList(users: List<User>) {
        items.clear()
        items.addAll(users)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): UserViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_user, parent, false)
        return UserViewHolder(view)
    }

    override fun onBindViewHolder(holder: UserViewHolder, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size

    class UserViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val nameText: TextView = itemView.findViewById(R.id.nameText)
        private val usernameText: TextView = itemView.findViewById(R.id.usernameText)
        private val emailText: TextView = itemView.findViewById(R.id.emailText)

        fun bind(user: User) {
            nameText.text = user.name?.ifBlank { null } ?: itemView.context.getString(R.string.unknown_name)
            usernameText.text = user.username?.ifBlank { null } ?: itemView.context.getString(R.string.unknown_username)
            emailText.text = user.email?.ifBlank { null } ?: itemView.context.getString(R.string.unknown_email)
        }
    }
}
EOF

cat > app/src/main/res/layout/activity_main.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:gravity="center_horizontal"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:id="@+id/titleText"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginBottom="8dp"
        android:text="@string/app_name"
        android:textAppearance="@style/TextAppearance.AppCompat.Large"
        android:textStyle="bold" />

    <TextView
        android:id="@+id/statusText"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginBottom="16dp"
        android:text="@string/loading"
        android:textAppearance="@style/TextAppearance.AppCompat.Body1" />

    <ProgressBar
        android:id="@+id/progressBar"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginBottom="16dp" />

    <Button
        android:id="@+id/retryButton"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginBottom="16dp"
        android:text="@string/retry"
        android:visibility="gone" />

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/usersRecyclerView"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:clipToPadding="false"
        android:paddingBottom="16dp"
        android:visibility="gone" />

</LinearLayout>
EOF

cat > app/src/main/res/layout/item_user.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:layout_marginBottom="12dp"
    android:background="@drawable/user_item_background"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:id="@+id/nameText"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:textAppearance="@style/TextAppearance.AppCompat.Medium"
        android:textStyle="bold" />

    <TextView
        android:id="@+id/usernameText"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="4dp"
        android:textAppearance="@style/TextAppearance.AppCompat.Body1" />

    <TextView
        android:id="@+id/emailText"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="4dp"
        android:autoLink="email"
        android:textAppearance="@style/TextAppearance.AppCompat.Body2" />

</LinearLayout>
EOF

cat > app/src/main/res/drawable/ic_launcher.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <corners android:radius="12dp" />
    <solid android:color="#3F51B5" />
</shape>
EOF

cat > app/src/main/res/drawable/user_item_background.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <corners android:radius="12dp" />
    <solid android:color="#FFF3F4F6" />
    <stroke
        android:width="1dp"
        android:color="#FFD1D5DB" />
</shape>
EOF

cat > app/src/main/res/values/colors.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">#3F51B5</color>
    <color name="primary_dark">#303F9F</color>
    <color name="background">#FFFFFF</color>
</resources>
EOF

cat > app/src/main/res/values/strings.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Users</string>
    <string name="loading">Loading users...</string>
    <string name="retry">Retry</string>
    <string name="empty_state">No users returned yet.</string>
    <string name="environment_label">Environment: %1$s</string>
    <string name="error_message">Couldn&apos;t load users: %1$s</string>
    <string name="error_http">Request failed with HTTP %1$d</string>
    <string name="error_generic">Unexpected error</string>
    <string name="unknown_name">Unknown name</string>
    <string name="unknown_username">@unknown</string>
    <string name="unknown_email">No email</string>
</resources>
EOF

cat > app/src/main/res/values/themes.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.UsersApp" parent="Theme.AppCompat.Light.NoActionBar">
        <item name="colorPrimary">@color/primary</item>
        <item name="colorPrimaryDark">@color/primary_dark</item>
        <item name="android:statusBarColor">@color/primary_dark</item>
        <item name="android:navigationBarColor">@color/background</item>
    </style>
</resources>
EOF