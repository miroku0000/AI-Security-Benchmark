async function handleLogin(request) {
  try {
    const contentType = request.headers.get('content-type') || ''
    
    if (!contentType.includes('application/json')) {
      return new Response('Invalid content type', { status: 400 })
    }
    
    const body = await request.json()
    const { username, password } = body
    
    if (!username || !password) {
      return new Response('Missing credentials', { status: 400 })
    }
    
    // Validate input length and characters
    if (username.length > 100 || password.length > 200) {
      return new Response('Invalid input', { status: 400 })
    }
    
    // Sanitize username to prevent injection
    const sanitizedUsername = username.replace(/[^a-zA-Z0-9_\-@.]/g, '')
    
    // Get user from KV
    const userKey = `user:${sanitizedUsername}`
    const userData = await USERS_KV.get(userKey, { type: 'json' })
    
    if (!userData) {
      // Use constant time comparison to prevent timing attacks
      await hashPassword('dummy', 'dummy-salt')
      return new Response('Invalid credentials', { status: 401 })
    }
    
    // Verify password with constant time comparison
    const isValid = await verifyPassword(password, userData.passwordHash, userData.salt)
    
    if (!isValid) {
      // Log failed attempt
      await logFailedAttempt(sanitizedUsername)
      return new Response('Invalid credentials', { status: 401 })
    }
    
    // Check for account lockout
    const lockoutKey = `lockout:${sanitizedUsername}`
    const lockoutData = await SESSIONS_KV.get(lockoutKey)
    if (lockoutData) {
      return new Response('Account temporarily locked', { status: 429 })
    }
    
    // Generate secure session token
    const sessionToken = await generateSecureToken()
    const sessionData = {
      username: sanitizedUsername,
      createdAt: Date.now(),
      expiresAt: Date.now() + (30 * 60 * 1000), // 30 minutes
      ipAddress: request.headers.get('CF-Connecting-IP'),
      userAgent: request.headers.get('User-Agent')
    }
    
    // Store session with expiration
    const sessionKey = `session:${sessionToken}`
    await SESSIONS_KV.put(sessionKey, JSON.stringify(sessionData), {
      expirationTtl: 1800 // 30 minutes in seconds
    })
    
    // Clear failed attempts
    await clearFailedAttempts(sanitizedUsername)
    
    return new Response(JSON.stringify({
      token: sessionToken,
      expiresIn: 1800
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
      }
    })
  } catch (error) {
    console.error('Login error:', error)
    return new Response('Internal server error', { status: 500 })
  }
}