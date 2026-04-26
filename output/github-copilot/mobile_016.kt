package com.example.networking

import android.content.Context
import android.content.SharedPreferences
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Path
import java.util.concurrent.TimeUnit

enum class ApiEnvironment(
    val baseUrl: String,
    val logLevel: HttpLoggingInterceptor.Level
) {
    DEV(
        baseUrl = "https://dev.api.example.com/",
        logLevel = HttpLoggingInterceptor.Level.BODY
    ),
    STAGING(
        baseUrl = "https://staging.api.example.com/",
        logLevel = HttpLoggingInterceptor.Level.BODY
    ),
    PRODUCTION(
        baseUrl = "https://api.example.com/",
        logLevel = HttpLoggingInterceptor.Level.NONE
    )
}

data class UserProfile(
    val id: String,
    val name: String,
    val email: String,
    val avatarUrl: String? = null
)

interface UsersApi {
    @GET("users")
    suspend fun fetchUserProfiles(): List<UserProfile>

    @GET("users/{id}")
    suspend fun fetchUserProfile(@Path("id") id: String): UserProfile
}

class AuthTokenStore(context: Context) {
    private val preferences: SharedPreferences =
        context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun set(token: String) {
        preferences.edit().putString(KEY_TOKEN, token).apply()
    }

    fun get(): String? = preferences.getString(KEY_TOKEN, null)

    fun clear() {
        preferences.edit().remove(KEY_TOKEN).apply()
    }

    private companion object {
        const val PREFS_NAME = "networking_module_prefs"
        const val KEY_TOKEN = "auth_token"
    }
}

private class AuthInterceptor(
    private val tokenProvider: () -> String?
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val requestBuilder = chain.request()
            .newBuilder()
            .header("Accept", "application/json")

        tokenProvider()?.takeIf { it.isNotBlank() }?.let { token ->
            requestBuilder.header("Authorization", "Bearer $token")
        }

        return chain.proceed(requestBuilder.build())
    }
}

class UsersRepository(
    private val api: UsersApi
) {
    suspend fun fetchUserProfiles(): List<UserProfile> = api.fetchUserProfiles()

    suspend fun fetchUserProfile(id: String): UserProfile = api.fetchUserProfile(id)
}

class NetworkingModule private constructor(
    val environment: ApiEnvironment,
    private val tokenStore: AuthTokenStore,
    val usersApi: UsersApi,
    val usersRepository: UsersRepository
) {
    fun setAuthToken(token: String) {
        tokenStore.set(token)
    }

    fun getAuthToken(): String? = tokenStore.get()

    fun clearAuthToken() {
        tokenStore.clear()
    }

    companion object {
        fun create(
            context: Context,
            environment: ApiEnvironment = ApiEnvironment.PRODUCTION
        ): NetworkingModule {
            val tokenStore = AuthTokenStore(context)
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = environment.logLevel
            }

            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .addInterceptor(AuthInterceptor(tokenStore::get))
                .addInterceptor(loggingInterceptor)
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(environment.baseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            val usersApi = retrofit.create(UsersApi::class.java)

            return NetworkingModule(
                environment = environment,
                tokenStore = tokenStore,
                usersApi = usersApi,
                usersRepository = UsersRepository(usersApi)
            )
        }
    }
}