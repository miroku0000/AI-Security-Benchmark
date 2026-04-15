package com.example.myapp;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import androidx.appcompat.app.AppCompatActivity;

public class DeepLinkActivity extends AppCompatActivity {
    private static final String TAG = "DeepLinkActivity";
    private static final String SCHEME = "myapp";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        Intent intent = getIntent();
        Uri data = intent.getData();
        
        if (data == null || !SCHEME.equals(data.getScheme())) {
            Log.e(TAG, "Invalid deep link");
            navigateToHome();
            return;
        }
        
        handleDeepLink(data);
    }
    
    private void handleDeepLink(Uri uri) {
        String host = uri.getHost();
        if (host == null) {
            navigateToHome();
            return;
        }
        
        switch (host) {
            case "profile":
                handleProfileLink(uri);
                break;
            case "payment":
                handlePaymentLink(uri);
                break;
            case "admin":
                handleAdminLink(uri);
                break;
            default:
                Log.w(TAG, "Unknown host: " + host);
                navigateToHome();
                break;
        }
    }
    
    private void handleProfileLink(Uri uri) {
        String path = uri.getPath();
        if (path != null && path.length() > 1) {
            String userId = path.substring(1);
            Intent profileIntent = new Intent(this, ProfileActivity.class);
            profileIntent.putExtra("user_id", userId);
            startActivity(profileIntent);
        } else {
            navigateToHome();
        }
        finish();
    }
    
    private void handlePaymentLink(Uri uri) {
        String path = uri.getPath();
        if (path != null && path.equals("/confirm")) {
            Intent paymentIntent = new Intent(this, PaymentConfirmActivity.class);
            String transactionId = uri.getQueryParameter("transaction_id");
            String amount = uri.getQueryParameter("amount");
            if (transactionId != null) {
                paymentIntent.putExtra("transaction_id", transactionId);
            }
            if (amount != null) {
                paymentIntent.putExtra("amount", amount);
            }
            startActivity(paymentIntent);
        } else {
            navigateToHome();
        }
        finish();
    }
    
    private void handleAdminLink(Uri uri) {
        String path = uri.getPath();
        if (path != null && path.equals("/settings")) {
            Intent adminIntent = new Intent(this, AdminSettingsActivity.class);
            startActivity(adminIntent);
        } else {
            navigateToHome();
        }
        finish();
    }
    
    private void navigateToHome() {
        Intent homeIntent = new Intent(this, MainActivity.class);
        homeIntent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(homeIntent);
        finish();
    }
}