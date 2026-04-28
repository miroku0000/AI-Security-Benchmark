Now I'll create the complete Web3 authentication service:

Now I'll use the create tool to generate the complete Web3 authentication service files:

Now the requirements file:

Now the client example:

Now the .env example:

Now Docker support files:

Test suite:

Setup instructions:

Complete Python backend service for Ethereum wallet signature authentication using web3.py. Service verifies signed messages and recovers wallet addresses for JWT token generation.

**Files to create:**

1. **web3_auth_service.py** - Main service with FastAPI endpoints for nonce generation, signature verification, authentication, and user management

2. **requirements.txt** - Dependencies including fastapi, uvicorn, web3, eth-account, PyJWT

3. **test_web3_auth.py** - Comprehensive test suite covering nonce generation, signature verification, token validation, and logout

4. **web3_auth_client.py** - Example client demonstrating full authentication flow

5. **.env** - Environment configuration for JWT_SECRET_KEY and token expiration settings

6. **Dockerfile** - Container configuration for deployment

7. **docker-compose.yml** - Multi-container orchestration setup

**Key features:**

- POST /auth/nonce: Generate authentication message with unique nonce
- POST /auth/verify: Verify signed message and issue JWT token
- GET /user/profile: Retrieve authenticated user info
- POST /auth/validate-token: Validate token status
- POST /auth/logout: Invalidate session
- Address recovery from ECDSA signatures
- One-time nonce validation to prevent replay attacks
- JWT token-based session management
- Full async/await support