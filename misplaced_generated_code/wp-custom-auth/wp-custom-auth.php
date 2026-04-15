<?php
/**
 * Plugin Name: Custom User Auth
 * Description: User registration and login with password hashing.
 * Version: 1.0.0
 * Author: Custom
 * License: GPL-2.0-or-later
 */

if (!defined('ABSPATH')) {
    exit;
}

final class WP_Custom_User_Auth {

    private static $instance = null;

    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action('init', array($this, 'register_shortcodes'));
        add_action('init', array($this, 'handle_registration'));
        add_action('init', array($this, 'handle_login'));
    }

    public function register_shortcodes() {
        add_shortcode('custom_register_form', array($this, 'render_register_form'));
        add_shortcode('custom_login_form', array($this, 'render_login_form'));
    }

    public function render_register_form() {
        if (is_user_logged_in()) {
            return '<p>' . esc_html__('You are already logged in.', 'wp-custom-auth') . '</p>';
        }
        ob_start();
        $error = get_transient('wpca_reg_error');
        $success = get_transient('wpca_reg_success');
        if ($error) {
            delete_transient('wpca_reg_error');
            echo '<p class="wpca-error">' . esc_html($error) . '</p>';
        }
        if ($success) {
            delete_transient('wpca_reg_success');
            echo '<p class="wpca-success">' . esc_html($success) . '</p>';
        }
        ?>
        <form method="post" action="" class="wpca-register-form">
            <?php wp_nonce_field('wpca_register', 'wpca_register_nonce'); ?>
            <p>
                <label for="wpca_username"><?php esc_html_e('Username', 'wp-custom-auth'); ?></label>
                <input type="text" name="wpca_username" id="wpca_username" required autocomplete="username" />
            </p>
            <p>
                <label for="wpca_email"><?php esc_html_e('Email', 'wp-custom-auth'); ?></label>
                <input type="email" name="wpca_email" id="wpca_email" required autocomplete="email" />
            </p>
            <p>
                <label for="wpca_password"><?php esc_html_e('Password', 'wp-custom-auth'); ?></label>
                <input type="password" name="wpca_password" id="wpca_password" required autocomplete="new-password" />
            </p>
            <p>
                <button type="submit" name="wpca_register_submit" value="1"><?php esc_html_e('Register', 'wp-custom-auth'); ?></button>
            </p>
        </form>
        <?php
        return ob_get_clean();
    }

    public function render_login_form() {
        if (is_user_logged_in()) {
            return '<p>' . esc_html__('You are already logged in.', 'wp-custom-auth') . '</p>';
        }
        ob_start();
        $error = get_transient('wpca_login_error');
        if ($error) {
            delete_transient('wpca_login_error');
            echo '<p class="wpca-error">' . esc_html($error) . '</p>';
        }
        ?>
        <form method="post" action="" class="wpca-login-form">
            <?php wp_nonce_field('wpca_login', 'wpca_login_nonce'); ?>
            <p>
                <label for="wpca_login_user"><?php esc_html_e('Username or Email', 'wp-custom-auth'); ?></label>
                <input type="text" name="wpca_login_user" id="wpca_login_user" required autocomplete="username" />
            </p>
            <p>
                <label for="wpca_login_password"><?php esc_html_e('Password', 'wp-custom-auth'); ?></label>
                <input type="password" name="wpca_login_password" id="wpca_login_password" required autocomplete="current-password" />
            </p>
            <p>
                <button type="submit" name="wpca_login_submit" value="1"><?php esc_html_e('Log In', 'wp-custom-auth'); ?></button>
            </p>
        </form>
        <?php
        return ob_get_clean();
    }

    public function handle_registration() {
        if (!isset($_POST['wpca_register_submit']) || !isset($_POST['wpca_register_nonce'])) {
            return;
        }
        if (!wp_verify_nonce(sanitize_text_field(wp_unslash($_POST['wpca_register_nonce'])), 'wpca_register')) {
            set_transient('wpca_reg_error', __('Security check failed.', 'wp-custom-auth'), 60);
            return;
        }
        $username = isset($_POST['wpca_username']) ? sanitize_user(wp_unslash($_POST['wpca_username']), true) : '';
        $email = isset($_POST['wpca_email']) ? sanitize_email(wp_unslash($_POST['wpca_email'])) : '';
        $password = isset($_POST['wpca_password']) ? wp_unslash($_POST['wpca_password']) : '';

        if ($username === '' || $email === '' || $password === '') {
            set_transient('wpca_reg_error', __('All fields are required.', 'wp-custom-auth'), 60);
            wp_safe_redirect(wp_get_referer() ? wp_get_referer() : home_url('/'));
            exit;
        }

        if (username_exists($username)) {
            set_transient('wpca_reg_error', __('That username is already taken.', 'wp-custom-auth'), 60);
            wp_safe_redirect(wp_get_referer() ? wp_get_referer() : home_url('/'));
            exit;
        }

        if (email_exists($email)) {
            set_transient('wpca_reg_error', __('That email is already registered.', 'wp-custom-auth'), 60);
            wp_safe_redirect(wp_get_referer() ? wp_get_referer() : home_url('/'));
            exit;
        }

        $temp_pass = wp_generate_password(32, true, true);
        $user_id = wp_insert_user(array(
            'user_login' => $username,
            'user_email' => $email,
            'user_pass'  => $temp_pass,
            'role'       => get_option('default_role', 'subscriber'),
        ));

        if (is_wp_error($user_id)) {
            set_transient('wpca_reg_error', $user_id->get_error_message(), 60);
            wp_safe_redirect(wp_get_referer() ? wp_get_referer() : home_url('/'));
            exit;
        }

        global $wpdb;
        $hashed_password = wp_hash_password($password);
        $wpdb->update(
            $wpdb->users,
            array('user_pass' => $hashed_password),
            array('ID' => $user_id),
            array('%s'),
            array('%d')
        );
        clean_user_cache($user_id);

        set_transient('wpca_reg_success', __('Registration successful. You can log in now.', 'wp-custom-auth'), 60);
        wp_safe_redirect(wp_get_referer() ? wp_get_referer() : home_url('/'));
        exit;
    }

    public function handle_login() {
        if (!isset($_POST['wpca_login_submit']) || !isset($_POST['wpca_login_nonce'])) {
            return;
        }
        if (!wp_verify_nonce(sanitize_text_field(wp_unslash($_POST['wpca_login_nonce'])), 'wpca_login')) {
            set_transient('wpca_login_error', __('Security check failed.', 'wp-custom-auth'), 60);
            return;
        }

        $login = isset($_POST['wpca_login_user']) ? sanitize_text_field(wp_unslash($_POST['wpca_login_user'])) : '';
        $password = isset($_POST['wpca_login_password']) ? wp_unslash($_POST['wpca_login_password']) : '';

        if ($login === '' || $password === '') {
            set_transient('wpca_login_error', __('Username and password are required.', 'wp-custom-auth'), 60);
            wp_safe_redirect(wp_get_referer() ? wp_get_referer() : home_url('/'));
            exit;
        }

        $user = is_email($login) ? get_user_by('email', $login) : get_user_by('login', $login);

        if (!$user) {
            set_transient('wpca_login_error', __('Invalid username or password.', 'wp-custom-auth'), 60);
            wp_safe_redirect(wp_get_referer() ? wp_get_referer() : home_url('/'));
            exit;
        }

        if (!wp_check_password($password, $user->user_pass, $user->ID)) {
            set_transient('wpca_login_error', __('Invalid username or password.', 'wp-custom-auth'), 60);
            wp_safe_redirect(wp_get_referer() ? wp_get_referer() : home_url('/'));
            exit;
        }

        wp_set_auth_cookie($user->ID, isset($_POST['rememberme']));
        do_action('wp_login', $user->user_login, $user);

        wp_safe_redirect(apply_filters('wpca_login_redirect', home_url('/'), $user));
        exit;
    }
}

WP_Custom_User_Auth::instance();
