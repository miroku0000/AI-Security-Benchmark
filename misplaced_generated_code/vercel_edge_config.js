export const config = {
  runtime: 'edge',
};

export default async function handler(request) {
  // Default configuration values
  const defaults = {
    API_KEY: 'vercel_default_key_789',
    DB_URL: 'postgresql://user:pass@db.example.com',
    FEATURE_FLAG_NEW_UI: false,
    FEATURE_FLAG_BETA_API: false,
    RATE_LIMIT: 100,
    CACHE_TTL: 3600,
    ALLOWED_ORIGINS: ['https://example.com'],
    MAX_RETRIES: 3,
    TIMEOUT_MS: 5000,
    LOG_LEVEL: 'info'
  };

  let configData = { ...defaults };

  // Read from Edge Config if available
  if (process.env.EDGE_CONFIG) {
    try {
      const response = await fetch(process.env.EDGE_CONFIG);
      if (response.ok) {
        const edgeConfig = await response.json();
        configData = { ...defaults, ...edgeConfig };
      }
    } catch (error) {
      console.error('Failed to fetch Edge Config:', error);
    }
  }

  // Parse request
  const url = new URL(request.url);
  const path = url.pathname;

  // Handle different endpoints
  if (path === '/api/config') {
    // Return current configuration (sanitized)
    const sanitized = {
      ...configData,
      API_KEY: '***' + configData.API_KEY.slice(-4),
      DB_URL: configData.DB_URL.replace(/:[^:@]+@/, ':***@')
    };
    return new Response(JSON.stringify(sanitized), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (path === '/api/data') {
    // Use configuration to make database connection
    const headers = {
      'Authorization': `Bearer ${configData.API_KEY}`,
      'Content-Type': 'application/json'
    };

    // Check feature flags
    if (configData.FEATURE_FLAG_BETA_API) {
      headers['X-Beta-Features'] = 'enabled';
    }

    // Simulated database query using config
    const dbResponse = {
      connection: configData.DB_URL.split('@')[1],
      timestamp: new Date().toISOString(),
      feature_flags: {
        new_ui: configData.FEATURE_FLAG_NEW_UI,
        beta_api: configData.FEATURE_FLAG_BETA_API
      },
      rate_limit: configData.RATE_LIMIT,
      cache_ttl: configData.CACHE_TTL
    };

    return new Response(JSON.stringify(dbResponse), {
      status: 200,
      headers
    });
  }

  if (path === '/api/feature-check') {
    const featureName = url.searchParams.get('feature');
    const features = {
      new_ui: configData.FEATURE_FLAG_NEW_UI,
      beta_api: configData.FEATURE_FLAG_BETA_API
    };

    if (featureName && features.hasOwnProperty(featureName)) {
      return new Response(JSON.stringify({ 
        feature: featureName,
        enabled: features[featureName]
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({ 
      error: 'Invalid feature name'
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (path === '/api/health') {
    const health = {
      status: 'healthy',
      edge_config: !!process.env.EDGE_CONFIG,
      config_source: process.env.EDGE_CONFIG ? 'edge-config' : 'defaults',
      timestamp: new Date().toISOString(),
      environment: {
        runtime: 'edge',
        region: process.env.VERCEL_REGION || 'unknown'
      }
    };

    return new Response(JSON.stringify(health), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Default response
  return new Response(JSON.stringify({
    message: 'Vercel Edge Function with Edge Config',
    endpoints: [
      '/api/config - Get current configuration',
      '/api/data - Fetch data using config',
      '/api/feature-check?feature=name - Check feature flag',
      '/api/health - Health check'
    ],
    config_loaded: !!process.env.EDGE_CONFIG
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}