package com.example.hybridmvp;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.SslErrorHandler;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

public class MainActivity extends Activity {
    private static final String INITIAL_URL = "https://m.example.com/";
    private static final Set<String> ALLOWED_HOSTS = new HashSet<String>(Arrays.asList(
            "m.example.com",
            "example.com",
            "static.example.com",
            "payments.example.com"
    ));

    private static final int REQUEST_CAMERA = 1001;
    private static final int REQUEST_PAYMENT = 1002;
    private static final int REQUEST_LOCATION_PERMISSION = 1003;
    private static final long LOCATION_TIMEOUT_MS = 15000L;

    private static final Pattern CALLBACK_ID_PATTERN = Pattern.compile("^[A-Za-z0-9_.-]{1,64}$");
    private static final Pattern UPI_ID_PATTERN = Pattern.compile("^[A-Za-z0-9._-]{2,256}@[A-Za-z]{2,64}$");

    private WebView webView;
    private LocationManager locationManager;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final String jsInterfaceName = "NativeBridge_" + UUID.randomUUID().toString().replace("-", "");

    private volatile String currentPageUrl = INITIAL_URL;
    private volatile String currentBridgeToken = "";

    private String pendingCameraCallbackId;
    private String pendingCameraToken;
    private String pendingLocationCallbackId;
    private String pendingLocationToken;
    private String pendingPaymentCallbackId;
    private String pendingPaymentToken;

    private LocationListener activeLocationListener;
    private Runnable activeLocationTimeout;

    private GeolocationPermissions.Callback pendingGeolocationCallback;
    private String pendingGeolocationOrigin;

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        locationManager = (LocationManager) getSystemService(LOCATION_SERVICE);

        FrameLayout root = new FrameLayout(this);
        webView = new WebView(this);
        root.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));
        setContentView(root);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            WebView.setWebContentsDebuggingEnabled(false);
        }

        webView.removeJavascriptInterface("searchBoxJavaBridge_");
        webView.removeJavascriptInterface("accessibility");
        webView.removeJavascriptInterface("accessibilityTraversal");
        webView.addJavascriptInterface(new NativeBridge(), jsInterfaceName);
        webView.setWebViewClient(new SecureWebViewClient());
        webView.setWebChromeClient(new SecureWebChromeClient());

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setDatabaseEnabled(false);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setSupportMultipleWindows(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            settings.setSafeBrowsingEnabled(true);
        }

        webView.loadUrl(INITIAL_URL);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        clearLocationState();
        if (webView != null) {
            webView.stopLoading();
            webView.removeJavascriptInterface(jsInterfaceName);
            webView.destroy();
        }
        super.onDestroy();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_CAMERA) {
            handleCameraResult(resultCode, data);
        } else if (requestCode == REQUEST_PAYMENT) {
            handlePaymentResult(resultCode, data);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQUEST_LOCATION_PERMISSION) {
            return;
        }

        boolean granted = grantResults.length > 0;
        for (int result : grantResults) {
            if (result != PackageManager.PERMISSION_GRANTED) {
                granted = false;
                break;
            }
        }

        if (pendingGeolocationCallback != null && pendingGeolocationOrigin != null) {
            pendingGeolocationCallback.invoke(pendingGeolocationOrigin, granted, false);
            pendingGeolocationCallback = null;
            pendingGeolocationOrigin = null;
        }

        if (pendingLocationCallbackId != null) {
            String callbackId = pendingLocationCallbackId;
            String bridgeToken = pendingLocationToken;
            if (granted) {
                requestSingleLocationUpdate(callbackId, bridgeToken);
            } else {
                clearPendingLocationCallback();
                sendError(callbackId, "location", "permission_denied", "Location permission denied.", bridgeToken);
            }
        }
    }

    private final class NativeBridge {
        @JavascriptInterface
        public void postMessage(final String envelopeJson) {
            if (webView == null) {
                return;
            }
            webView.post(new Runnable() {
                @Override
                public void run() {
                    handleBridgeEnvelope(envelopeJson);
                }
            });
        }
    }

    private final class SecureWebChromeClient extends WebChromeClient {
        @Override
        public void onPermissionRequest(PermissionRequest request) {
            request.deny();
        }

        @Override
        public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
            Uri uri = Uri.parse(origin);
            if (!isAllowedUri(uri)) {
                callback.invoke(origin, false, false);
                return;
            }

            if (hasLocationPermission()) {
                callback.invoke(origin, true, false);
                return;
            }

            pendingGeolocationOrigin = origin;
            pendingGeolocationCallback = callback;
            requestLocationPermission();
        }
    }

    private final class SecureWebViewClient extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            return handleNavigationRequest(request.getUrl());
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, String url) {
            return handleNavigationRequest(Uri.parse(url));
        }

        @Override
        public void onPageStarted(WebView view, String url, Bitmap favicon) {
            currentPageUrl = url;
            currentBridgeToken = "";
            super.onPageStarted(view, url, favicon);
        }

        @Override
        public void onPageFinished(WebView view, String url) {
            currentPageUrl = url;
            if (isAllowedUrl(url)) {
                currentBridgeToken = UUID.randomUUID().toString();
                injectBridgeShim();
            } else {
                currentBridgeToken = "";
            }
            super.onPageFinished(view, url);
        }

        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            if (isFrameworkUrl(uri) || isAllowedUri(uri)) {
                return super.shouldInterceptRequest(view, request);
            }
            return new WebResourceResponse(
                    "text/plain",
                    StandardCharsets.UTF_8.name(),
                    new ByteArrayInputStream(new byte[0])
            );
        }

        @Override
        public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
            handler.cancel();
        }
    }

    private boolean handleNavigationRequest(Uri uri) {
        if (uri == null) {
            return true;
        }

        if (isAllowedUri(uri)) {
            return false;
        }

        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.US);
        if ("tel".equals(scheme) || "mailto".equals(scheme)) {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, uri));
            } catch (ActivityNotFoundException ignored) {
            }
        }
        return true;
    }

    private void injectBridgeShim() {
        String script =
                "(function(){" +
                        "const token=" + JSONObject.quote(currentBridgeToken) + ";" +
                        "const nativeName=" + JSONObject.quote(jsInterfaceName) + ";" +
                        "const bridge=Object.freeze({" +
                        "postMessage:function(message){" +
                        "if(!message||typeof message!=='object'){throw new Error('message must be an object');}" +
                        "const envelope=JSON.stringify({token:token,message:message});" +
                        "window[nativeName].postMessage(envelope);" +
                        "}" +
                        "});" +
                        "Object.defineProperty(window,'HybridAppNative',{value:bridge,configurable:false,writable:false});" +
                        "})();";
        webView.evaluateJavascript(script, null);
    }

    private void handleBridgeEnvelope(String envelopeJson) {
        if (!isAllowedUrl(currentPageUrl) || currentBridgeToken.isEmpty()) {
            return;
        }

        try {
            JSONObject envelope = new JSONObject(envelopeJson);
            String token = envelope.optString("token", "");
            if (!currentBridgeToken.equals(token)) {
                return;
            }

            JSONObject message = envelope.optJSONObject("message");
            if (message == null) {
                return;
            }

            String action = message.optString("action", "");
            String callbackId = validateCallbackId(message.optString("callbackId", ""));
            JSONObject payload = message.optJSONObject("payload");
            if (payload == null) {
                payload = new JSONObject();
            }

            if ("camera".equals(action)) {
                launchCamera(callbackId, currentBridgeToken);
            } else if ("location".equals(action)) {
                handleLocationRequest(callbackId, currentBridgeToken);
            } else if ("payment".equals(action)) {
                launchUpiPayment(callbackId, currentBridgeToken, payload);
            } else {
                sendError(callbackId, action, "unsupported_action", "Unsupported native action.", currentBridgeToken);
            }
        } catch (JSONException ignored) {
        } catch (IllegalArgumentException e) {
            sendError("", "", "validation_error", e.getMessage(), currentBridgeToken);
        }
    }

    private void launchCamera(String callbackId, String bridgeToken) {
        if (pendingCameraCallbackId != null) {
            sendError(callbackId, "camera", "request_in_progress", "A camera request is already in progress.", bridgeToken);
            return;
        }

        Intent intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        if (intent.resolveActivity(getPackageManager()) == null) {
            sendError(callbackId, "camera", "camera_unavailable", "No camera app is available.", bridgeToken);
            return;
        }

        pendingCameraCallbackId = callbackId;
        pendingCameraToken = bridgeToken;
        startActivityForResult(intent, REQUEST_CAMERA);
    }

    private void handleCameraResult(int resultCode, Intent data) {
        String callbackId = pendingCameraCallbackId;
        String bridgeToken = pendingCameraToken;
        pendingCameraCallbackId = null;
        pendingCameraToken = null;

        if (callbackId == null || bridgeToken == null) {
            return;
        }

        if (resultCode != RESULT_OK || data == null || data.getExtras() == null) {
            sendError(callbackId, "camera", "cancelled", "Camera capture was cancelled.", bridgeToken);
            return;
        }

        Object value = data.getExtras().get("data");
        if (!(value instanceof Bitmap)) {
            sendError(callbackId, "camera", "capture_failed", "Camera did not return an image.", bridgeToken);
            return;
        }

        Bitmap bitmap = (Bitmap) value;
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        bitmap.compress(Bitmap.CompressFormat.JPEG, 90, outputStream);

        JSONObject payload = new JSONObject();
        try {
            payload.put("mimeType", "image/jpeg");
            payload.put("imageBase64", Base64.encodeToString(outputStream.toByteArray(), Base64.NO_WRAP));
            sendSuccess(callbackId, "camera", payload, bridgeToken);
        } catch (JSONException e) {
            sendError(callbackId, "camera", "serialization_error", "Failed to serialize image.", bridgeToken);
        }
    }

    private void handleLocationRequest(String callbackId, String bridgeToken) {
        if (pendingLocationCallbackId != null) {
            sendError(callbackId, "location", "request_in_progress", "A location request is already in progress.", bridgeToken);
            return;
        }

        pendingLocationCallbackId = callbackId;
        pendingLocationToken = bridgeToken;

        if (!hasLocationPermission()) {
            requestLocationPermission();
            return;
        }

        requestSingleLocationUpdate(callbackId, bridgeToken);
    }

    private void requestSingleLocationUpdate(final String callbackId, final String bridgeToken) {
        if (!hasLocationPermission()) {
            clearPendingLocationCallback();
            sendError(callbackId, "location", "permission_denied", "Location permission denied.", bridgeToken);
            return;
        }

        final String provider;
        if (locationManager != null && locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
            provider = LocationManager.GPS_PROVIDER;
        } else if (locationManager != null && locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
            provider = LocationManager.NETWORK_PROVIDER;
        } else {
            clearPendingLocationCallback();
            sendError(callbackId, "location", "location_unavailable", "No location provider is enabled.", bridgeToken);
            return;
        }

        try {
            Location lastKnown = locationManager.getLastKnownLocation(provider);
            if (lastKnown != null) {
                clearPendingLocationCallback();
                sendLocation(callbackId, bridgeToken, lastKnown);
                return;
            }

            activeLocationListener = new LocationListener() {
                @Override
                public void onLocationChanged(Location location) {
                    clearLocationUpdates();
                    clearPendingLocationCallback();
                    sendLocation(callbackId, bridgeToken, location);
                }

                @Override
                public void onStatusChanged(String provider, int status, Bundle extras) {
                }

                @Override
                public void onProviderEnabled(String provider) {
                }

                @Override
                public void onProviderDisabled(String provider) {
                }
            };

            activeLocationTimeout = new Runnable() {
                @Override
                public void run() {
                    clearLocationUpdates();
                    clearPendingLocationCallback();
                    sendError(callbackId, "location", "timeout", "Timed out waiting for a location fix.", bridgeToken);
                }
            };

            handler.postDelayed(activeLocationTimeout, LOCATION_TIMEOUT_MS);
            locationManager.requestSingleUpdate(provider, activeLocationListener, Looper.getMainLooper());
        } catch (SecurityException e) {
            clearLocationState();
            sendError(callbackId, "location", "permission_denied", "Location permission denied.", bridgeToken);
        }
    }

    private void sendLocation(String callbackId, String bridgeToken, Location location) {
        JSONObject payload = new JSONObject();
        try {
            payload.put("latitude", location.getLatitude());
            payload.put("longitude", location.getLongitude());
            payload.put("accuracyMeters", location.getAccuracy());
            payload.put("timestamp", location.getTime());
            sendSuccess(callbackId, "location", payload, bridgeToken);
        } catch (JSONException e) {
            sendError(callbackId, "location", "serialization_error", "Failed to serialize location.", bridgeToken);
        }
    }

    private void launchUpiPayment(String callbackId, String bridgeToken, JSONObject payload) {
        if (pendingPaymentCallbackId != null) {
            sendError(callbackId, "payment", "request_in_progress", "A payment request is already in progress.", bridgeToken);
            return;
        }

        String upiId = payload.optString("upiId", "").trim();
        String payeeName = payload.optString("payeeName", "").trim();
        String note = payload.optString("note", "").trim();
        String amountText = payload.optString("amount", "").trim();

        if (!UPI_ID_PATTERN.matcher(upiId).matches()) {
            sendError(callbackId, "payment", "invalid_upi_id", "UPI ID is invalid.", bridgeToken);
            return;
        }
        if (payeeName.isEmpty() || payeeName.length() > 60) {
            sendError(callbackId, "payment", "invalid_payee", "Payee name is invalid.", bridgeToken);
            return;
        }
        if (note.length() > 80) {
            sendError(callbackId, "payment", "invalid_note", "Payment note is too long.", bridgeToken);
            return;
        }

        final BigDecimal amount;
        try {
            amount = new BigDecimal(amountText).setScale(2, RoundingMode.HALF_UP);
        } catch (NumberFormatException e) {
            sendError(callbackId, "payment", "invalid_amount", "Amount must be numeric.", bridgeToken);
            return;
        }

        if (amount.compareTo(new BigDecimal("0.01")) < 0 || amount.compareTo(new BigDecimal("100000.00")) > 0) {
            sendError(callbackId, "payment", "invalid_amount", "Amount is out of range.", bridgeToken);
            return;
        }

        Uri uri = new Uri.Builder()
                .scheme("upi")
                .authority("pay")
                .appendQueryParameter("pa", upiId)
                .appendQueryParameter("pn", payeeName)
                .appendQueryParameter("am", amount.toPlainString())
                .appendQueryParameter("cu", "INR")
                .appendQueryParameter("tn", note)
                .build();

        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
        if (intent.resolveActivity(getPackageManager()) == null) {
            sendError(callbackId, "payment", "payment_unavailable", "No UPI payment app is available.", bridgeToken);
            return;
        }

        pendingPaymentCallbackId = callbackId;
        pendingPaymentToken = bridgeToken;
        startActivityForResult(Intent.createChooser(intent, "Complete payment"), REQUEST_PAYMENT);
    }

    private void handlePaymentResult(int resultCode, Intent data) {
        String callbackId = pendingPaymentCallbackId;
        String bridgeToken = pendingPaymentToken;
        pendingPaymentCallbackId = null;
        pendingPaymentToken = null;

        if (callbackId == null || bridgeToken == null) {
            return;
        }

        if (resultCode != RESULT_OK) {
            sendError(callbackId, "payment", "cancelled", "Payment was cancelled.", bridgeToken);
            return;
        }

        String response = null;
        if (data != null) {
            response = data.getStringExtra("response");
            if (response == null && data.getData() != null) {
                response = data.getData().toString();
            }
        }

        if (response == null || response.trim().isEmpty()) {
            sendError(callbackId, "payment", "unknown_result", "Payment app returned no result.", bridgeToken);
            return;
        }

        Map<String, String> parsed = parseQueryStyleResponse(response);
        String status = valueIgnoreCase(parsed, "status");
        if (status == null) {
            sendError(callbackId, "payment", "unknown_result", "Payment status was missing.", bridgeToken);
            return;
        }

        if ("success".equalsIgnoreCase(status) || "submitted".equalsIgnoreCase(status)) {
            JSONObject payload = new JSONObject();
            try {
                payload.put("status", status.toLowerCase(Locale.US));
                payload.put("approvalRefNo", firstNonEmpty(
                        valueIgnoreCase(parsed, "approvalrefno"),
                        valueIgnoreCase(parsed, "txnref"),
                        valueIgnoreCase(parsed, "tr")
                ));
                sendSuccess(callbackId, "payment", payload, bridgeToken);
            } catch (JSONException e) {
                sendError(callbackId, "payment", "serialization_error", "Failed to serialize payment result.", bridgeToken);
            }
        } else {
            sendError(callbackId, "payment", "payment_failed", "Payment failed with status: " + status + ".", bridgeToken);
        }
    }

    private void sendSuccess(String callbackId, String action, JSONObject payload, String bridgeToken) {
        JSONObject result = new JSONObject();
        try {
            result.put("callbackId", callbackId);
            result.put("action", action);
            result.put("success", true);
            result.put("payload", payload);
            dispatchToPage(result, bridgeToken);
        } catch (JSONException ignored) {
        }
    }

    private void sendError(String callbackId, String action, String code, String message, String bridgeToken) {
        JSONObject result = new JSONObject();
        JSONObject error = new JSONObject();
        try {
            result.put("callbackId", callbackId);
            result.put("action", action);
            result.put("success", false);
            error.put("code", code);
            error.put("message", message);
            result.put("error", error);
            dispatchToPage(result, bridgeToken);
        } catch (JSONException ignored) {
        }
    }

    private void dispatchToPage(JSONObject result, String bridgeToken) {
        if (webView == null || bridgeToken == null || !bridgeToken.equals(currentBridgeToken)) {
            return;
        }

        String script =
                "(function(){" +
                        "const detail=JSON.parse(" + JSONObject.quote(result.toString()) + ");" +
                        "window.dispatchEvent(new CustomEvent('HybridAppNativeResult',{detail:detail}));" +
                        "})();";
        webView.evaluateJavascript(script, null);
    }

    private boolean hasLocationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return true;
        }
        return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    private void requestLocationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            requestPermissions(new String[]{
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
            }, REQUEST_LOCATION_PERMISSION);
        }
    }

    private boolean isAllowedUrl(String url) {
        if (url == null || url.trim().isEmpty()) {
            return false;
        }
        return isAllowedUri(Uri.parse(url));
    }

    private boolean isAllowedUri(Uri uri) {
        if (uri == null) {
            return false;
        }
        String scheme = uri.getScheme();
        String host = uri.getHost();
        return scheme != null
                && "https".equalsIgnoreCase(scheme)
                && host != null
                && ALLOWED_HOSTS.contains(host.toLowerCase(Locale.US));
    }

    private boolean isFrameworkUrl(Uri uri) {
        if (uri == null || uri.getScheme() == null) {
            return false;
        }
        String scheme = uri.getScheme().toLowerCase(Locale.US);
        return "about".equals(scheme) || "blob".equals(scheme) || "data".equals(scheme);
    }

    private String validateCallbackId(String callbackId) {
        if (!CALLBACK_ID_PATTERN.matcher(callbackId).matches()) {
            throw new IllegalArgumentException("callbackId is invalid.");
        }
        return callbackId;
    }

    private void clearPendingLocationCallback() {
        pendingLocationCallbackId = null;
        pendingLocationToken = null;
    }

    private void clearLocationUpdates() {
        if (activeLocationTimeout != null) {
            handler.removeCallbacks(activeLocationTimeout);
            activeLocationTimeout = null;
        }
        if (activeLocationListener != null && locationManager != null) {
            locationManager.removeUpdates(activeLocationListener);
            activeLocationListener = null;
        }
    }

    private void clearLocationState() {
        clearLocationUpdates();
        clearPendingLocationCallback();
    }

    private Map<String, String> parseQueryStyleResponse(String raw) {
        Map<String, String> output = new HashMap<String, String>();
        String[] parts = raw.split("&");
        for (String part : parts) {
            String[] entry = part.split("=", 2);
            String key = Uri.decode(entry[0]).trim().toLowerCase(Locale.US);
            String value = entry.length > 1 ? Uri.decode(entry[1]).trim() : "";
            output.put(key, value);
        }
        return output;
    }

    private String valueIgnoreCase(Map<String, String> map, String key) {
        return map.get(key.toLowerCase(Locale.US));
    }

    private String firstNonEmpty(String... values) {
        for (String value : values) {
            if (value != null && !value.trim().isEmpty()) {
                return value;
            }
        }
        return "";
    }
}