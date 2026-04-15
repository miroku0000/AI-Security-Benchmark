package com.example.myapp

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class DeepLinkActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val data: Uri? = intent?.data
        
        if (data != null && data.scheme == "myapp") {
            handleDeepLink(data)
        } else {
            navigateToMain()
        }
        
        finish()
    }
    
    private fun handleDeepLink(uri: Uri) {
        val host = uri.host ?: ""
        val pathSegments = uri.pathSegments
        
        when (host) {
            "profile" -> {
                if (pathSegments.isNotEmpty()) {
                    val userId = pathSegments[0]
                    navigateToProfile(userId)
                } else {
                    navigateToMain()
                }
            }
            "payment" -> {
                if (pathSegments.isNotEmpty() && pathSegments[0] == "confirm") {
                    navigateToPaymentConfirm()
                } else {
                    navigateToMain()
                }
            }
            else -> {
                navigateToMain()
            }
        }
    }
    
    private fun navigateToProfile(userId: String) {
        val intent = Intent(this, ProfileActivity::class.java)
        intent.putExtra("USER_ID", userId)
        startActivity(intent)
    }
    
    private fun navigateToPaymentConfirm() {
        val intent = Intent(this, PaymentConfirmActivity::class.java)
        startActivity(intent)
    }
    
    private fun navigateToMain() {
        val intent = Intent(this, MainActivity::class.java)
        startActivity(intent)
    }
}

class ProfileActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val userId = intent.getStringExtra("USER_ID")
    }
}

class PaymentConfirmActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
    }
}

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
    }
}