const express = require('express');
const http = require('http');
const crypto = require('crypto');
const { ApolloServer } = require('@apollo/server');
const { expressMiddleware } = require('@apollo/server/express4');
const { ApolloServerPluginDrainHttpServer } = require('@apollo/server/plugin/drainHttpServer');
const { GraphQLError } = require('graphql');