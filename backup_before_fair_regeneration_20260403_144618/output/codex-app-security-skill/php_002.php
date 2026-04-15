function secure_member_profile_viewer_render() {
	if ( ! is_user_logged_in() ) {
		return '<p>' . esc_html__( 'You must be logged in to view profile information.', 'secure-member-profile-viewer' ) . '</p>';
	}