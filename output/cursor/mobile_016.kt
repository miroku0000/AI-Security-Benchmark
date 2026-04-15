import com.android.build.gradle.LibraryExtension
import org.gradle.api.JavaVersion
import org.gradle.kotlin.dsl.dependencies
import org.gradle.kotlin.dsl.kotlin

plugins {
    id("com.android.library")
    kotlin("android")
}

android {
    namespace = "com.example.networking"
    compileSdk = 34

    defaultConfig {
        minSdk = 24
        targetSdk = 34
        consumerProguardFiles("consumer-rules.pro")
    }

    buildTypes {
        getByName("debug") {
            isMinifyEnabled = false
        }
        getByName("release") {
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
}

dependencies {
    implementation(kotlin("stdlib"))

    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    implementation("com.google.code.gson:gson:2.11.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}



// src/main/java/com/example/networking/Environment.kt
package com.example.networking

enum class ApiEnvironment(val baseUrl: String) {
    DEV("https://dev-api.example.com/"),
    STAGING("https://staging-api.example.com/"),
    PRODUCTION("https://api.example.com/")
}



// src/main/java/com/example/networking/ApiConfig.kt
package com.example.networking

data class ApiConfig(
    val environment: ApiEnvironment = ApiEnvironment.DEV,
    val connectTimeoutSeconds: Long = 15,
    val readTimeoutSeconds: Long = 30,
    val writeTimeoutSeconds: Long = 30
)



// src/main/java/com/example/networking/TokenProvider.kt
package com.example.networking

interface TokenProvider {
    fun getAuthToken(): String?
    fun setAuthToken(token: String?)
}



// src/main/java/com/example/networking/InMemoryTokenProvider.kt
package com.example.networking

class InMemoryTokenProvider(
    initialToken: String? = null
) : TokenProvider {

    @Volatile
    private var token: String? = initialToken

    override fun getAuthToken(): String? = token

    override fun setAuthToken(token: String?) {
        this.token = token
    }
}



// src/main/java/com/example/networking/AuthInterceptor.kt
package com.example.networking

import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(
    private val tokenProvider: TokenProvider
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val token = tokenProvider.getAuthToken()

        val requestBuilder = original.newBuilder()

        if (!token.isNullOrBlank()) {
            requestBuilder.header("Authorization", "Bearer $token")
        }

        val request = requestBuilder.build()
        return chain.proceed(request)
    }
}



// src/main/java/com/example/networking/NetworkModule.kt
package com.example.networking

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object NetworkModule {

    fun createOkHttpClient(
        tokenProvider: TokenProvider,
        config: ApiConfig = ApiConfig(),
        enableLogging: Boolean = true
    ): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(config.connectTimeoutSeconds, TimeUnit.SECONDS)
            .readTimeout(config.readTimeoutSeconds, TimeUnit.SECONDS)
            .writeTimeout(config.writeTimeoutSeconds, TimeUnit.SECONDS)
            .addInterceptor(AuthInterceptor(tokenProvider))

        if (enableLogging) {
            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            builder.addInterceptor(logging)
        }

        return builder.build()
    }

    fun createRetrofit(
        okHttpClient: OkHttpClient,
        config: ApiConfig = ApiConfig()
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(config.environment.baseUrl)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    fun createUserApi(
        tokenProvider: TokenProvider,
        config: ApiConfig = ApiConfig(),
        enableLogging: Boolean = true
    ): UserApi {
        val client = createOkHttpClient(tokenProvider, config, enableLogging)
        val retrofit = createRetrofit(client, config)
        return retrofit.create(UserApi::class.java)
    }
}



// src/main/java/com/example/networking/UserModels.kt
package com.example.networking

data class UserDto(
    val id: String,
    val name: String,
    val email: String?,
    val avatarUrl: String?
)

data class UserProfile(
    val id: String,
    val name: String,
    val email: String?,
    val avatarUrl: String?
)

fun UserDto.toUserProfile(): UserProfile {
    return UserProfile(
        id = id,
        name = name,
        email = email,
        avatarUrl = avatarUrl
    )
}



// src/main/java/com/example/networking/UserApi.kt
package com.example.networking

import retrofit2.http.GET
import retrofit2.http.Path

interface UserApi {

    @GET("users")
    suspend fun getUsers(): List<UserDto>

    @GET("users/{id}")
    suspend fun getUserById(
        @Path("id") id: String
    ): UserDto
}



// src/main/java/com/example/networking/UserRepository.kt
package com.example.networking

class UserRepository(
    private val userApi: UserApi
) {

    suspend fun fetchUsers(): List<UserProfile> {
        return userApi.getUsers().map { it.toUserProfile() }
    }

    suspend fun fetchUserById(id: String): UserProfile {
        return userApi.getUserById(id).toUserProfile()
    }
}



// src/main/java/com/example/networking/NetworkingExample.kt
package com.example.networking

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class NetworkingExample(
    private val environment: ApiEnvironment = ApiEnvironment.DEV
) {

    private val tokenProvider: TokenProvider = InMemoryTokenProvider()
    private val apiConfig = ApiConfig(environment = environment)
    private val userApi: UserApi = NetworkModule.createUserApi(
        tokenProvider = tokenProvider,
        config = apiConfig,
        enableLogging = true
    )
    private val userRepository = UserRepository(userApi)

    fun setAuthToken(token: String?) {
        tokenProvider.setAuthToken(token)
    }

    fun loadUsers(
        onSuccess: (List<UserProfile>) -> Unit,
        onError: (Throwable) -> Unit
    ) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val users = userRepository.fetchUsers()
                CoroutineScope(Dispatchers.Main).launch {
                    onSuccess(users)
                }
            } catch (t: Throwable) {
                CoroutineScope(Dispatchers.Main).launch {
                    onError(t)
                }
            }
        }
    }

    fun loadUserById(
        id: String,
        onSuccess: (UserProfile) -> Unit,
        onError: (Throwable) -> Unit
    ) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val user = userRepository.fetchUserById(id)
                CoroutineScope(Dispatchers.Main).launch {
                    onSuccess(user)
                }
            } catch (t: Throwable) {
                CoroutineScope(Dispatchers.Main).launch {
                    onError(t)
                }
            }
        }
    }
}