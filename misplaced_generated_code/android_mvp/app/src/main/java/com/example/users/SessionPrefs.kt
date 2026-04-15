package com.example.users

import android.content.Context

object SessionPrefs {
    private const val PREFS_NAME = "session_prefs"
    private const val KEY_EMAIL = "email"
    private const val KEY_TOKEN = "auth_token"
    private const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
    private const val KEY_AUTHENTICATED = "is_authenticated"

    fun getEmail(context: Context): String? =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_EMAIL, null)

    fun getToken(context: Context): String? =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_TOKEN, null)

    fun isLoggedIn(context: Context): Boolean = !getToken(context).isNullOrBlank()

    fun isAuthenticated(context: Context): Boolean =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_AUTHENTICATED, false)

    fun setAuthenticated(context: Context, authenticated: Boolean) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_AUTHENTICATED, authenticated)
            .apply()
    }

    fun isBiometricEnabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_BIOMETRIC_ENABLED, false)

    fun setBiometricEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_BIOMETRIC_ENABLED, enabled)
            .apply()
    }

    fun saveSession(context: Context, email: String, token: String) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_EMAIL, email)
            .putString(KEY_TOKEN, token)
            .putBoolean(KEY_AUTHENTICATED, true)
            .apply()
    }

    fun clearSession(context: Context) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_EMAIL)
            .remove(KEY_TOKEN)
            .remove(KEY_AUTHENTICATED)
            .apply()
    }

    fun clearAll(context: Context) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_EMAIL)
            .remove(KEY_TOKEN)
            .remove(KEY_BIOMETRIC_ENABLED)
            .remove(KEY_AUTHENTICATED)
            .apply()
    }
}

