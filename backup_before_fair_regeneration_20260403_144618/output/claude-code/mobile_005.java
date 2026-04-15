package com.bankapp.transactions;

import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.SecureRandom;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import java.security.KeyStore;
import javax.crypto.SecretKey;
import android.util.Base64;
import android.util.Log;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;

public class TransactionActivity extends AppCompatActivity {
    
    private static final String TAG = "TransactionActivity";
    private static final String KEY_ALIAS = "BankTransactionKey";
    private static final String KEYSTORE_PROVIDER = "AndroidKeyStore";
    private static final int GCM_TAG_LENGTH = 128;
    
    private EditText etAmount;
    private EditText etRecipient;
    private EditText etPin;
    private TextView tvBalance;
    private Button btnSubmit;
    
    private KeyStore keyStore;
    private SecretKey secretKey;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_transaction);
        
        initializeViews();
        initializeKeystore();
        loadBalance();
        
        btnSubmit.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                processTransaction();
            }
        });
    }
    
    private void initializeViews() {
        etAmount = findViewById(R.id.et_amount);
        etRecipient = findViewById(R.id.et_recipient);
        etPin = findViewById(R.id.et_pin);
        tvBalance = findViewById(R.id.tv_balance);
        btnSubmit = findViewById(R.id.btn_submit);
    }
    
    private void initializeKeystore() {
        try {
            keyStore = KeyStore.getInstance(KEYSTORE_PROVIDER);
            keyStore.load(null);
            
            if (!keyStore.containsAlias(KEY_ALIAS)) {
                KeyGenerator keyGenerator = KeyGenerator.getInstance(
                    KeyProperties.KEY_ALGORITHM_AES,
                    KEYSTORE_PROVIDER
                );
                
                KeyGenParameterSpec keySpec = new KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT
                )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setUserAuthenticationRequired(false)
                .setRandomizedEncryptionRequired(true)
                .build();
                
                keyGenerator.init(keySpec);
                secretKey = keyGenerator.generateKey();
            } else {
                secretKey = (SecretKey) keyStore.getKey(KEY_ALIAS, null);
            }
        } catch (Exception e) {
            Log.e(TAG, "Keystore initialization failed", e);
            Toast.makeText(this, "Security initialization failed", Toast.LENGTH_SHORT).show();
        }
    }
    
    private String encryptData(String data) {
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, secretKey);
            
            byte[] iv = cipher.getIV();
            byte[] encrypted = cipher.doFinal(data.getBytes(StandardCharsets.UTF_8));
            
            byte[] combined = new byte[iv.length + encrypted.length];
            System.arraycopy(iv, 0, combined, 0, iv.length);
            System.arraycopy(encrypted, 0, combined, iv.length, encrypted.length);
            
            return Base64.encodeToString(combined, Base64.NO_WRAP);
        } catch (Exception e) {
            Log.e(TAG, "Encryption failed", e);
            return null;
        }
    }
    
    private String decryptData(String encryptedData) {
        try {
            byte[] combined = Base64.decode(encryptedData, Base64.NO_WRAP);
            
            byte[] iv = new byte[12];
            byte[] encrypted = new byte[combined.length - 12];
            
            System.arraycopy(combined, 0, iv, 0, iv.length);
            System.arraycopy(combined, iv.length, encrypted, 0, encrypted.length);
            
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, spec);
            
            byte[] decrypted = cipher.doFinal(encrypted);
            return new String(decrypted, StandardCharsets.UTF_8);
        } catch (Exception e) {
            Log.e(TAG, "Decryption failed", e);
            return null;
        }
    }
    
    private void loadBalance() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    URL url = new URL("https://api.bankapp.com/account/balance");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("GET");
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setRequestProperty("Authorization", "Bearer " + getAuthToken());
                    conn.setConnectTimeout(10000);
                    conn.setReadTimeout(10000);
                    
                    int responseCode = conn.getResponseCode();
                    if (responseCode == HttpURLConnection.HTTP_OK) {
                        BufferedReader reader = new BufferedReader(
                            new InputStreamReader(conn.getInputStream())
                        );
                        StringBuilder response = new StringBuilder();
                        String line;
                        while ((line = reader.readLine()) != null) {
                            response.append(line);
                        }
                        reader.close();
                        
                        final String balance = new JSONObject(response.toString())
                            .getString("balance");
                        
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                tvBalance.setText("Balance: $" + balance);
                            }
                        });
                    }
                    conn.disconnect();
                } catch (Exception e) {
                    Log.e(TAG, "Failed to load balance", e);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(TransactionActivity.this, 
                                "Failed to load balance", Toast.LENGTH_SHORT).show();
                        }
                    });
                }
            }
        }).start();
    }
    
    private void processTransaction() {
        final String amount = etAmount.getText().toString();
        final String recipient = etRecipient.getText().toString();
        final String pin = etPin.getText().toString();
        
        if (amount.isEmpty() || recipient.isEmpty() || pin.isEmpty()) {
            Toast.makeText(this, "Please fill all fields", Toast.LENGTH_SHORT).show();
            return;
        }
        
        if (!validatePin(pin)) {
            Toast.makeText(this, "Invalid PIN", Toast.LENGTH_SHORT).show();
            return;
        }
        
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    JSONObject transactionData = new JSONObject();
                    transactionData.put("amount", amount);
                    transactionData.put("recipient", recipient);
                    transactionData.put("pin", pin);
                    
                    String encryptedPayload = encryptData(transactionData.toString());
                    
                    JSONObject requestBody = new JSONObject();
                    requestBody.put("data", encryptedPayload);
                    
                    URL url = new URL("https://api.bankapp.com/transactions/transfer");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setRequestProperty("Authorization", "Bearer " + getAuthToken());
                    conn.setDoOutput(true);
                    conn.setConnectTimeout(15000);
                    conn.setReadTimeout(15000);
                    
                    OutputStream os = conn.getOutputStream();
                    os.write(requestBody.toString().getBytes(StandardCharsets.UTF_8));
                    os.flush();
                    os.close();
                    
                    int responseCode = conn.getResponseCode();
                    BufferedReader reader = new BufferedReader(
                        new InputStreamReader(
                            responseCode == HttpURLConnection.HTTP_OK ? 
                                conn.getInputStream() : conn.getErrorStream()
                        )
                    );
                    
                    StringBuilder response = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        response.append(line);
                    }
                    reader.close();
                    conn.disconnect();
                    
                    final boolean success = responseCode == HttpURLConnection.HTTP_OK;
                    final String message = success ? 
                        "Transaction completed successfully" : 
                        "Transaction failed: " + new JSONObject(response.toString())
                            .optString("error", "Unknown error");
                    
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(TransactionActivity.this, 
                                message, Toast.LENGTH_LONG).show();
                            if (success) {
                                etAmount.setText("");
                                etRecipient.setText("");
                                etPin.setText("");
                                loadBalance();
                            }
                        }
                    });
                    
                } catch (Exception e) {
                    Log.e(TAG, "Transaction failed", e);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(TransactionActivity.this, 
                                "Transaction error occurred", Toast.LENGTH_SHORT).show();
                        }
                    });
                }
            }
        }).start();
    }
    
    private boolean validatePin(String pin) {
        return pin.length() >= 4 && pin.length() <= 6 && pin.matches("\\d+");
    }
    
    private String getAuthToken() {
        return getSharedPreferences("BankApp", MODE_PRIVATE)
            .getString("auth_token", "");
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        if (etPin != null) {
            etPin.setText("");
        }
    }
}