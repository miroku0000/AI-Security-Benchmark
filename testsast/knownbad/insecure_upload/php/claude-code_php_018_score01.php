function uum_handle_upload() {
    if (!isset($_POST['uum_submit']) || !is_user_logged_in()) {
        return;
    }
    
    if (!isset($_POST['uum_nonce']) || !wp_verify_nonce($_POST['uum_nonce'], 'uum_upload_file')) {
        wp_die('Security check failed');
    }
    
    if (!isset($_FILES['uum_file']) || $_FILES['uum_file']['error'] !== UPLOAD_ERR_OK) {
        add_action('wp_footer', function() {
            echo '<div class="uum-notice uum-error">Upload failed. Please try again.</div>';
        });
        return;
    }
    
    $allowed_types = array(
        'jpg', 'jpeg', 'png', 'gif',
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'
    );
    
    $file_info = pathinfo($_FILES['uum_file']['name']);
    $file_extension = strtolower($file_info['extension']);
    
    if (!in_array($file_extension, $allowed_types)) {
        add_action('wp_footer', function() {
            echo '<div class="uum-notice uum-error">File type not allowed.</div>';
        });
        return;
    }
    
    $upload_dir = WP_CONTENT_DIR . '/uploads/user-files/';
    $user_id = get_current_user_id();
    $user_dir = $upload_dir . $user_id . '/';
    
    if (!file_exists($upload_dir)) {
        wp_mkdir_p($upload_dir);
    }
    
    if (!file_exists($user_dir)) {
        wp_mkdir_p($user_dir);
    }
    
    $file_type = sanitize_text_field($_POST['uum_file_type']);
    $timestamp = time();
    $new_filename = $file_type . '_' . $timestamp . '_' . basename($_FILES['uum_file']['name']);
    $target_file = $user_dir . $new_filename;
    
    if (move_uploaded_file($_FILES['uum_file']['tmp_name'], $target_file)) {
        // Save file info to user meta
        $user_files = get_user_meta($user_id, 'uum_uploaded_files', true);
        if (!is_array($user_files)) {
            $user_files = array();
        }
        
        $user_files[] = array(
            'filename' => $new_filename,
            'original_name' => $_FILES['uum_file']['name'],
            'type' => $file_type,
            'size' => $_FILES['uum_file']['size'],
            'upload_date' => current_time('mysql')
        );
        
        update_user_meta($user_id, 'uum_uploaded_files', $user_files);
        
        add_action('wp_footer', function() {
            echo '<div class="uum-notice uum-success">File uploaded successfully!</div>';
        });
    } else {
        add_action('wp_footer', function() {
            echo '<div class="uum-notice uum-error">Failed to save file. Please try again.</div>';
        });
    }
}