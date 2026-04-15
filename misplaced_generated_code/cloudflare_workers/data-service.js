export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method;
    const path = url.pathname;

    if (!isAuthorizedInternalCall(request, env) && path !== '/data/health') {
      return new Response(JSON.stringify({ error: 'Forbidden' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (method === 'GET' && path === '/data/health') {
      return new Response(JSON.stringify({ ok: true, service: 'data-service' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const storage = {
      users: new Map([
        ['1', { id: '1', name: 'Alice Johnson', email: 'alice@example.com', role: 'admin', created: '2024-01-15' }],
        ['2', { id: '2', name: 'Bob Smith', email: 'bob@example.com', role: 'user', created: '2024-02-20' }],
        ['3', { id: '3', name: 'Charlie Brown', email: 'charlie@example.com', role: 'user', created: '2024-03-10' }]
      ]),
      products: new Map([
        ['p1', { id: 'p1', name: 'Product A', price: 99.99, stock: 100 }],
        ['p2', { id: 'p2', name: 'Product B', price: 149.99, stock: 50 }],
        ['p3', { id: 'p3', name: 'Product C', price: 199.99, stock: 25 }]
      ]),
      orders: new Map([
        ['o1', { id: 'o1', userId: '1', products: ['p1', 'p2'], total: 249.98, status: 'shipped' }],
        ['o2', { id: 'o2', userId: '2', products: ['p3'], total: 199.99, status: 'processing' }]
      ])
    };
    
    if (method === 'GET' && path.startsWith('/data/users/')) {
      const userId = path.split('/').pop();
      const user = storage.users.get(userId);
      
      if (!user) {
        return new Response(JSON.stringify({ error: 'User not found' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      return new Response(JSON.stringify(user), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'PUT' && path.startsWith('/data/users/')) {
      const userId = path.split('/').pop();
      const updates = await request.json();
      const existing = storage.users.get(userId);
      
      if (!existing) {
        return new Response(JSON.stringify({ error: 'User not found' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      const updated = { ...existing, ...updates, id: userId };
      storage.users.set(userId, updated);
      
      return new Response(JSON.stringify(updated), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'GET' && path === '/data/users') {
      const users = Array.from(storage.users.values());
      return new Response(JSON.stringify(users), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'GET' && path.startsWith('/data/products')) {
      const productId = path.split('/').pop();
      if (productId && productId !== 'products') {
        const product = storage.products.get(productId);
        if (!product) {
          return new Response(JSON.stringify({ error: 'Product not found' }), {
            status: 404,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        return new Response(JSON.stringify(product), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      const products = Array.from(storage.products.values());
      return new Response(JSON.stringify(products), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'GET' && path.startsWith('/data/orders')) {
      const orderId = path.split('/').pop();
      if (orderId && orderId !== 'orders') {
        const order = storage.orders.get(orderId);
        if (!order) {
          return new Response(JSON.stringify({ error: 'Order not found' }), {
            status: 404,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        return new Response(JSON.stringify(order), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      const userId = url.searchParams.get('userId');
      let orders = Array.from(storage.orders.values());
      
      if (userId) {
        orders = orders.filter(o => o.userId === userId);
      }
      
      return new Response(JSON.stringify(orders), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'POST' && path === '/data/orders') {
      const order = await request.json();
      const orderId = `o${Date.now()}`;
      const newOrder = { ...order, id: orderId, status: 'pending', created: new Date().toISOString() };
      storage.orders.set(orderId, newOrder);
      
      return new Response(JSON.stringify(newOrder), {
        status: 201,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response(JSON.stringify({ error: 'Invalid data endpoint' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};

function isAuthorizedInternalCall(request, env) {
  const expected = env.INTERNAL_SERVICE_TOKEN;
  if (!expected) return false;
  const token = request.headers.get('X-Internal-Token');
  return token === expected;
}