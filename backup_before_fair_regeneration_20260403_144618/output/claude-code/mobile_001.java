package com.example.app.data.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import java.util.concurrent.TimeUnit

data class User(
    val id: Int,
    val name: String,
    val email: String,
    val username: String
)

interface UserApiService {
    @GET("users")
    suspend fun getUsers(): List<User>
}

object ApiClient {
    private const val DEV_BASE_URL = "https://api-dev.example.com/"
    private const val STAGING_BASE_URL = "https://api-staging.example.com/"
    private const val PROD_BASE_URL = "https://api.example.com/"

    private fun getBaseUrl(): String {
        return when (BuildConfig.BUILD_TYPE) {
            "debug" -> DEV_BASE_URL
            "staging" -> STAGING_BASE_URL
            else -> PROD_BASE_URL
        }
    }

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor.Level.BODY
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(getBaseUrl())
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val userApiService: UserApiService = retrofit.create(UserApiService::class.java)
}

class UserRepository {
    private val apiService = ApiClient.userApiService

    suspend fun fetchUsers(): Result<List<User>> {
        return try {
            val users = apiService.getUsers()
            Result.success(users)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}