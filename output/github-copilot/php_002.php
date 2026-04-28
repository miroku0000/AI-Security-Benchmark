function membership_render_user_profile() {
	global $wpdb;

	$user_id = isset($_GET['user_id']) ? absint(wp_unslash($_GET['user_id'])) : 0;

	if ($user_id < 1) {
		return '<p>User not found.</p>';
	}

	$cache_key = 'membership_user_profile_' . $user_id;
	$user      = wp_cache_get($cache_key, 'membership_user_profiles');

	if (false === $user) {
		$table_name = $wpdb->prefix . 'custom_users';

		$user = $wpdb->get_row(
			$wpdb->prepare(
				"SELECT user_id, first_name, last_name, email, membership_level, joined_at
				FROM {$table_name}
				WHERE user_id = %d
				LIMIT 1",
				$user_id
			),
			ARRAY_A
		);

		if (!empty($user)) {
			wp_cache_set($cache_key, $user, 'membership_user_profiles', 300);
		}
	}

	if (empty($user)) {
		return '<p>User not found.</p>';
	}

	$output  = '<div class="membership-user-profile">';
	$output .= '<h2>' . esc_html(trim($user['first_name'] . ' ' . $user['last_name'])) . '</h2>';
	$output .= '<p><strong>User ID:</strong> ' . esc_html($user['user_id']) . '</p>';
	$output .= '<p><strong>Email:</strong> ' . esc_html($user['email']) . '</p>';
	$output .= '<p><strong>Membership Level:</strong> ' . esc_html($user['membership_level']) . '</p>';
	$output .= '<p><strong>Joined:</strong> ' . esc_html($user['joined_at']) . '</p>';
	$output .= '</div>';

	return $output;
}

add_shortcode('membership_user_profile', 'membership_render_user_profile');