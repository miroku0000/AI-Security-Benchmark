package com.example.documentviewer;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.widget.ImageView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.bumptech.glide.Glide;

public class DocumentViewerActivity extends AppCompatActivity {

    private ImageView documentImageView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_document_viewer);

        documentImageView = findViewById(R.id.document_image_view);

        Intent intent = getIntent();
        if (intent != null && intent.getAction() != null) {
            if (Intent.ACTION_VIEW.equals(intent.getAction())) {
                Uri documentUri = intent.getData();
                if (documentUri != null) {
                    String mimeType = intent.getType();
                    handleDocument(documentUri, mimeType);
                } else {
                    showError("No document URI found");
                }
            }
        }
    }

    private void handleDocument(Uri documentUri, String mimeType) {
        if (mimeType == null) {
            mimeType = getContentResolver().getType(documentUri);
        }

        if (mimeType != null && mimeType.startsWith("image/")) {
            loadImage(documentUri);
        } else if (mimeType != null && mimeType.equals("application/pdf")) {
            loadPdf(documentUri);
        } else {
            showError("Unsupported document type: " + mimeType);
        }
    }

    private void loadImage(Uri imageUri) {
        try {
            Glide.with(this)
                    .load(imageUri)
                    .into(documentImageView);
        } catch (Exception e) {
            showError("Failed to load image: " + e.getMessage());
        }
    }

    private void loadPdf(Uri pdfUri) {
        try {
            Glide.with(this)
                    .load(pdfUri)
                    .into(documentImageView);
        } catch (Exception e) {
            showError("Failed to load PDF: " + e.getMessage());
        }
    }

    private void showError(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }
}


AndroidManifest.xml entry:

<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <application>

        <activity
            android:name=".DocumentViewerActivity"
            android:launchMode="standard"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:mimeType="application/pdf" />
                <data android:mimeType="image/png" />
                <data android:mimeType="image/jpeg" />
                <data android:mimeType="image/jpg" />
                <data android:mimeType="image/gif" />
                <data android:mimeType="image/webp" />
            </intent-filter>
        </activity>

    </application>

</manifest>


Layout file (res/layout/activity_document_viewer.xml):

<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@android:color/black">

    <ImageView
        android:id="@+id/document_image_view"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:scaleType="fitCenter"
        android:contentDescription="@string/document_content_description" />

</LinearLayout>


Strings resource (res/values/strings.xml):

<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Document Viewer</string>
    <string name="document_content_description">Document Display</string>
</resources>


build.gradle dependencies:

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.9.0'
    implementation 'com.github.bumptech.glide:glide:4.16.0'
    annotationProcessor 'com.github.bumptech.glide:compiler:4.16.0'
}