func validateSessionContents(s *Session) error {
	if s == nil {
		return errors.New("nil session")
	}
	if !userIDPattern.MatchString(s.UserID) {
		return errors.New("invalid session user_id")
	}
	if len(s.Preferences) > maxPreferenceCount {
		return errors.New("too many session preferences")
	}
	for k, v := range s.Preferences {
		if !preferenceKeyPat.MatchString(k) {
			return errors.New("invalid session preference key")
		}
		if len(v) == 0 || len(v) > maxPreferenceValLen || strings.ContainsAny(v, "\x00\r\n") {
			return errors.New("invalid session preference value")
		}
	}
	if len(s.Permissions) > maxPermissionCount {
		return errors.New("too many session permissions")
	}
	for _, p := range s.Permissions {
		if !permissionValuePat.MatchString(p) {
			return errors.New("invalid session permission")
		}
	}
	if s.CreatedAt.IsZero() || s.ExpiresAt.IsZero() || s.LastActivity.IsZero() {
		return errors.New("invalid session timestamps")
	}
	if !s.ExpiresAt.After(s.CreatedAt) {
		return errors.New("invalid session expiry")
	}
	return nil
}