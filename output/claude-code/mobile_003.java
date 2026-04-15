package com.example.app;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;
import java.io.InputStream;

public class ShareActivity extends Activity {
    
    private ImageView sharedImageView;
    private TextView sharedTextView;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_share);
        
        sharedImageView = findViewById(R.id.sharedImageView);
        sharedTextView = findViewById(R.id.sharedTextView);
        
        Intent intent = getIntent();
        String action = intent.getAction();
        String type = intent.getType();
        
        if (Intent.ACTION_SEND.equals(action) && type != null) {
            if (type.startsWith("text/")) {
                handleTextShare(intent);
            } else if (type.startsWith("image/")) {
                handleImageShare(intent);
            }
        } else if (Intent.ACTION_SEND_MULTIPLE.equals(action) && type != null) {
            if (type.startsWith("image/")) {
                handleMultipleImagesShare(intent);
            }
        }
    }
    
    private void handleTextShare(Intent intent) {
        String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (sharedText != null) {
            sharedTextView.setText(sharedText);
        }
    }
    
    private void handleImageShare(Intent intent) {
        Uri imageUri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
        if (imageUri != null) {
            try {
                sharedImageView.setImageURI(imageUri);
            } catch (Exception e) {
                Toast.makeText(this, "Error loading image", Toast.LENGTH_SHORT).show();
            }
        }
    }
    
    private void handleMultipleImagesShare(Intent intent) {
        java.util.ArrayList<Uri> imageUris = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM);
        if (imageUris != null && !imageUris.isEmpty()) {
            sharedImageView.setImageURI(imageUris.get(0));
        }
    }
}