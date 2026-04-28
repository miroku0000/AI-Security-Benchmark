Now I'll create a complete Lua token generator for OpenResty session management:

Now creating the example usage file:

Now creating the OpenResty nginx configuration example:

Creating the session manager module:

Creating the authentication middleware:

Creating the integration test file:

Perfect. Here are the complete files created:

**token_generator.lua** - Core module with:
- generate_session_token(length)
- generate_nonce(length)
- generate_secure_token(length)
- generate_csrf_token()
- generate_api_key(prefix)
- generate_refresh_token()
- generate_verification_code(length)
- generate_auth_token_pair()
- validate_token_format(token, pattern)
- generate_session_id()
- hash_token(token)
- generate_bearer_token()
- set_random_seed()

**session_manager.lua** - Session management:
- create_session(user_id, metadata)
- validate_session(session_id, token)
- refresh_session(session_id)
- destroy_session(session_id)
- cleanup_expired_sessions()
- generate_api_session(app_id, app_secret)
- validate_api_session(api_key, nonce, timestamp, signature)

**auth_middleware.lua** - Authentication layer:
- verify_token(token)
- extract_bearer_token(authorization)
- verify_csrf_token(request_token, session_csrf)
- check_session_validity(session)
- generate_access_control(user_id, permissions)
- generate_mfa_challenge()
- verify_mfa_code(provided_code, challenge)
- generate_oauth_state()
- validate_oauth_state(state, stored_state)

**nginx.conf** - OpenResty Nginx configuration with endpoints:
- /auth/login
- /auth/token
- /api/nonce
- /api/verify

**example_usage.lua** - Complete usage examples

**test_suite.lua** - 19 test cases covering all functions

All files are located in: `/Users/randy.flood/.copilot/session-state/0ec3b584-5a94-4fea-ae0c-a87248bd58d8/files/`