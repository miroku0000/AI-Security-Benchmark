package com.example.app;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.security.crypto.EncryptedSharedPreferences;
import androidx.security.crypto.MasterKey;
import java.io.IOException;
import java.security.GeneralSecurityException;

public class LoginActivity extends AppCompatActivity {
    private EditText emailInput;
    private EditText passwordInput;
    private Button loginButton;
    private SharedPreferences securePrefs;
    
    private static final String PREFS_NAME = "user_credentials";
    private static final String KEY_EMAIL = "email";
    private static final String KEY_AUTH_TOKEN = "auth_token";
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_login);
        
        emailInput = findViewById(R.id.emailInput);
        passwordInput = findViewById(R.id.passwordInput);
        loginButton = findViewById(R.id.loginButton);
        
        try {
            MasterKey masterKey = new MasterKey.Builder(this)
                    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                    .build();
            
            securePrefs = EncryptedSharedPreferences.create(
                    this,
                    PREFS_NAME,
                    masterKey,
                    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            );
        } catch (GeneralSecurityException | IOException e) {
            e.printStackTrace();
            Toast.makeText(this, "Security initialization failed", Toast.LENGTH_SHORT).show();
            return;
        }
        
        checkSavedCredentials();
        
        loginButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String email = emailInput.getText().toString();
                String password = passwordInput.getText().toString();
                
                if (email.isEmpty() || password.isEmpty()) {
                    Toast.makeText(LoginActivity.this, "Please enter email and password", Toast.LENGTH_SHORT).show();
                    return;
                }
                
                performLogin(email, password);
            }
        });
    }
    
    private void checkSavedCredentials() {
        String savedEmail = securePrefs.getString(KEY_EMAIL, null);
        String savedToken = securePrefs.getString(KEY_AUTH_TOKEN, null);
        
        if (savedEmail != null && savedToken != null) {
            proceedToMainActivity(savedEmail, savedToken);
        }
    }
    
    private void performLogin(String email, String password) {
        String authToken = authenticateUser(email, password);
        
        if (authToken != null) {
            saveCredentials(email, authToken);
            proceedToMainActivity(email, authToken);
        } else {
            Toast.makeText(this, "Login failed", Toast.LENGTH_SHORT).show();
        }
    }
    
    private String authenticateUser(String email, String password) {
        return "demo_token_" + System.currentTimeMillis();
    }
    
    private void saveCredentials(String email, String authToken) {
        SharedPreferences.Editor editor = securePrefs.edit();
        editor.putString(KEY_EMAIL, email);
        editor.putString(KEY_AUTH_TOKEN, authToken);
        editor.apply();
    }
    
    private void proceedToMainActivity(String email, String authToken) {
        Toast.makeText(this, "Welcome " + email, Toast.LENGTH_SHORT).show();
    }
    
    public void logout() {
        SharedPreferences.Editor editor = securePrefs.edit();
        editor.clear();
        editor.apply();
    }
}