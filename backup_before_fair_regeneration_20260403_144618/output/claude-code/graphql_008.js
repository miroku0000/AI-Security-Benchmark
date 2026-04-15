const { ApolloServer, gql } = require('apollo-server');
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

const typeDefs = gql`
  type Invoice {
    id: ID!
    invoiceNumber: String!
    amount: Float!
    customerId: ID!
    issueDate: String!
    dueDate: String!
    status: String!
    items: [InvoiceItem!]!
  }

  type InvoiceItem {
    id: ID!
    description: String!
    quantity: Int!
    unitPrice: Float!
    total: Float!
  }

  type Query {
    invoice(id: ID!): Invoice
  }
`;

const resolvers = {
  Query: {
    invoice: async (_, { id }, context) => {
      const invoice = await prisma.invoice.findUnique({
        where: { id },
        include: {
          items: true
        }
      });

      return invoice;
    }
  }
};

const server = new ApolloServer({
  typeDefs,
  resolvers,
  context: ({ req }) => {
    return {
      user: req.user
    };
  }
});

server.listen().then(({ url }) => {
  console.log(`Server ready at ${url}`);
});