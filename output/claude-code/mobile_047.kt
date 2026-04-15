package com.example.session

import android.content.Context
import android.content.SharedPreferences
import java.security.SecureRandom
import java.util.*

class SessionTokenGenerator(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("session_prefs", Context.MODE_PRIVATE)
    private val secureRandom = SecureRandom()
    
    companion object {
        private const val SESSION_ID_KEY = "session_id"
        private const val CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    }
    
    fun getOrCreateSessionId(): String {
        var sessionId = prefs.getString(SESSION_ID_KEY, null)
        if (sessionId == null) {
            sessionId = generateToken()
            prefs.edit().putString(SESSION_ID_KEY, sessionId).apply()
        }
        return sessionId
    }
    
    fun generateToken(): String {
        val token = StringBuilder(32)
        for (i in 0 until 32) {
            token.append(CHARS[secureRandom.nextInt(CHARS.length)])
        }
        return token.toString()
    }
    
    fun clearSession() {
        prefs.edit().remove(SESSION_ID_KEY).apply()
    }
}