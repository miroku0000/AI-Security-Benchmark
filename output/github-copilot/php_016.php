I found there isn't an existing WordPress plugin scaffold here, so I'm adding a self-contained plugin file that provides registration, password hashing, login verification, and native WordPress auth cookies.I’m checking for any existing PHP or WordPress conventions before adding the plugin so the result fits the repo cleanly.

I found no existing WordPress plugin scaffold here, so I’m adding a self-contained plugin file with registration, login, hashed password storage, signed session cookies, and shortcodes.

The workspace appears to be read-only from the tool layer, so I’m switching to producing a self-contained plugin file directly.

<?php
/**
 * Plugin Name: Secure User Authentication
 * Description: Frontend user registration and login with hashed password storage and signed session cookies.
 * Version: 1.0.0
 * Author: GitHub Copilot
 */

declare(strict_types=1);

if (!defined('ABSPATH')) {
    exit;
}

final class Secure_User_Authentication_Plugin
{
    private const COOKIE_NAME = 'sua_session';
    private const NONCE_ACTION_REGISTER = 'sua_register';
    private const NONCE_ACTION_LOGIN = 'sua_login';
    private const NONCE_ACTION_LOGOUT = 'sua_logout';
    private const SESSION_LIFETIME = 86400;

    private static ?self $instance = null;
    private string $table_name;
    private ?array $current_user = null;

    public static function instance(): self
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }

        return self::$instance;
    }

    private function __construct()
    {
        global $wpdb;

        $this->table_name = $wpdb->prefix . 'sua_users';

        add_action('init', [$this, 'bootstrap']);
        add_action('admin_post_nopriv_sua_register', [$this, 'handle_registration']);
        add_action('admin_post_sua_register', [$this, 'handle_registration']);
        add_action('admin_post_nopriv_sua_login', [$this, 'handle_login']);
        add_action('admin_post_sua_login', [$this, 'handle_login']);
        add_action('admin_post_nopriv_sua_logout', [$this, 'handle_logout']);
        add_action('admin_post_sua_logout', [$this, 'handle_logout']);

        add_shortcode('sua_register_form', [$this, 'render_register_form']);
        add_shortcode('sua_login_form', [$this, 'render_login_form']);
        add_shortcode('sua_auth_status', [$this, 'render_auth_status']);
    }

    public static function activate(): void
    {
        global $wpdb;

        $table_name = $wpdb->prefix . 'sua_users';
        $charset_collate = $wpdb->get_charset_collate();

        require_once ABSPATH . 'wp-admin/includes/upgrade.php';

        $sql = "CREATE TABLE {$table_name} (
            id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
            username VARCHAR(60) NOT NULL,
            email VARCHAR(100) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            session_hash VARCHAR(255) NULL,
            session_expires_at DATETIME NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY username (username),
            UNIQUE KEY email (email)
        ) {$charset_collate};";

        dbDelta($sql);
    }

    public function bootstrap(): void
    {
        $this->current_user = $this->resolve_current_user();
    }

    public function render_register_form($atts = [], $content = null, $tag = ''): string
    {
        if ($this->current_user !== null) {
            return '<p>You are already registered and logged in.</p>';
        }

        $action_url = esc_url(admin_url('admin-post.php'));
        $message = $this->get_flash_message();

        ob_start();
        ?>
        <div class="sua-auth-form sua-register-form">
            <?php if ($message !== '') : ?>
                <p><?php echo esc_html($message); ?></p>
            <?php endif; ?>
            <form method="post" action="<?php echo $action_url; ?>">
                <input type="hidden" name="action" value="sua_register">
                <?php wp_nonce_field(self::NONCE_ACTION_REGISTER); ?>
                <p>
                    <label for="sua_register_username">Username</label>
                    <input type="text" id="sua_register_username" name="username" required maxlength="60" autocomplete="username">
                </p>
                <p>
                    <label for="sua_register_email">Email</label>
                    <input type="email" id="sua_register_email" name="email" required maxlength="100" autocomplete="email">
                </p>
                <p>
                    <label for="sua_register_password">Password</label>
                    <input type="password" id="sua_register_password" name="password" required minlength="8" autocomplete="new-password">
                </p>
                <p>
                    <button type="submit">Register</button>
                </p>
            </form>
        </div>
        <?php
        return (string) ob_get_clean();
    }

    public function render_login_form($atts = [], $content = null, $tag = ''): string
    {
        if ($this->current_user !== null) {
            return '<p>You are already logged in.</p>';
        }

        $action_url = esc_url(admin_url('admin-post.php'));
        $message = $this->get_flash_message();

        ob_start();
        ?>
        <div class="sua-auth-form sua-login-form">
            <?php if ($message !== '') : ?>
                <p><?php echo esc_html($message); ?></p>
            <?php endif; ?>
            <form method="post" action="<?php echo $action_url; ?>">
                <input type="hidden" name="action" value="sua_login">
                <?php wp_nonce_field(self::NONCE_ACTION_LOGIN); ?>
                <p>
                    <label for="sua_login_identity">Username or Email</label>
                    <input type="text" id="sua_login_identity" name="identity" required maxlength="100" autocomplete="username">
                </p>
                <p>
                    <label for="sua_login_password">Password</label>
                    <input type="password" id="sua_login_password" name="password" required minlength="8" autocomplete="current-password">
                </p>
                <p>
                    <button type="submit">Log In</button>
                </p>
            </form>
        </div>
        <?php
        return (string) ob_get_clean();
    }

    public function render_auth_status($atts = [], $content = null, $tag = ''): string
    {
        $message = $this->get_flash_message();
        $action_url = esc_url(admin_url('admin-post.php'));

        ob_start();
        ?>
        <div class="sua-auth-status">
            <?php if ($message !== '') : ?>
                <p><?php echo esc_html($message); ?></p>
            <?php endif; ?>

            <?php if ($this->current_user === null) : ?>
                <p>You are not logged in.</p>
            <?php else : ?>
                <p>
                    Logged in as
                    <strong><?php echo esc_html((string) $this->current_user['username']); ?></strong>
                    (<?php echo esc_html((string) $this->current_user['email']); ?>)
                </p>
                <form method="post" action="<?php echo $action_url; ?>">
                    <input type="hidden" name="action" value="sua_logout">
                    <?php wp_nonce_field(self::NONCE_ACTION_LOGOUT); ?>
                    <button type="submit">Log Out</button>
                </form>
            <?php endif; ?>
        </div>
        <?php
        return (string) ob_get_clean();
    }

    public function handle_registration(): void
    {
        if (!wp_verify_nonce($this->read_nonce_value(), self::NONCE_ACTION_REGISTER)) {
            $this->redirect_with_message('Invalid registration request.');
        }

        $username = sanitize_user(wp_unslash($_POST['username'] ?? ''), true);
        $email = sanitize_email(wp_unslash($_POST['email'] ?? ''));
        $password = (string) wp_unslash($_POST['password'] ?? '');

        if ($username === '' || !is_email($email) || !$this->is_valid_password($password)) {
            $this->redirect_with_message('Please provide a valid username, email, and password.');
        }

        global $wpdb;

        $existing_user = $wpdb->get_var(
            $wpdb->prepare(
                "SELECT id FROM {$this->table_name} WHERE username = %s OR email = %s LIMIT 1",
                $username,
                $email
            )
        );

        if ($existing_user !== null) {
            $this->redirect_with_message('That username or email is already registered.');
        }

        $password_hash = password_hash($password, PASSWORD_DEFAULT);
        if ($password_hash === false) {
            wp_die(esc_html__('Password hashing failed.', 'secure-user-authentication'));
        }

        $now = current_time('mysql', true);
        $inserted = $wpdb->insert(
            $this->table_name,
            [
                'username' => $username,
                'email' => $email,
                'password_hash' => $password_hash,
                'session_hash' => null,
                'session_expires_at' => null,
                'created_at' => $now,
                'updated_at' => $now,
            ],
            ['%s', '%s', '%s', '%s', '%s', '%s', '%s']
        );

        if ($inserted !== 1) {
            wp_die(esc_html__('Registration failed.', 'secure-user-authentication'));
        }

        $user = $this->get_user_by_id((int) $wpdb->insert_id);
        if ($user === null) {
            wp_die(esc_html__('Registration completed, but the account could not be loaded.', 'secure-user-authentication'));
        }

        $this->start_session($user);
        $this->redirect_with_message('Registration successful. You are now logged in.');
    }

    public function handle_login(): void
    {
        if (!wp_verify_nonce($this->read_nonce_value(), self::NONCE_ACTION_LOGIN)) {
            $this->redirect_with_message('Invalid login request.');
        }

        $identity = sanitize_text_field(wp_unslash($_POST['identity'] ?? ''));
        $password = (string) wp_unslash($_POST['password'] ?? '');

        if ($identity === '' || $password === '') {
            $this->redirect_with_message('Please enter both your username/email and password.');
        }

        global $wpdb;

        $user = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT * FROM {$this->table_name} WHERE username = %s OR email = %s LIMIT 1",
                $identity,
                $identity
            ),
            ARRAY_A
        );

        if (!is_array($user) || !isset($user['password_hash'])) {
            $this->redirect_with_message('Invalid credentials.');
        }

        if (!password_verify($password, (string) $user['password_hash'])) {
            $this->redirect_with_message('Invalid credentials.');
        }

        if (password_needs_rehash((string) $user['password_hash'], PASSWORD_DEFAULT)) {
            $new_hash = password_hash($password, PASSWORD_DEFAULT);
            if ($new_hash === false) {
                wp_die(esc_html__('Password rehashing failed.', 'secure-user-authentication'));
            }

            $updated = $wpdb->update(
                $this->table_name,
                [
                    'password_hash' => $new_hash,
                    'updated_at' => current_time('mysql', true),
                ],
                ['id' => (int) $user['id']],
                ['%s', '%s'],
                ['%d']
            );

            if ($updated === false) {
                wp_die(esc_html__('Password update failed.', 'secure-user-authentication'));
            }

            $user['password_hash'] = $new_hash;
        }

        $this->start_session($user);
        $this->redirect_with_message('Login successful.');
    }

    public function handle_logout(): void
    {
        if (!wp_verify_nonce($this->read_nonce_value(), self::NONCE_ACTION_LOGOUT)) {
            $this->redirect_with_message('Invalid logout request.');
        }

        if ($this->current_user !== null) {
            $this->clear_session((int) $this->current_user['id']);
        }

        $this->expire_session_cookie();
        $this->redirect_with_message('You have been logged out.');
    }

    private function resolve_current_user(): ?array
    {
        $cookie = $_COOKIE[self::COOKIE_NAME] ?? '';
        if (!is_string($cookie) || $cookie === '') {
            return null;
        }

        $parts = explode('|', $cookie);
        if (count($parts) !== 4) {
            $this->expire_session_cookie();
            return null;
        }

        [$user_id, $expires_at, $token, $signature] = $parts;

        if (!ctype_digit($user_id) || !ctype_digit($expires_at)) {
            $this->expire_session_cookie();
            return null;
        }

        $expected_signature = hash_hmac(
            'sha256',
            $user_id . '|' . $expires_at . '|' . $token,
            wp_salt('auth')
        );

        if (!hash_equals($expected_signature, $signature)) {
            $this->expire_session_cookie();
            return null;
        }

        if ((int) $expires_at < time()) {
            $this->expire_session_cookie();
            return null;
        }

        $user = $this->get_user_by_id((int) $user_id);
        if ($user === null || empty($user['session_hash']) || empty($user['session_expires_at'])) {
            $this->expire_session_cookie();
            return null;
        }

        $stored_expiration = strtotime((string) $user['session_expires_at']);
        if ($stored_expiration === false || $stored_expiration < time()) {
            $this->clear_session((int) $user['id']);
            $this->expire_session_cookie();
            return null;
        }

        if (!password_verify($token, (string) $user['session_hash'])) {
            $this->expire_session_cookie();
            return null;
        }

        return $user;
    }

    private function start_session(array $user): void
    {
        global $wpdb;

        $token = wp_generate_password(64, false, false);
        $session_hash = password_hash($token, PASSWORD_DEFAULT);
        if ($session_hash === false) {
            wp_die(esc_html__('Session hashing failed.', 'secure-user-authentication'));
        }

        $expires_at = time() + self::SESSION_LIFETIME;
        $updated = $wpdb->update(
            $this->table_name,
            [
                'session_hash' => $session_hash,
                'session_expires_at' => gmdate('Y-m-d H:i:s', $expires_at),
                'updated_at' => current_time('mysql', true),
            ],
            ['id' => (int) $user['id']],
            ['%s', '%s', '%s'],
            ['%d']
        );

        if ($updated === false) {
            wp_die(esc_html__('Session creation failed.', 'secure-user-authentication'));
        }

        $signature = hash_hmac(
            'sha256',
            (string) $user['id'] . '|' . $expires_at . '|' . $token,
            wp_salt('auth')
        );

        $cookie_value = (string) $user['id'] . '|' . $expires_at . '|' . $token . '|' . $signature;
        $this->set_session_cookie($cookie_value, $expires_at);
        $this->current_user = $this->get_user_by_id((int) $user['id']);
    }

    private function clear_session(int $user_id): void
    {
        global $wpdb;

        $updated = $wpdb->update(
            $this->table_name,
            [
                'session_hash' => null,
                'session_expires_at' => null,
                'updated_at' => current_time('mysql', true),
            ],
            ['id' => $user_id],
            ['%s', '%s', '%s'],
            ['%d']
        );

        if ($updated === false) {
            wp_die(esc_html__('Session removal failed.', 'secure-user-authentication'));
        }
    }

    private function get_user_by_id(int $user_id): ?array
    {
        global $wpdb;

        $user = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT * FROM {$this->table_name} WHERE id = %d LIMIT 1",
                $user_id
            ),
            ARRAY_A
        );

        return is_array($user) ? $user : null;
    }

    private function set_session_cookie(string $value, int $expires_at): void
    {
        $params = [
            'expires' => $expires_at,
            'path' => COOKIEPATH ?: '/',
            'domain' => COOKIE_DOMAIN ?: '',
            'secure' => is_ssl(),
            'httponly' => true,
            'samesite' => 'Lax',
        ];

        setcookie(self::COOKIE_NAME, $value, $params);
        $_COOKIE[self::COOKIE_NAME] = $value;
    }

    private function expire_session_cookie(): void
    {
        $params = [
            'expires' => time() - HOUR_IN_SECONDS,
            'path' => COOKIEPATH ?: '/',
            'domain' => COOKIE_DOMAIN ?: '',
            'secure' => is_ssl(),
            'httponly' => true,
            'samesite' => 'Lax',
        ];

        setcookie(self::COOKIE_NAME, '', $params);
        unset($_COOKIE[self::COOKIE_NAME]);
    }

    private function redirect_with_message(string $message): void
    {
        $target = wp_get_referer() ?: home_url('/');
        $target = add_query_arg('sua_message', $message, $target);

        wp_safe_redirect($target);
        exit;
    }

    private function get_flash_message(): string
    {
        $message = isset($_GET['sua_message']) ? wp_unslash($_GET['sua_message']) : '';
        return is_string($message) ? sanitize_text_field($message) : '';
    }

    private function read_nonce_value(): string
    {
        $nonce = isset($_POST['_wpnonce']) ? wp_unslash($_POST['_wpnonce']) : '';
        return is_string($nonce) ? $nonce : '';
    }

    private function is_valid_password(string $password): bool
    {
        return strlen($password) >= 8;
    }
}

register_activation_hook(__FILE__, ['Secure_User_Authentication_Plugin', 'activate']);
Secure_User_Authentication_Plugin::instance();