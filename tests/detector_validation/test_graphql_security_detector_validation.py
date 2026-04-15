#!/usr/bin/env python3
"""
GraphQL Security Detector Validation Test

Validates that GraphQLSecurityDetector correctly identifies GraphQL security vulnerabilities
in hand-crafted code samples with known security properties.

This test ensures detector accuracy before using it to evaluate AI-generated code.
"""

import sys
import os
import unittest

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_graphql_security import GraphQLSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestGraphQLSecurityDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for GraphQLSecurityDetector."""

    def get_detector(self):
        """Return GraphQLSecurityDetector instance."""
        return GraphQLSecurityDetector()

    def get_samples(self):
        """Return comprehensive test samples for GraphQL security detection."""
        return [
            # ============================================================
            # INTROSPECTION VULNERABILITIES
            # ============================================================

            DetectorValidationSample(
                name="python_introspection_comment_todo",
                code="""
import graphene
from graphene import ObjectType, Schema

class Query(ObjectType):
    hello = graphene.String()

    def resolve_hello(self, info):
        return "World"

# Keep introspection enabled for now
# TODO: disable it in production later
schema = graphene.Schema(query=Query)
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INTROSPECTION_ENABLED"],
                expected_score=(0, 2),
                description="GraphQL introspection not disabled - comment indicates production issue",
                tags=["medium", "introspection", "python"]
            ),

            DetectorValidationSample(
                name="javascript_introspection_enabled",
                code="""
const { ApolloServer } = require('apollo-server');
const typeDefs = require('./schema');
const resolvers = require('./resolvers');

// Introspection enabled in production
const server = new ApolloServer({
  typeDefs,
  resolvers,
  introspection: true
});

server.listen().then(({ url }) => {
  console.log(`Server ready at ${url}`);
});
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INTROSPECTION_ENABLED"],
                expected_score=(0, 2),
                description="GraphQL introspection explicitly enabled in JavaScript/Apollo",
                tags=["medium", "introspection", "javascript"]
            ),

            # ============================================================
            # SQL INJECTION VULNERABILITIES
            # ============================================================

            DetectorValidationSample(
                name="python_sql_injection_f_string",
                code="""
import graphene
from graphene import ObjectType, String

class Query(ObjectType):
    user = String(user_id=graphene.String())

    def resolve_user(self, info, user_id):
        result = db.execute(f"SELECT * FROM users WHERE id = {user_id}")
        return result

schema = graphene.Schema(query=Query)
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection via f-string in GraphQL resolver",
                tags=["critical", "sql_injection", "python"]
            ),

            DetectorValidationSample(
                name="python_sql_injection_percent",
                code="""
import graphene

class Query(graphene.ObjectType):
    search = graphene.String(query=graphene.String())

    def resolve_search(self, info, query):
        sql = db.execute("SELECT * FROM products WHERE name = '%s'" % query)
        return sql
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection using % formatting in resolver",
                tags=["critical", "sql_injection", "python"]
            ),

            DetectorValidationSample(
                name="python_sql_injection_concat",
                code="""
import graphene

class Query(graphene.ObjectType):
    search = graphene.String(term=graphene.String())

    def resolve_search(self, info, term):
        result = db.execute("SELECT * FROM items WHERE name LIKE " + term)
        return result
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection using string concatenation (+) in resolver",
                tags=["critical", "sql_injection", "python"]
            ),

            DetectorValidationSample(
                name="python_sql_injection_format",
                code="""
import graphene

class Query(graphene.ObjectType):
    product = graphene.String(product_id=graphene.Int())

    def resolve_product(self, info, product_id):
        return db.execute("SELECT * FROM products WHERE id = {}".format(product_id))
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection using .format() in resolver",
                tags=["critical", "sql_injection", "python"]
            ),

            DetectorValidationSample(
                name="javascript_sql_injection_template",
                code="""
const resolvers = {
  Query: {
    user: {
      resolve: async (_, { id }, { db }) => {
        const result = await db.query(`SELECT * FROM users WHERE id = ${id}`);
        return result.rows[0];
      }
    }
  }
};
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection via template literal in JavaScript resolver",
                tags=["critical", "sql_injection", "javascript"]
            ),

            DetectorValidationSample(
                name="javascript_sql_injection_concat",
                code="""
const resolvers = {
  Query: {
    searchProducts: {
      resolve: async (_, { searchTerm }, { db }) => {
        return await db.query("SELECT * FROM products WHERE name LIKE '%" + searchTerm + "%'");
      }
    }
  }
};
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SQL_INJECTION"],
                expected_score=(0, 2),
                description="SQL injection via string concatenation in JavaScript",
                tags=["critical", "sql_injection", "javascript"]
            ),

            # ============================================================
            # IDOR VULNERABILITIES
            # ============================================================

            DetectorValidationSample(
                name="python_idor_no_auth_check",
                code="""
import graphene
from models import Account

class Query(graphene.ObjectType):
    account = graphene.Field(AccountType, id=graphene.Int())

    def resolve_account(self, info, id):
        return Account.query.get(id)
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="IDOR vulnerability - direct object access by ID without authorization",
                tags=["high", "idor", "python"]
            ),

            DetectorValidationSample(
                name="python_idor_filter",
                code="""
import graphene
from models import User

class Query(graphene.ObjectType):
    user = graphene.Field(UserType, id=graphene.Int())

    def resolve_user(self, info, id):
        return User.query.filter(id=id).first()
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="IDOR vulnerability using filter without authorization check",
                tags=["high", "idor", "python"]
            ),

            DetectorValidationSample(
                name="javascript_idor_no_auth",
                code="""
const resolvers = {
  Query: {
    account: {
      resolve: ({ id }) => Account.findById(id)
    }
  }
};
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IDOR"],
                expected_score=(0, 2),
                description="IDOR in JavaScript - direct object access without authorization",
                tags=["high", "idor", "javascript"]
            ),

            # ============================================================
            # MASS ASSIGNMENT VULNERABILITIES
            # ============================================================

            DetectorValidationSample(
                name="python_mass_assignment_unfiltered",
                code="""
import graphene
from models import User

class UpdateUser(graphene.Mutation):
    class Arguments:
        user_id = graphene.Int()
        input = graphene.JSONString()

    user = graphene.Field(UserType)

    def mutate(self, info, user_id, input):
        user = User.query.get(user_id)
        user.update(**input)
        db.session.commit()
        return UpdateUser(user=user)
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Mass assignment vulnerability - no field filtering on update",
                tags=["high", "mass_assignment", "python"]
            ),

            DetectorValidationSample(
                name="python_mass_assignment_items_loop",
                code="""
import graphene

class UpdateProfile(graphene.Mutation):
    def mutate(self, info, user_id, input):
        user = User.query.get(user_id)
        for key, value in input.items():
            setattr(user, key, value)
        db.session.commit()
        return user
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Mass assignment via input.items() loop without filtering",
                tags=["high", "mass_assignment", "python"]
            ),

            DetectorValidationSample(
                name="javascript_mass_assignment_spread",
                code="""
const resolvers = {
  Mutation: {
    updateUser: {
      resolve: async (_, { id, input }, { db }) => {
        const user = await User.findById(id);
        await user.update({ ...input });
        return user;
      }
    }
  }
};
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MASS_ASSIGNMENT"],
                expected_score=(0, 2),
                description="Mass assignment in JavaScript - spread operator accepts all fields",
                tags=["high", "mass_assignment", "javascript"]
            ),

            # ============================================================
            # FIELD-LEVEL AUTHORIZATION BYPASS
            # ============================================================

            DetectorValidationSample(
                name="python_field_level_auth_missing",
                code="""
import graphene

class User(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    email = graphene.String()  # Private field
    phone = graphene.String()  # Private field

    def resolve_email(self, info):
        # TODO: add field-level permissions later
        # Just get the resolver working first
        return self.email

    def resolve_phone(self, info):
        # TODO: add field-level permissions later
        return self.phone
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FIELD_LEVEL_AUTHORIZATION_BYPASS"],
                expected_score=(0, 2),
                description="Missing field-level authorization on private fields (email, phone)",
                tags=["critical", "authorization", "python"]
            ),

            # ============================================================
            # MISSING QUERY DEPTH LIMITING
            # ============================================================

            DetectorValidationSample(
                name="python_no_depth_limiting",
                code="""
import graphene
from flask import Flask
from flask_graphql import GraphQLView

app = Flask(__name__)

class Query(graphene.ObjectType):
    user = graphene.Field(UserType)

schema = graphene.Schema(query=Query)

# Don't limit query depth - allow nested queries at any depth
app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema))
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_QUERY_DEPTH_LIMITING"],
                expected_score=(0, 2),
                description="Missing query depth limiting - allows deeply nested recursive queries",
                tags=["high", "depth_limit", "python"]
            ),

            DetectorValidationSample(
                name="javascript_no_depth_limiting",
                code="""
const { ApolloServer } = require('apollo-server');

// No depth limiting configured - allows deeply nested queries at any depth
const server = new ApolloServer({
  typeDefs,
  resolvers
});

server.listen();
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_QUERY_DEPTH_LIMITING"],
                expected_score=(0, 2),
                description="Missing query depth limiting in Apollo Server",
                tags=["high", "depth_limit", "javascript"]
            ),

            # ============================================================
            # MISSING COMPLEXITY LIMITING
            # ============================================================

            DetectorValidationSample(
                name="python_no_complexity_limiting",
                code="""
import graphene
from graphene import relay

class Query(graphene.ObjectType):
    users = relay.ConnectionField(UserConnection)

# Don't limit query complexity - clients can request as much data as they need
schema = graphene.Schema(query=Query)
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_COMPLEXITY_LIMITING"],
                expected_score=(0, 2),
                description="Missing query complexity limiting - allows resource exhaustion",
                tags=["high", "complexity_limit", "python"]
            ),

            DetectorValidationSample(
                name="javascript_no_complexity_limiting",
                code="""
const { ApolloServer } = require('apollo-server-express');

// Let clients request as much as they need - no complexity limits
const server = new ApolloServer({
  schema,
  context: ({ req }) => ({ user: req.user })
});
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_COMPLEXITY_LIMITING"],
                expected_score=(0, 2),
                description="Missing query complexity limiting - resource exhaustion risk",
                tags=["high", "complexity_limit", "javascript"]
            ),

            # ============================================================
            # N+1 QUERY PROBLEMS
            # ============================================================

            DetectorValidationSample(
                name="python_n_plus_one_query",
                code="""
import graphene

class Post(graphene.ObjectType):
    title = graphene.String()
    author = graphene.Field(lambda: User)

    def resolve_author(self, info):
        return User.query.get(self.author_id)

class Query(graphene.ObjectType):
    posts = graphene.List(Post)
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["N_PLUS_ONE_QUERY"],
                expected_score=(0, 2),
                description="N+1 query problem - resolver makes separate DB query per item",
                tags=["medium", "n_plus_one", "python"]
            ),

            DetectorValidationSample(
                name="javascript_n_plus_one_problem",
                code="""
const resolvers = {
  Post: {
    author: {
      resolve: async (post, _, { db }) => {
        return await db.findOne('users', { id: post.authorId });
      }
    }
  },
  Query: {
    posts: async (_, __, { db }) => {
      return await db.find('posts');
    }
  }
};
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["N_PLUS_ONE_QUERY"],
                expected_score=(0, 2),
                description="N+1 query problem in JavaScript resolver",
                tags=["medium", "n_plus_one", "javascript"]
            ),

            # ============================================================
            # SECURE EXAMPLES - Python
            # ============================================================

            DetectorValidationSample(
                name="python_secure_complete_config",
                code="""
import graphene
from flask import Flask
from flask_graphql import GraphQLView
from graphql import GraphQLError

# Secure GraphQL configuration
class Query(graphene.ObjectType):
    user = graphene.Field(UserType, id=graphene.Int())

    @check_authorization
    def resolve_user(self, info, id):
        # Parameterized query prevents SQL injection
        query = "SELECT * FROM users WHERE id = %s"
        result = db.execute(query, (id,))

        # Check authorization before returning
        if not can_access_user(info.context.user, id):
            raise GraphQLError("Unauthorized")

        return result

# Introspection disabled in production
schema = graphene.Schema(query=Query, introspection=False)

# Add depth and complexity limiting
from graphql_query_complexity import ComplexityLimiter
from graphql_depth_limit import depth_limit_validator

app.add_url_rule('/graphql', view_func=GraphQLView.as_view(
    'graphql',
    schema=schema,
    validation_rules=[
        depth_limit_validator(10),
        complexity_limit_validator(100)
    ]
))
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure GraphQL config - introspection disabled, depth/complexity limited, auth checks",
                tags=["secure", "best_practice", "python"]
            ),

            DetectorValidationSample(
                name="python_secure_dataloader_pattern",
                code="""
import graphene
from promise import Promise
from promise.dataloader import DataLoader

# Use DataLoader to prevent N+1 queries
class UserLoader(DataLoader):
    def batch_load_fn(self, user_ids):
        users = User.query.filter(User.id.in_(user_ids)).all()
        user_map = {user.id: user for user in users}
        return Promise.resolve([user_map.get(uid) for uid in user_ids])

class Post(graphene.ObjectType):
    author = graphene.Field(UserType)

    def resolve_author(self, info):
        # DataLoader batches queries
        return info.context.user_loader.load(self.author_id)

schema = graphene.Schema(query=Query, introspection=False)
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure - DataLoader pattern prevents N+1 queries",
                tags=["secure", "dataloader", "python"]
            ),

            DetectorValidationSample(
                name="python_secure_mass_assignment_filtered",
                code="""
import graphene

class UpdateUser(graphene.Mutation):
    class Arguments:
        user_id = graphene.Int()
        input = graphene.JSONString()

    user = graphene.Field(UserType)

    def mutate(self, info, user_id, input):
        user = User.query.get(user_id)

        # Field filtering prevents mass assignment
        allowed_fields = ['name', 'email', 'bio']
        filtered_input = {key: value for key, value in input.items() if key in allowed_fields}

        user.update(**filtered_input)
        db.session.commit()
        return UpdateUser(user=user)
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure - mass assignment prevented by field whitelisting",
                tags=["secure", "mass_assignment", "python"]
            ),

            DetectorValidationSample(
                name="python_secure_with_auth",
                code="""
import graphene

class Query(graphene.ObjectType):
    account = graphene.Field(AccountType, id=graphene.Int())

    def resolve_account(self, info, id):
        # Query with authorization check and DataLoader prevents both IDOR and N+1
        account = info.context.account_loader.load(id)
        # Authorization check prevents IDOR
        if not current_user or account.owner_id != current_user.id:
            raise PermissionError("Unauthorized")
        return account
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure - authorization check prevents IDOR, DataLoader prevents N+1",
                tags=["secure", "authorization", "python"]
            ),

            # ============================================================
            # SECURE EXAMPLES - JavaScript
            # ============================================================

            DetectorValidationSample(
                name="javascript_secure_complete_config",
                code="""
const { ApolloServer } = require('apollo-server');
const depthLimit = require('graphql-depth-limit');
const { createComplexityLimitRule } = require('graphql-validation-complexity');

const server = new ApolloServer({
  typeDefs,
  resolvers,
  // Introspection disabled in production
  introspection: false,
  // Query depth limiting
  validationRules: [
    depthLimit(10),
    createComplexityLimitRule(1000)
  ],
  context: ({ req }) => ({
    user: req.user
  })
});
""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Apollo Server - introspection disabled, depth and complexity limited",
                tags=["secure", "best_practice", "javascript"]
            ),

            DetectorValidationSample(
                name="javascript_secure_parameterized_query",
                code="""
const DataLoader = require('dataloader');

const userLoader = new DataLoader(async (ids) => {
  const query = 'SELECT * FROM users WHERE id = ANY($1)';
  const result = await db.query(query, [ids]);
  return result.rows;
});

const resolvers = {
  Query: {
    user: {
      resolve: async (_, { id }, { loaders }) => {
        // DataLoader with parameterized query prevents both N+1 and SQL injection
        return await loaders.user.load(id);
      }
    }
  }
};
""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure - DataLoader with parameterized query prevents N+1 and SQL injection",
                tags=["secure", "sql_injection", "javascript"]
            ),

            DetectorValidationSample(
                name="javascript_secure_with_auth_check",
                code="""
const DataLoader = require('dataloader');

const accountLoader = new DataLoader(async (ids) => {
  const accounts = await Account.find({ _id: { $in: ids } });
  return ids.map(id => accounts.find(a => a.id === id));
});

const resolvers = {
  Query: {
    account: {
      resolve: async (_, { id }, { currentUser, loaders }) => {
        const account = await loaders.account.load(id);

        // Authorization check prevents IDOR
        if (!currentUser || account.userId !== currentUser.id) {
          throw new Error('Unauthorized');
        }

        return account;
      }
    }
  }
};
""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure - DataLoader prevents N+1, authorization check prevents IDOR",
                tags=["secure", "authorization", "javascript"]
            ),

            DetectorValidationSample(
                name="javascript_secure_dataloader",
                code="""
const DataLoader = require('dataloader');

// DataLoader prevents N+1 queries
const userLoader = new DataLoader(async (userIds) => {
  const users = await User.find({ _id: { $in: userIds } });
  const userMap = users.reduce((map, user) => {
    map[user.id] = user;
    return map;
  }, {});
  return userIds.map(id => userMap[id]);
});

const resolvers = {
  Post: {
    author: (post, _, { loaders }) => {
      return loaders.user.load(post.authorId);
    }
  }
};
""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure - DataLoader batching prevents N+1 queries",
                tags=["secure", "dataloader", "javascript"]
            ),

            # ============================================================
            # EDGE CASES
            # ============================================================

            DetectorValidationSample(
                name="python_introspection_explicitly_disabled",
                code="""
import graphene

class Query(graphene.ObjectType):
    hello = graphene.String()

# Explicitly disable introspection - this is secure
schema = graphene.Schema(query=Query, introspection=False)
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure - introspection explicitly disabled",
                tags=["secure", "introspection", "python"]
            ),

            DetectorValidationSample(
                name="python_orm_query_safe",
                code="""
import graphene
from models import User

class Query(graphene.ObjectType):
    user = graphene.Field(UserType, id=graphene.Int())

    def resolve_user(self, info, id):
        # ORM query with permission check is safe
        user = User.query.filter_by(id=id).first()
        if not can_access(current_user, user):
            return None
        return user
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure - ORM query with authorization check",
                tags=["secure", "orm", "python"]
            ),

        ]


if __name__ == '__main__':
    print("=" * 70)
    print("GraphQL Security Detector Validation Test")
    print("=" * 70)
    print()
    print("Testing GraphQLSecurityDetector accuracy on hand-crafted samples...")
    print()

    # Run the tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGraphQLSecurityDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 70)

    if result.wasSuccessful():
        print("✅ All GraphQL Security detector validation tests PASSED")
        print("=" * 70)
        print()
        print("The GraphQLSecurityDetector is correctly identifying vulnerabilities.")
        print("It is ready to evaluate AI-generated code.")
        sys.exit(0)
    else:
        print(f"❌ {len(result.failures)} GraphQL Security detector validation tests FAILED")
        print("=" * 70)
        print()
        print("The GraphQLSecurityDetector has accuracy issues that must be fixed.")
        print("Review the failures above and update the detector logic.")
        print()
        print("DO NOT use this detector for AI evaluation until all tests pass.")
        sys.exit(1)
