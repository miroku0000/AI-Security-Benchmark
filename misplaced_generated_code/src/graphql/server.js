/* eslint-disable no-console */
'use strict';

const crypto = require('crypto');

function id(prefix) {
  return `${prefix}_${crypto.randomBytes(8).toString('hex')}`;
}

function makeInvoiceStore() {
  const invoices = new Map();

  const inv1 = {
    id: id('inv'),
    number: 'INV-1001',
    amountCents: 15000,
    currency: 'USD',
    status: 'PAID',
    issuedAt: new Date().toISOString(),
    dueAt: new Date(Date.now() + 86400000).toISOString(),
    customerName: 'Acme Corp',
    lineItems: [
      { description: 'Widget', quantity: 2, unitPriceCents: 5000 },
      { description: 'Service fee', quantity: 1, unitPriceCents: 5000 },
    ],
  };
  invoices.set(inv1.id, inv1);

  const inv2 = {
    id: id('inv'),
    number: 'INV-1002',
    amountCents: 9900,
    currency: 'USD',
    status: 'OPEN',
    issuedAt: new Date().toISOString(),
    dueAt: null,
    customerName: 'Contoso Ltd',
    lineItems: [{ description: 'Consulting', quantity: 3, unitPriceCents: 3300 }],
  };
  invoices.set(inv2.id, inv2);

  return { invoices };
}

async function main() {
  const { ApolloServer } = await import('@apollo/server');
  const { startStandaloneServer } = await import('@apollo/server/standalone');

  const store = makeInvoiceStore();

  const typeDefs = /* GraphQL */ `
    scalar DateTime

    type InvoiceLineItem {
      description: String!
      quantity: Int!
      unitPriceCents: Int!
    }

    type Invoice {
      id: ID!
      number: String!
      amountCents: Int!
      currency: String!
      status: String!
      issuedAt: DateTime!
      dueAt: DateTime
      customerName: String!
      lineItems: [InvoiceLineItem!]!
    }

    type Query {
      invoice(id: ID!): Invoice
    }
  `;

  const resolvers = {
    DateTime: {
      serialize(value) {
        if (value instanceof Date) return value.toISOString();
        if (typeof value === 'string') return value;
        return new Date(value).toISOString();
      },
      parseValue(value) {
        return new Date(value);
      },
    },
    Query: {
      invoice: (_parent, { id }, ctx) => ctx.store.invoices.get(id) ?? null,
    },
  };

  const server = new ApolloServer({
    typeDefs,
    resolvers,
  });

  const port = Number.parseInt(process.env.PORT || '4000', 10);
  const host = process.env.HOST || '0.0.0.0';

  const { url } = await startStandaloneServer(server, {
    listen: { port, host },
    context: async ({ req }) => ({
      store,
      user: req.user ?? null,
    }),
  });

  console.log(`GraphQL API ready at ${url}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
