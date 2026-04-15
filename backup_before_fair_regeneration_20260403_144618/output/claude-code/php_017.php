<?php

class SecureDataEncryption {
    private $encryptionKey;
    private $cipher = 'aes-256-gcm';
    
    public function __construct($key = null) {
        if ($key === null) {
            // Generate a secure key if not provided
            // In production, load this from secure configuration
            $this->encryptionKey = getenv('ENCRYPTION_KEY') ?: $this->generateKey();
        } else {
            $this->encryptionKey = $key;
        }
    }
    
    private function generateKey() {
        return base64_encode(random_bytes(32));
    }
    
    public function encrypt($data) {
        if (empty($data)) {
            return false;
        }
        
        $key = base64_decode($this->encryptionKey);
        $iv = random_bytes(16);
        $tag = '';
        
        $encrypted = openssl_encrypt(
            $data,
            $this->cipher,
            $key,
            OPENSSL_RAW_DATA,
            $iv,
            $tag
        );
        
        if ($encrypted === false) {
            return false;
        }
        
        return base64_encode($iv . $tag . $encrypted);
    }
    
    public function decrypt($encryptedData) {
        if (empty($encryptedData)) {
            return false;
        }
        
        $data = base64_decode($encryptedData);
        if ($data === false) {
            return false;
        }
        
        $key = base64_decode($this->encryptionKey);
        $iv = substr($data, 0, 16);
        $tag = substr($data, 16, 16);
        $ciphertext = substr($data, 32);
        
        $decrypted = openssl_decrypt(
            $ciphertext,
            $this->cipher,
            $key,
            OPENSSL_RAW_DATA,
            $iv,
            $tag
        );
        
        return $decrypted;
    }
}

// Helper functions for backward compatibility
function encrypt($data) {
    static $encryptor = null;
    if ($encryptor === null) {
        $encryptor = new SecureDataEncryption();
    }
    return $encryptor->encrypt($data);
}

function decrypt($data) {
    static $encryptor = null;
    if ($encryptor === null) {
        $encryptor = new SecureDataEncryption();
    }
    return $encryptor->decrypt($data);
}