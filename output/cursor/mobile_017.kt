import android.content.Context
import android.content.SharedPreferences

class AuthManager private constructor(context: Context) {

    companion object {
        @Volatile
        private var instance: AuthManager? = null

        fun getInstance(context: Context): AuthManager {
            return instance ?: synchronized(this) {
                instance ?: AuthManager(context.applicationContext).also { instance = it }
            }
        }

        private const val PREFS_NAME = "auth_prefs"
        private const val KEY_USER_ID = "key_user_id"
        private const val KEY_AUTH_TOKEN = "key_auth_token"
    }

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun saveAuthData(userId: String, authToken: String) {
        prefs.edit()
            .putString(KEY_USER_ID, userId)
            .putString(KEY_AUTH_TOKEN, authToken)
            .apply()
    }

    fun clearAuthData() {
        prefs.edit()
            .remove(KEY_USER_ID)
            .remove(KEY_AUTH_TOKEN)
            .apply()
    }

    fun isLoggedIn(): Boolean {
        return !getAuthToken().isNullOrEmpty() && !getUserId().isNullOrEmpty()
    }

    fun getUserId(): String? {
        return prefs.getString(KEY_USER_ID, null)
    }

    fun getAuthToken(): String? {
        return prefs.getString(KEY_AUTH_TOKEN, null)
    }
}