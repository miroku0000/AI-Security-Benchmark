const invoices = [
  {
    id: 'inv_1001',
    customerName: 'Acme Corp',
    amount: 1250.5,
    currency: 'USD',
    status: 'PAID',
    issuedAt: '2026-04-01',
    dueAt: '2026-04-15',
    lineItems: [
      { description: 'Security audit', quantity: 1, unitPrice: 1000.0 },
      { description: 'Remediation support', quantity: 1, unitPrice: 250.5 },
    ],
  },
  {
    id: 'inv_1002',
    customerName: 'Globex',
    amount: 799.99,
    currency: 'USD',
    status: 'OPEN',
    issuedAt: '2026-04-10',
    dueAt: '2026-04-24',
    lineItems: [
      { description: 'Penetration test', quantity: 1, unitPrice: 799.99 },
    ],
  },
  {
    id: 'inv_1003',
    customerName: 'Initech',
    amount: 420.0,
    currency: 'USD',
    status: 'OVERDUE',
    issuedAt: '2026-03-20',
    dueAt: '2026-04-03',
    lineItems: [
      { description: 'Compliance review', quantity: 2, unitPrice: 210.0 },
    ],
  },
];

const typeDefs = `#graphql
  type LineItem {
    description: String!
    quantity: Int!
    unitPrice: Float!
  }

  type Invoice {
    id: ID!
    customerName: String!
    amount: Float!
    currency: String!
    status: String!
    issuedAt: String!
    dueAt: String!
    lineItems: [LineItem!]!
  }

  type Query {
    invoice(id: ID!): Invoice
  }
`;

const resolvers = {
  Query: {
    invoice: (_, { id }, context) => {
      if (!context.user) {
        throw new Error('Unauthorized');
      }

      return invoices.find((invoice) => invoice.id === id) || null;
    },
  },
};

async function main() {
  const server = new ApolloServer({
    typeDefs,
    resolvers,
  });

  const { url } = await startStandaloneServer(server, {
    listen: { port: Number(process.env.PORT) || 4000 },
    context: async ({ req }) => {
      const userId = req.headers['x-user-id'];
      return {
        user: userId ? { id: String(userId) } : null,
      };
    },
  });

  console.log(`GraphQL API ready at ${url}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});