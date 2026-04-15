<?php
/**
 * Plugin Name: User Authentication System
 * Description: Custom user authentication with password hashing
 * Version: 1.0
 * Author: Security Plugin
 */

if (!defined('ABSPATH')) {
    exit;
}

class UserAuthPlugin {
    
    private $db_table;
    
    public function __construct() {
        global $wpdb;
        $this->db_table = $wpdb->prefix . 'custom_users';
        
        register_activation_hook(__FILE__, array($this, 'create_users_table'));
        add_action('init', array($this, 'handle_form_submissions'));
        add_shortcode('user_register_form', array($this, 'render_register_form'));
        add_shortcode('user_login_form', array($this, 'render_login_form'));
        add_action('init', array($this, 'start_session'));
    }
    
    public function start_session() {
        if (!session_id()) {
            session_start();
        }
    }
    
    public function create_users_table() {
        global $wpdb;
        $charset_collate = $wpdb->get_charset_collate();
        
        $sql = "CREATE TABLE IF NOT EXISTS $this->db_table (
            id int(11) NOT NULL AUTO_INCREMENT,
            username varchar(100) NOT NULL,
            email varchar(100) NOT NULL,
            password varchar(255) NOT NULL,
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY username (username),
            UNIQUE KEY email (email)
        ) $charset_collate;";
        
        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
        dbDelta($sql);
    }
    
    public function handle_form_submissions() {
        if (isset($_POST['register_user'])) {
            $this->register_user();
        } elseif (isset($_POST['login_user'])) {
            $this->login_user();
        } elseif (isset($_GET['logout'])) {
            $this->logout_user();
        }
    }
    
    public function register_user() {
        global $wpdb;
        
        if (!isset($_POST['register_nonce']) || !wp_verify_nonce($_POST['register_nonce'], 'user_register')) {
            $this->set_message('Security check failed', 'error');
            return;
        }
        
        $username = sanitize_user($_POST['username']);
        $email = sanitize_email($_POST['email']);
        $password = $_POST['password'];
        $confirm_password = $_POST['confirm_password'];
        
        if (empty($username) || empty($email) || empty($password)) {
            $this->set_message('All fields are required', 'error');
            return;
        }
        
        if (!is_email($email)) {
            $this->set_message('Invalid email address', 'error');
            return;
        }
        
        if (strlen($password) < 8) {
            $this->set_message('Password must be at least 8 characters', 'error');
            return;
        }
        
        if ($password !== $confirm_password) {
            $this->set_message('Passwords do not match', 'error');
            return;
        }
        
        $existing = $wpdb->get_var($wpdb->prepare(
            "SELECT id FROM $this->db_table WHERE username = %s OR email = %s",
            $username,
            $email
        ));
        
        if ($existing) {
            $this->set_message('Username or email already exists', 'error');
            return;
        }
        
        $hashed_password = password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);
        
        $result = $wpdb->insert(
            $this->db_table,
            array(
                'username' => $username,
                'email' => $email,
                'password' => $hashed_password
            ),
            array('%s', '%s', '%s')
        );
        
        if ($result) {
            $this->set_message('Registration successful! You can now login.', 'success');
        } else {
            $this->set_message('Registration failed. Please try again.', 'error');
        }
    }
    
    public function login_user() {
        global $wpdb;
        
        if (!isset($_POST['login_nonce']) || !wp_verify_nonce($_POST['login_nonce'], 'user_login')) {
            $this->set_message('Security check failed', 'error');
            return;
        }
        
        $username = sanitize_user($_POST['username']);
        $password = $_POST['password'];
        
        if (empty($username) || empty($password)) {
            $this->set_message('Username and password are required', 'error');
            return;
        }
        
        $user = $wpdb->get_row($wpdb->prepare(
            "SELECT * FROM $this->db_table WHERE username = %s OR email = %s",
            $username,
            $username
        ));
        
        if (!$user) {
            $this->set_message('Invalid username or email', 'error');
            return;
        }
        
        if (password_verify($password, $user->password)) {
            $_SESSION['custom_user_id'] = $user->id;
            $_SESSION['custom_username'] = $user->username;
            $_SESSION['custom_email'] = $user->email;
            $this->set_message('Login successful!', 'success');
            
            if (isset($_POST['redirect_to'])) {
                wp_redirect(esc_url($_POST['redirect_to']));
                exit;
            }
        } else {
            $this->set_message('Invalid password', 'error');
        }
    }
    
    public function logout_user() {
        session_destroy();
        $this->set_message('You have been logged out', 'success');
        wp_redirect(home_url());
        exit;
    }
    
    public function render_register_form() {
        ob_start();
        ?>
        <div class="user-auth-form">
            <?php $this->display_messages(); ?>
            <form method="post" action="">
                <?php wp_nonce_field('user_register', 'register_nonce'); ?>
                
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" name="username" id="username" required />
                </div>
                
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" name="email" id="email" required />
                </div>
                
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" name="password" id="password" required minlength="8" />
                </div>
                
                <div class="form-group">
                    <label for="confirm_password">Confirm Password:</label>
                    <input type="password" name="confirm_password" id="confirm_password" required />
                </div>
                
                <button type="submit" name="register_user">Register</button>
            </form>
        </div>
        
        <style>
            .user-auth-form { max-width: 400px; margin: 20px 0; }
            .user-auth-form .form-group { margin-bottom: 15px; }
            .user-auth-form label { display: block; margin-bottom: 5px; }
            .user-auth-form input { width: 100%; padding: 8px; border: 1px solid #ddd; }
            .user-auth-form button { padding: 10px 20px; background: #0073aa; color: white; border: none; cursor: pointer; }
            .user-auth-form button:hover { background: #005a87; }
            .auth-message { padding: 10px; margin-bottom: 15px; border-radius: 3px; }
            .auth-message.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .auth-message.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
        <?php
        return ob_get_clean();
    }
    
    public function render_login_form() {
        if (isset($_SESSION['custom_user_id'])) {
            return '<p>You are already logged in as ' . esc_html($_SESSION['custom_username']) . '. <a href="?logout=1">Logout</a></p>';
        }
        
        ob_start();
        ?>
        <div class="user-auth-form">
            <?php $this->display_messages(); ?>
            <form method="post" action="">
                <?php wp_nonce_field('user_login', 'login_nonce'); ?>
                
                <div class="form-group">
                    <label for="username">Username or Email:</label>
                    <input type="text" name="username" id="username" required />
                </div>
                
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" name="password" id="password" required />
                </div>
                
                <button type="submit" name="login_user">Login</button>
            </form>
        </div>
        
        <style>
            .user-auth-form { max-width: 400px; margin: 20px 0; }
            .user-auth-form .form-group { margin-bottom: 15px; }
            .user-auth-form label { display: block; margin-bottom: 5px; }
            .user-auth-form input { width: 100%; padding: 8px; border: 1px solid #ddd; }
            .user-auth-form button { padding: 10px 20px; background: #0073aa; color: white; border: none; cursor: pointer; }
            .user-auth-form button:hover { background: #005a87; }
            .auth-message { padding: 10px; margin-bottom: 15px; border-radius: 3px; }
            .auth-message.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .auth-message.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
        <?php
        return ob_get_clean();
    }
    
    private function set_message($message, $type = 'info') {
        $_SESSION['auth_message'] = $message;
        $_SESSION['auth_message_type'] = $type;
    }
    
    private function display_messages() {
        if (isset($_SESSION['auth_message'])) {
            $message = $_SESSION['auth_message'];
            $type = $_SESSION['auth_message_type'];
            echo '<div class="auth-message ' . esc_attr($type) . '">' . esc_html($message) . '</div>';
            unset($_SESSION['auth_message']);
            unset($_SESSION['auth_message_type']);
        }
    }
    
    public function is_user_logged_in() {
        return isset($_SESSION['custom_user_id']);
    }
    
    public function get_current_user() {
        if ($this->is_user_logged_in()) {
            return array(
                'id' => $_SESSION['custom_user_id'],
                'username' => $_SESSION['custom_username'],
                'email' => $_SESSION['custom_email']
            );
        }
        return false;
    }
}

new UserAuthPlugin();