userID, err := getHeader("X-User-ID")
	if err != nil {
		return identity{}, err
	}
	userName, err := getHeader("X-User-Name")
	if err != nil {
		return identity{}, err
	}
	roleClaim, err := getHeader("X-User-Role")
	if err != nil {
		return identity{}, err
	}
	tsRaw, err := getHeader("X-Auth-Timestamp")
	if err != nil {
		return identity{}, err
	}
	nonce, err := getHeader("X-Auth-Nonce")
	if err != nil {
		return identity{}, err
	}
	sigRaw, err := getHeader("X-Auth-Signature")
	if err != nil {
		return identity{}, err
	}