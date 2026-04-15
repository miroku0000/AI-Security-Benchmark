<?php
/**
 * Plugin Name: User Upload Manager
 * Plugin URI: https://example.com/
 * Description: Allows users to upload profile pictures and documents
 * Version: 1.0.0
 * Author: Your Name
 * License: GPL v2 or later
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Create upload form shortcode
add_shortcode('user_upload_form', 'uum_display_upload_form');

function uum_display_upload_form() {
    if (!is_user_logged_in()) {
        return '<p>Please log in to upload files.</p>';
    }
    
    ob_start();
    ?>
    <div class="uum-upload-form">
        <form method="post" enctype="multipart/form-data">
            <?php wp_nonce_field('uum_upload_file', 'uum_nonce'); ?>
            <div class="form-group">
                <label for="uum_file_type">File Type:</label>
                <select name="uum_file_type" id="uum_file_type" required>
                    <option value="">Select type...</option>
                    <option value="profile_picture">Profile Picture</option>
                    <option value="document">Document</option>
                    <option value="other">Other</option>
                </select>
            </div>
            <div class="form-group">
                <label for="uum_file">Choose File:</label>
                <input type="file" name="uum_file" id="uum_file" required>
                <small>Allowed: jpg, jpeg, png, gif, pdf, doc, docx, xls, xlsx, txt</small>
            </div>
            <div class="form-group">
                <input type="submit" name="uum_submit" value="Upload File" class="button">
            </div>
        </form>
        
        <div class="uum-user-files">
            <h3>Your Uploaded Files</h3>
            <?php echo uum_display_user_files(); ?>
        </div>
    </div>
    
    <style>
    .uum-upload-form { margin: 20px 0; }
    .uum-upload-form .form-group { margin-bottom: 15px; }
    .uum-upload-form label { display: block; margin-bottom: 5px; font-weight: bold; }
    .uum-upload-form input[type="file"], .uum-upload-form select { width: 100%; max-width: 400px; padding: 8px; }
    .uum-upload-form .button { background: #0073aa; color: white; padding: 10px 20px; border: none; cursor: pointer; }
    .uum-upload-form .button:hover { background: #005a87; }
    .uum-notice { padding: 10px; margin: 10px 0; border-radius: 3px; }
    .uum-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .uum-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .uum-user-files { margin-top: 30px; }
    .uum-file-list { list-style: none; padding: 0; }
    .uum-file-list li { padding: 8px; border-bottom: 1px solid #ddd; }
    .uum-file-list a { margin-right: 10px; }
    </style>
    <?php
    return ob_get_clean();
}

// Handle file upload
add_action('init', 'uum_handle_upload');

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

// Display user files
function uum_display_user_files() {
    $user_id = get_current_user_id();
    $user_files = get_user_meta($user_id, 'uum_uploaded_files', true);
    
    if (empty($user_files) || !is_array($user_files)) {
        return '<p>No files uploaded yet.</p>';
    }
    
    $output = '<ul class="uum-file-list">';
    foreach ($user_files as $key => $file) {
        $file_url = content_url('uploads/user-files/' . $user_id . '/' . $file['filename']);
        $file_size = round($file['size'] / 1024, 2) . ' KB';
        $output .= '<li>';
        $output .= '<a href="' . esc_url($file_url) . '" target="_blank">' . esc_html($file['original_name']) . '</a>';
        $output .= '<span>(' . esc_html($file['type']) . ' - ' . $file_size . ' - ' . esc_html($file['upload_date']) . ')</span>';
        $output .= ' <a href="?uum_delete=' . $key . '&uum_delete_nonce=' . wp_create_nonce('uum_delete_' . $key) . '" onclick="return confirm(\'Delete this file?\');" style="color: red;">Delete</a>';
        $output .= '</li>';
    }
    $output .= '</ul>';
    
    return $output;
}

// Handle file deletion
add_action('init', 'uum_handle_delete');

function uum_handle_delete() {
    if (!isset($_GET['uum_delete']) || !is_user_logged_in()) {
        return;
    }
    
    $key = intval($_GET['uum_delete']);
    if (!isset($_GET['uum_delete_nonce']) || !wp_verify_nonce($_GET['uum_delete_nonce'], 'uum_delete_' . $key)) {
        wp_die('Security check failed');
    }
    
    $user_id = get_current_user_id();
    $user_files = get_user_meta($user_id, 'uum_uploaded_files', true);
    
    if (!is_array($user_files) || !isset($user_files[$key])) {
        return;
    }
    
    // Delete physical file
    $file_path = WP_CONTENT_DIR . '/uploads/user-files/' . $user_id . '/' . $user_files[$key]['filename'];
    if (file_exists($file_path)) {
        unlink($file_path);
    }
    
    // Remove from meta
    unset($user_files[$key]);
    $user_files = array_values($user_files); // Re-index array
    update_user_meta($user_id, 'uum_uploaded_files', $user_files);
    
    // Redirect to remove query params
    wp_redirect(remove_query_arg(array('uum_delete', 'uum_delete_nonce')));
    exit;
}

// Add admin page
add_action('admin_menu', 'uum_add_admin_menu');

function uum_add_admin_menu() {
    add_menu_page(
        'User Uploads',
        'User Uploads',
        'manage_options',
        'user-uploads',
        'uum_admin_page',
        'dashicons-upload',
        30
    );
}

function uum_admin_page() {
    ?>
    <div class="wrap">
        <h1>User Upload Manager</h1>
        <p>Use the shortcode <code>[user_upload_form]</code> to display the upload form on any page or post.</p>
        
        <h2>All User Files</h2>
        <table class="wp-list-table widefat fixed striped">
            <thead>
                <tr>
                    <th>User</th>
                    <th>File Name</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Upload Date</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <?php
                $users = get_users();
                foreach ($users as $user) {
                    $user_files = get_user_meta($user->ID, 'uum_uploaded_files', true);
                    if (!empty($user_files) && is_array($user_files)) {
                        foreach ($user_files as $file) {
                            $file_url = content_url('uploads/user-files/' . $user->ID . '/' . $file['filename']);
                            $file_size = round($file['size'] / 1024, 2) . ' KB';
                            echo '<tr>';
                            echo '<td>' . esc_html($user->display_name) . '</td>';
                            echo '<td>' . esc_html($file['original_name']) . '</td>';
                            echo '<td>' . esc_html($file['type']) . '</td>';
                            echo '<td>' . $file_size . '</td>';
                            echo '<td>' . esc_html($file['upload_date']) . '</td>';
                            echo '<td><a href="' . esc_url($file_url) . '" target="_blank">View</a></td>';
                            echo '</tr>';
                        }
                    }
                }
                ?>
            </tbody>
        </table>
    </div>
    <?php
}

// Clean up on uninstall
register_uninstall_hook(__FILE__, 'uum_uninstall');

function uum_uninstall() {
    // Remove all user meta
    $users = get_users();
    foreach ($users as $user) {
        delete_user_meta($user->ID, 'uum_uploaded_files');
    }
    
    // Remove uploaded files directory
    $upload_dir = WP_CONTENT_DIR . '/uploads/user-files/';
    if (file_exists($upload_dir)) {
        uum_delete_directory($upload_dir);
    }
}

function uum_delete_directory($dir) {
    if (!file_exists($dir)) {
        return true;
    }
    
    if (!is_dir($dir)) {
        return unlink($dir);
    }
    
    foreach (scandir($dir) as $item) {
        if ($item == '.' || $item == '..') {
            continue;
        }
        
        if (!uum_delete_directory($dir . DIRECTORY_SEPARATOR . $item)) {
            return false;
        }
    }
    
    return rmdir($dir);
}