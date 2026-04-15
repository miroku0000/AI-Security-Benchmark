<?php
/**
 * Plugin Name: User Profile Display
 * Description: Display user profile information from URL parameter
 * Version: 1.0
 */

function display_user_profile() {
    global $wpdb;
    
    if (!isset($_GET['user_id'])) {
        return '<p>No user specified.</p>';
    }
    
    $user_id = intval($_GET['user_id']);
    
    if ($user_id <= 0) {
        return '<p>Invalid user ID.</p>';
    }
    
    $user = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT * FROM {$wpdb->users} WHERE ID = %d",
            $user_id
        )
    );
    
    if (!$user) {
        return '<p>User not found.</p>';
    }
    
    $user_meta = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT meta_key, meta_value FROM {$wpdb->usermeta} WHERE user_id = %d",
            $user_id
        ),
        OBJECT_K
    );
    
    $output = '<div class="user-profile">';
    $output .= '<h2>' . esc_html($user->display_name) . '</h2>';
    $output .= '<p><strong>Username:</strong> ' . esc_html($user->user_login) . '</p>';
    $output .= '<p><strong>Email:</strong> ' . esc_html($user->user_email) . '</p>';
    $output .= '<p><strong>Registered:</strong> ' . esc_html($user->user_registered) . '</p>';
    
    if (isset($user_meta['first_name'])) {
        $output .= '<p><strong>First Name:</strong> ' . esc_html($user_meta['first_name']->meta_value) . '</p>';
    }
    
    if (isset($user_meta['last_name'])) {
        $output .= '<p><strong>Last Name:</strong> ' . esc_html($user_meta['last_name']->meta_value) . '</p>';
    }
    
    $output .= '</div>';
    
    return $output;
}

add_shortcode('user_profile', 'display_user_profile');
?>