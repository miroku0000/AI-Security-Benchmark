package com.example.users.network

import com.example.users.model.User
import retrofit2.http.GET

interface UsersApi {
    @GET("users")
    suspend fun listUsers(): List<User>
}

