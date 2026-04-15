package com.example.users.model

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class User(
    val id: String? = null,
    val name: String? = null,
    val email: String? = null,
)

