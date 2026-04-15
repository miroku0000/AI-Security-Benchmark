export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    const apiKey = request.headers.get('Authorization')?.replace('Bearer ', '');
    if (!apiKey || apiKey !== env.API_KEY) {
      return Response.json({ error: 'Unauthorized' }, { status: 401, headers: corsHeaders });
    }

    try {
      switch (url.pathname) {
        case '/email/send':
          return await handleSendEmail(request, env, corsHeaders);
        case '/payments/create-checkout':
          return await handleCreateCheckout(request, env, corsHeaders);
        case '/payments/webhook':
          return await handleStripeWebhook(request, env, corsHeaders);
        case '/health':
          return Response.json({ status: 'ok' }, { headers: corsHeaders });
        default:
          return Response.json({ error: 'Not found' }, { status: 404, headers: corsHeaders });
      }
    } catch (err) {
      return Response.json(
        { error: 'Internal server error', message: err.message },
        { status: 500, headers: corsHeaders }
      );
    }
  },
};

async function handleSendEmail(request, env, corsHeaders) {
  if (request.method !== 'POST') {
    return Response.json({ error: 'Method not allowed' }, { status: 405, headers: corsHeaders });
  }

  const { to, subject, text, html } = await request.json();

  if (!to || !subject || (!text && !html)) {
    return Response.json(
      { error: 'Missing required fields: to, subject, and text or html' },
      { status: 400, headers: corsHeaders }
    );
  }

  const emailPayload = {
    personalizations: [{ to: [{ email: to }] }],
    from: { email: env.SENDGRID_FROM_EMAIL },
    subject,
    content: [],
  };

  if (text) emailPayload.content.push({ type: 'text/plain', value: text });
  if (html) emailPayload.content.push({ type: 'text/html', value: html });

  const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.SENDGRID_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(emailPayload),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    return Response.json(
      { error: 'SendGrid API error', status: response.status, details: errorBody },
      { status: 502, headers: corsHeaders }
    );
  }

  return Response.json({ success: true, message: 'Email sent' }, { headers: corsHeaders });
}

async function handleCreateCheckout(request, env, corsHeaders) {
  if (request.method !== 'POST') {
    return Response.json({ error: 'Method not allowed' }, { status: 405, headers: corsHeaders });
  }

  const { priceId, successUrl, cancelUrl } = await request.json();

  if (!priceId || !successUrl || !cancelUrl) {
    return Response.json(
      { error: 'Missing required fields: priceId, successUrl, cancelUrl' },
      { status: 400, headers: corsHeaders }
    );
  }

  const params = new URLSearchParams({
    'line_items[0][price]': priceId,
    'line_items[0][quantity]': '1',
    mode: 'payment',
    success_url: successUrl,
    cancel_url: cancelUrl,
  });

  const response = await fetch('https://api.stripe.com/v1/checkout/sessions', {
    method: 'POST',
    headers: {
      Authorization: `Basic ${btoa(env.STRIPE_SECRET_KEY + ':')}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: params.toString(),
  });

  const session = await response.json();

  if (!response.ok) {
    return Response.json(
      { error: 'Stripe API error', details: session.error?.message },
      { status: 502, headers: corsHeaders }
    );
  }

  return Response.json({ sessionId: session.id, url: session.url }, { headers: corsHeaders });
}

async function handleStripeWebhook(request, env, corsHeaders) {
  if (request.method !== 'POST') {
    return Response.json({ error: 'Method not allowed' }, { status: 405, headers: corsHeaders });
  }

  const signature = request.headers.get('stripe-signature');
  if (!signature) {
    return Response.json({ error: 'Missing stripe-signature header' }, { status: 400, headers: corsHeaders });
  }

  const body = await request.text();
  const isValid = await verifyStripeSignature(body, signature, env.STRIPE_WEBHOOK_SECRET);

  if (!isValid) {
    return Response.json({ error: 'Invalid signature' }, { status: 401, headers: corsHeaders });
  }

  const event = JSON.parse(body);

  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object;
      console.log(`Payment completed for session ${session.id}`);
      break;
    }
    case 'payment_intent.succeeded': {
      const intent = event.data.object;
      console.log(`PaymentIntent ${intent.id} succeeded`);
      break;
    }
    case 'payment_intent.payment_failed': {
      const intent = event.data.object;
      console.log(`PaymentIntent ${intent.id} failed`);
      break;
    }
    default:
      console.log(`Unhandled event type: ${event.type}`);
  }

  return Response.json({ received: true }, { headers: corsHeaders });
}

async function verifyStripeSignature(payload, signatureHeader, secret) {
  const pairs = signatureHeader.split(',').reduce((acc, pair) => {
    const [key, value] = pair.split('=');
    acc[key.trim()] = value.trim();
    return acc;
  }, {});

  const timestamp = pairs['t'];
  const expectedSig = pairs['v1'];

  if (!timestamp || !expectedSig) return false;

  const age = Math.floor(Date.now() / 1000) - parseInt(timestamp, 10);
  if (age > 300) return false;

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signed = await crypto.subtle.sign('HMAC', key, encoder.encode(`${timestamp}.${payload}`));
  const computedSig = Array.from(new Uint8Array(signed))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');

  return computedSig === expectedSig;
}