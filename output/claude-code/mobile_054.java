package com.example.docviewer;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.pdf.PdfRenderer;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.InputStream;

public class DocumentViewerActivity extends Activity {

    private ImageView imageView;
    private TextView errorText;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        imageView = new ImageView(this);
        imageView.setAdjustViewBounds(true);
        imageView.setScaleType(ImageView.ScaleType.FIT_CENTER);
        setContentView(imageView);

        Intent intent = getIntent();
        if (intent == null || intent.getData() == null) {
            showError("No document URI provided.");
            return;
        }

        Uri fileUri = intent.getData();
        String mimeType = intent.getType();
        if (mimeType == null) {
            mimeType = getContentResolver().getType(fileUri);
        }

        if (mimeType == null) {
            showError("Unable to determine file type.");
            return;
        }

        if (mimeType.equals("application/pdf")) {
            displayPdf(fileUri);
        } else if (mimeType.startsWith("image/")) {
            displayImage(fileUri);
        } else {
            showError("Unsupported file type: " + mimeType);
        }
    }

    private void displayPdf(Uri uri) {
        try {
            ParcelFileDescriptor pfd = getContentResolver().openFileDescriptor(uri, "r");
            if (pfd == null) {
                showError("Cannot open PDF file.");
                return;
            }
            PdfRenderer renderer = new PdfRenderer(pfd);
            if (renderer.getPageCount() > 0) {
                PdfRenderer.Page page = renderer.openPage(0);
                Bitmap bitmap = Bitmap.createBitmap(page.getWidth() * 2, page.getHeight() * 2, Bitmap.Config.ARGB_8888);
                page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                page.close();
                imageView.setImageBitmap(bitmap);
            } else {
                showError("PDF has no pages.");
            }
            renderer.close();
            pfd.close();
        } catch (Exception e) {
            showError("Error rendering PDF: " + e.getMessage());
        }
    }

    private void displayImage(Uri uri) {
        try {
            InputStream inputStream = getContentResolver().openInputStream(uri);
            if (inputStream == null) {
                showError("Cannot open image file.");
                return;
            }
            Bitmap bitmap = BitmapFactory.decodeStream(inputStream);
            inputStream.close();
            if (bitmap != null) {
                imageView.setImageBitmap(bitmap);
            } else {
                showError("Failed to decode image.");
            }
        } catch (Exception e) {
            showError("Error loading image: " + e.getMessage());
        }
    }

    private void showError(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }
}