package com.example.app;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import java.util.concurrent.Executor;

public class BiometricAuthActivity extends AppCompatActivity {

    private static final String PREFS_NAME = "BiometricPrefs";
    private static final String KEY_BIOMETRIC_ENABLED = "biometric_enabled";
    private static final String KEY_AUTH_STATUS = "auth_status";

    private BiometricPrompt biometricPrompt;
    private BiometricPrompt.PromptInfo promptInfo;
    private SharedPreferences sharedPreferences;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        sharedPreferences = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        
        if (isBiometricEnabled() && isAuthenticationValid()) {
            navigateToMainScreen();
            return;
        }
        
        if (isBiometricEnabled()) {
            setupBiometricAuthentication();
            showBiometricPrompt();
        }
    }

    private void setupBiometricAuthentication() {
        Executor executor = ContextCompat.getMainExecutor(this);
        
        biometricPrompt = new BiometricPrompt(this, executor, new BiometricPrompt.AuthenticationCallback() {
            @Override
            public void onAuthenticationError(int errorCode, @NonNull CharSequence errString) {
                super.onAuthenticationError(errorCode, errString);
                Toast.makeText(BiometricAuthActivity.this, "Authentication error: " + errString, Toast.LENGTH_SHORT).show();
            }

            @Override
            public void onAuthenticationSucceeded(@NonNull BiometricPrompt.AuthenticationResult result) {
                super.onAuthenticationSucceeded(result);
                saveAuthenticationStatus(true);
                Toast.makeText(BiometricAuthActivity.this, "Authentication succeeded", Toast.LENGTH_SHORT).show();
                navigateToMainScreen();
            }

            @Override
            public void onAuthenticationFailed() {
                super.onAuthenticationFailed();
                Toast.makeText(BiometricAuthActivity.this, "Authentication failed", Toast.LENGTH_SHORT).show();
            }
        });

        promptInfo = new BiometricPrompt.PromptInfo.Builder()
                .setTitle("Biometric Authentication")
                .setSubtitle("Log in using your fingerprint")
                .setNegativeButtonText("Use password")
                .build();
    }

    private void showBiometricPrompt() {
        BiometricManager biometricManager = BiometricManager.from(this);
        int canAuthenticate = biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG);
        
        if (canAuthenticate == BiometricManager.BIOMETRIC_SUCCESS) {
            biometricPrompt.authenticate(promptInfo);
        } else {
            Toast.makeText(this, "Biometric authentication not available", Toast.LENGTH_SHORT).show();
        }
    }

    public void enableBiometricLogin() {
        SharedPreferences.Editor editor = sharedPreferences.edit();
        editor.putBoolean(KEY_BIOMETRIC_ENABLED, true);
        editor.apply();
    }

    public void disableBiometricLogin() {
        SharedPreferences.Editor editor = sharedPreferences.edit();
        editor.putBoolean(KEY_BIOMETRIC_ENABLED, false);
        editor.remove(KEY_AUTH_STATUS);
        editor.apply();
    }

    private boolean isBiometricEnabled() {
        return sharedPreferences.getBoolean(KEY_BIOMETRIC_ENABLED, false);
    }

    private void saveAuthenticationStatus(boolean authenticated) {
        SharedPreferences.Editor editor = sharedPreferences.edit();
        editor.putBoolean(KEY_AUTH_STATUS, authenticated);
        editor.apply();
    }

    private boolean isAuthenticationValid() {
        return sharedPreferences.getBoolean(KEY_AUTH_STATUS, false);
    }

    private void navigateToMainScreen() {
        finish();
    }
}