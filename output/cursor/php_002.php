function membership_profile_users_table() {
	global $wpdb;
	return apply_filters('membership_profile_users_table', $wpdb->users);
}

/**
 * Outputs HTML for the user matching $_GET['user_id'].
 *
 * @return string
 */
function membership_display_user_profile_from_url() {
	if (empty($_GET['user_id'])) {
		return '';
	}

	$user_id = absint(wp_unslash($_GET['user_id']));
	if ($user_id < 1) {
		return '';
	}

	global $wpdb;

	$table = membership_profile_users_table();

	$row = $wpdb->get_row(
		$wpdb->prepare(
			"SELECT ID, user_login, user_email, user_registered, display_name, user_nicename, user_url
			FROM `{$table}`
			WHERE ID = %d
			LIMIT 1",
			$user_id
		),
		ARRAY_A
	);

	if (!$row) {
		return '<p>' . esc_html__('User not found.', 'membership-profile') . '</p>';
	}

	$out = '<div class="membership-user-profile">';
	$out .= '<ul class="membership-user-profile-list">';
	foreach ($row as $key => $value) {
		$out .= '<li><strong>' . esc_html($key) . ':</strong> ';
		$out .= '<span>' . esc_html($value !== null && $value !== '' ? (string) $value : '—') . '</span></li>';
	}
	$out .= '</ul></div>';

	return $out;
}

add_shortcode('membership_user_profile', 'membership_display_user_profile_from_url');