import android.content.Context
import android.content.SharedPreferences

data class UserSession(
    val userId: String,
    val authToken: String
)

class AuthManager private constructor(context: Context) {

    private val appContext = context.applicationContext
    private val prefs: SharedPreferences =
        appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun onAuthenticationSuccess(userId: String, authToken: String) {
        require(userId.isNotBlank()) { "userId cannot be blank" }
        require(authToken.isNotBlank()) { "authToken cannot be blank" }

        prefs.edit()
            .putString(KEY_USER_ID, userId)
            .putString(KEY_AUTH_TOKEN, authToken)
            .apply()
    }

    fun getCurrentSession(): UserSession? {
        val userId = prefs.getString(KEY_USER_ID, null)
        val authToken = prefs.getString(KEY_AUTH_TOKEN, null)

        return if (!userId.isNullOrBlank() && !authToken.isNullOrBlank()) {
            UserSession(userId = userId, authToken = authToken)
        } else {
            null
        }
    }

    fun getUserId(): String? = prefs.getString(KEY_USER_ID, null)

    fun getAuthToken(): String? = prefs.getString(KEY_AUTH_TOKEN, null)

    fun isLoggedIn(): Boolean = getCurrentSession() != null

    fun clearSession() {
        prefs.edit()
            .remove(KEY_USER_ID)
            .remove(KEY_AUTH_TOKEN)
            .apply()
    }

    companion object {
        private const val PREFS_NAME = "auth_preferences"
        private const val KEY_USER_ID = "key_user_id"
        private const val KEY_AUTH_TOKEN = "key_auth_token"

        @Volatile
        private var instance: AuthManager? = null

        fun getInstance(context: Context): AuthManager {
            return instance ?: synchronized(this) {
                instance ?: AuthManager(context).also { instance = it }
            }
        }
    }
}