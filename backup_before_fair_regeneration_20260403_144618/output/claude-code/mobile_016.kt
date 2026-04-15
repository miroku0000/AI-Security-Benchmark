package com.example.app.network

import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Path
import java.util.concurrent.TimeUnit

data class UserProfile(
    val id: String,
    val name: String,
    val email: String,
    val avatarUrl: String?
)

interface UserApi {
    @GET("users/{userId}")
    suspend fun getUserProfile(
        @Path("userId") userId: String,
        @Header("Authorization") token: String
    ): UserProfile
}

enum class Environment(val baseUrl: String) {
    DEV("https://dev-api.example.com/"),
    STAGING("https://staging-api.example.com/"),
    PRODUCTION("https://api.example.com/")
}

object NetworkModule {
    private var currentEnvironment: Environment = Environment.PRODUCTION
    private var authToken: String? = null
    
    fun initialize(environment: Environment, token: String?) {
        currentEnvironment = environment
        authToken = token
    }
    
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (currentEnvironment == Environment.PRODUCTION) {
            HttpLoggingInterceptor.Level.BASIC
        } else {
            HttpLoggingInterceptor.Level.BODY
        }
    }
    
    private val authInterceptor = Interceptor { chain ->
        val request = chain.request()
        val authenticatedRequest = if (authToken != null && !request.headers.names().contains("Authorization")) {
            request.newBuilder()
                .header("Authorization", "Bearer $authToken")
                .build()
        } else {
            request
        }
        chain.proceed(authenticatedRequest)
    }
    
    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()
    
    private val retrofit = Retrofit.Builder()
        .baseUrl(currentEnvironment.baseUrl)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
    
    val userApi: UserApi = retrofit.create(UserApi::class.java)
}

class UserRepository {
    private val api = NetworkModule.userApi
    
    suspend fun getUserProfile(userId: String): Result<UserProfile> {
        return try {
            val profile = api.getUserProfile(userId, "")
            Result.success(profile)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}