worker.js:
import { Router } from 'itty-router';
import { json } from 'itty-router-extras';

const router = Router();

async function generateSessionToken() {
  const randomValues = crypto.getRandomValues(new Uint8Array(32));
  return Array.from(randomValues)
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('');
}

async function hashPassword(password, salt) {
  const encoder = new TextEncoder();
  const data = encoder.encode(password + salt);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

router.post('/auth/login', async (request, env) => {
  try {
    const body = await request.json();
    const { username, password } = body;

    if (!username || !password) {
      return json({ error: 'Missing username or password' }, { status: 400 });
    }

    const userKey = `user:${username}`;
    const userData = await env.AUTH_KV.get(userKey);

    if (!userData) {
      return json({ error: 'Invalid credentials' }, { status: 401 });
    }

    const user = JSON.parse(userData);
    const salt = user.salt || 'default_salt';
    const hashedPassword = await hashPassword(password, salt);

    if (hashedPassword !== user.passwordHash) {
      return json({ error: 'Invalid credentials' }, { status: 401 });
    }

    const sessionToken = await generateSessionToken();
    const sessionExpiry = Date.now() + 24 * 60 * 60 * 1000;

    const sessionData = {
      username,
      createdAt: Date.now(),
      expiresAt: sessionExpiry,
      userId: user.id
    };

    await env.AUTH_KV.put(
      `session:${sessionToken}`,
      JSON.stringify(sessionData),
      { expirationTtl: 86400 }
    );

    return json({
      success: true,
      sessionToken,
      expiresAt: sessionExpiry,
      userId: user.id
    });
  } catch (error) {
    return json({ error: 'Authentication failed', details: error.message }, { status: 500 });
  }
});

router.post('/auth/validate', async (request, env) => {
  try {
    const body = await request.json();
    const { sessionToken } = body;

    if (!sessionToken) {
      return json({ error: 'Missing session token' }, { status: 400 });
    }

    const sessionData = await env.AUTH_KV.get(`session:${sessionToken}`);

    if (!sessionData) {
      return json({ error: 'Invalid or expired token' }, { status: 401 });
    }

    const session = JSON.parse(sessionData);

    if (Date.now() > session.expiresAt) {
      await env.AUTH_KV.delete(`session:${sessionToken}`);
      return json({ error: 'Token expired' }, { status: 401 });
    }

    return json({
      valid: true,
      username: session.username,
      userId: session.userId,
      expiresAt: session.expiresAt
    });
  } catch (error) {
    return json({ error: 'Validation failed', details: error.message }, { status: 500 });
  }
});

router.post('/auth/logout', async (request, env) => {
  try {
    const body = await request.json();
    const { sessionToken } = body;

    if (!sessionToken) {
      return json({ error: 'Missing session token' }, { status: 400 });
    }

    await env.AUTH_KV.delete(`session:${sessionToken}`);

    return json({ success: true, message: 'Logged out successfully' });
  } catch (error) {
    return json({ error: 'Logout failed', details: error.message }, { status: 500 });
  }
});

router.post('/admin/register-user', async (request, env) => {
  try {
    const authHeader = request.headers.get('Authorization');
    const adminKey = env.ADMIN_API_KEY;

    if (!authHeader || authHeader !== `Bearer ${adminKey}`) {
      return json({ error: 'Unauthorized' }, { status: 403 });
    }

    const body = await request.json();
    const { username, password } = body;

    if (!username || !password) {
      return json({ error: 'Missing username or password' }, { status: 400 });
    }

    const userKey = `user:${username}`;
    const existingUser = await env.AUTH_KV.get(userKey);

    if (existingUser) {
      return json({ error: 'User already exists' }, { status: 409 });
    }

    const salt = crypto.getRandomValues(new Uint8Array(16)).toString();
    const passwordHash = await hashPassword(password, salt);
    const userId = crypto.getRandomValues(new Uint8Array(8)).toString();

    const userData = {
      id: userId,
      username,
      passwordHash,
      salt,
      createdAt: Date.now()
    };

    await env.AUTH_KV.put(userKey, JSON.stringify(userData));

    return json({
      success: true,
      userId,
      username
    });
  } catch (error) {
    return json({ error: 'Registration failed', details: error.message }, { status: 500 });
  }
});

router.get('/health', () => {
  return json({ status: 'healthy' });
});

router.all('*', () => json({ error: 'Not found' }, { status: 404 }));

export default {
  fetch: router.handle
};


wrangler.toml:
name = "auth-worker"
main = "src/worker.js"
compatibility_date = "2024-01-01"

[[env.production.kv_namespaces]]
binding = "AUTH_KV"
id = "your-production-kv-id"

[[env.staging.kv_namespaces]]
binding = "AUTH_KV"
id = "your-staging-kv-id"

[env.production]
vars = { ADMIN_API_KEY = "your-admin-key-production" }
route = "https://auth.yourdomain.com/*"
zone_id = "your-zone-id"

[env.staging]
vars = { ADMIN_API_KEY = "your-admin-key-staging" }
route = "https://auth-staging.yourdomain.com/*"
zone_id = "your-zone-id"

routes = [
  { pattern = "auth.yourdomain.com/*", zone_name = "yourdomain.com" }
]


package.json:
{
  "name": "auth-worker",
  "version": "1.0.0",
  "description": "Cloudflare Worker for edge authentication",
  "main": "src/worker.js",
  "scripts": {
    "dev": "wrangler dev",
    "deploy:staging": "wrangler publish --env staging",
    "deploy:production": "wrangler publish --env production",
    "test": "jest"
  },
  "dependencies": {
    "itty-router": "^3.0.0",
    "itty-router-extras": "^0.2.0"
  },
  "devDependencies": {
    "wrangler": "^3.0.0",
    "@cloudflare/wrangler": "^3.0.0"
  }
}


test.js:
import { Router } from 'itty-router';
import { json } from 'itty-router-extras';

global.crypto = {
  getRandomValues: (arr) => {
    for (let i = 0; i < arr.length; i++) {
      arr[i] = Math.floor(Math.random() * 256);
    }
    return arr;
  },
  subtle: {
    digest: async (algo, data) => {
      const hash = require('crypto').createHash('sha256');
      hash.update(Buffer.from(data));
      return hash.digest();
    }
  }
};

describe('Auth Worker', () => {
  let mockEnv;

  beforeEach(() => {
    mockEnv = {
      AUTH_KV: {
        get: jest.fn(),
        put: jest.fn(),
        delete: jest.fn()
      },
      ADMIN_API_KEY: 'test-admin-key'
    };
  });

  test('login with valid credentials', async () => {
    const userData = {
      id: 'user123',
      username: 'testuser',
      passwordHash: 'abcd1234',
      salt: 'salt123'
    };

    mockEnv.AUTH_KV.get.mockResolvedValue(JSON.stringify(userData));
    mockEnv.AUTH_KV.put.mockResolvedValue(undefined);

    const request = new Request('http://localhost/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        username: 'testuser',
        password: 'password123'
      })
    });

    expect(mockEnv.AUTH_KV.get).toHaveBeenCalled();
  });

  test('validate session token', async () => {
    const sessionData = {
      username: 'testuser',
      userId: 'user123',
      expiresAt: Date.now() + 3600000
    };

    mockEnv.AUTH_KV.get.mockResolvedValue(JSON.stringify(sessionData));

    const request = new Request('http://localhost/auth/validate', {
      method: 'POST',
      body: JSON.stringify({
        sessionToken: 'valid-token-123'
      })
    });

    expect(mockEnv.AUTH_KV.get).toHaveBeenCalledWith('session:valid-token-123');
  });
});


deployment.sh:
#!/bin/bash

set -e

ENV=${1:-staging}
ADMIN_KEY=${2:-}

if [ -z "$ADMIN_KEY" ]; then
  echo "Usage: ./deployment.sh [staging|production] <admin-api-key>"
  exit 1
fi

echo "Deploying to $ENV with admin key..."

wrangler secret put ADMIN_API_KEY --env "$ENV" <<< "$ADMIN_KEY"

npm run "deploy:$ENV"

echo "Deployment complete!"


setup.sh:
#!/bin/bash

npm install

wrangler kv:namespace create "auth-store" --preview false
wrangler kv:namespace create "auth-store" --preview true

echo "Setup complete. Created KV namespaces."
echo "Update wrangler.toml with namespace IDs from above."