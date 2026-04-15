package com.example.documentviewer;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.pdf.PdfRenderer;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.util.Log;
import android.widget.ImageView;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.LinearLayout;
import android.widget.Toast;
import java.io.FileDescriptor;
import java.io.IOException;
import java.io.InputStream;

public class DocumentViewerActivity extends Activity {
    private static final String TAG = "DocumentViewer";
    private ImageView imageView;
    private TextView errorText;
    private LinearLayout container;
    private PdfRenderer pdfRenderer;
    private ParcelFileDescriptor parcelFileDescriptor;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        ScrollView scrollView = new ScrollView(this);
        container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        
        imageView = new ImageView(this);
        errorText = new TextView(this);
        errorText.setPadding(20, 20, 20, 20);
        errorText.setTextSize(16);
        
        container.addView(imageView);
        container.addView(errorText);
        scrollView.addView(container);
        setContentView(scrollView);
        
        Intent intent = getIntent();
        String action = intent.getAction();
        String type = intent.getType();
        
        if (Intent.ACTION_VIEW.equals(action) && type != null) {
            Uri uri = intent.getData();
            if (uri != null) {
                handleDocument(uri, type);
            } else {
                showError("No document URI provided");
            }
        } else {
            showError("Invalid intent action or type");
        }
    }
    
    private void handleDocument(Uri uri, String mimeType) {
        Log.d(TAG, "Handling document: " + uri.toString() + " with type: " + mimeType);
        
        try {
            if (mimeType.equals("application/pdf")) {
                displayPdf(uri);
            } else if (mimeType.startsWith("image/")) {
                displayImage(uri);
            } else {
                showError("Unsupported document type: " + mimeType);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error handling document", e);
            showError("Failed to open document: " + e.getMessage());
        }
    }
    
    private void displayPdf(Uri uri) throws IOException {
        parcelFileDescriptor = getContentResolver().openFileDescriptor(uri, "r");
        if (parcelFileDescriptor != null) {
            pdfRenderer = new PdfRenderer(parcelFileDescriptor);
            if (pdfRenderer.getPageCount() > 0) {
                PdfRenderer.Page page = pdfRenderer.openPage(0);
                
                Bitmap bitmap = Bitmap.createBitmap(
                    page.getWidth() * 2,
                    page.getHeight() * 2, 
                    Bitmap.Config.ARGB_8888
                );
                
                page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                page.close();
                
                imageView.setImageBitmap(bitmap);
                Toast.makeText(this, "PDF loaded (page 1 of " + pdfRenderer.getPageCount() + ")", Toast.LENGTH_SHORT).show();
            }
        } else {
            showError("Could not open PDF file");
        }
    }
    
    private void displayImage(Uri uri) throws IOException {
        InputStream inputStream = getContentResolver().openInputStream(uri);
        if (inputStream != null) {
            Bitmap bitmap = BitmapFactory.decodeStream(inputStream);
            inputStream.close();
            
            if (bitmap != null) {
                imageView.setImageBitmap(bitmap);
                Toast.makeText(this, "Image loaded successfully", Toast.LENGTH_SHORT).show();
            } else {
                showError("Failed to decode image");
            }
        } else {
            showError("Could not open image file");
        }
    }
    
    private void showError(String message) {
        errorText.setText(message);
        imageView.setVisibility(ImageView.GONE);
        errorText.setVisibility(TextView.VISIBLE);
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (pdfRenderer != null) {
            pdfRenderer.close();
        }
        if (parcelFileDescriptor != null) {
            try {
                parcelFileDescriptor.close();
            } catch (IOException e) {
                Log.e(TAG, "Error closing file descriptor", e);
            }
        }
    }
}