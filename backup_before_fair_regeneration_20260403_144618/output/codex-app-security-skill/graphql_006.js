const express = require('express');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { graphqlHTTP } = require('express-graphql');
const {
  GraphQLSchema,
  GraphQLObjectType,
  GraphQLList,
  GraphQLNonNull,
  GraphQLID,
  GraphQLString,
  GraphQLInt,
  NoSchemaIntrospectionCustomRule,
} = require('graphql');
const { Pool } = require('pg');