const commandValidators = {
  PING(args) {
    if (args.length > 1) {
      throw new Error('PING accepts zero or one argument.');
    }
    return ['PING', ...args];
  },
  TIME(args) {
    if (args.length !== 0) {
      throw new Error('TIME does not accept arguments.');
    }
    return ['TIME'];
  },
  DBSIZE(args) {
    if (args.length !== 0) {
      throw new Error('DBSIZE does not accept arguments.');
    }
    return ['DBSIZE'];
  },
  INFO(args) {
    if (args.length > 1) {
      throw new Error('INFO accepts zero or one argument.');
    }
    if (args.length === 1) {
      const section = args[0].toUpperCase();
      if (!allowedInfoSections.has(section)) {
        throw new Error('Invalid INFO section.');
      }
      return ['INFO', section];
    }
    return ['INFO'];
  },
  TYPE(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('TYPE requires one allowed key argument.');
    }
    return ['TYPE', args[0]];
  },
  TTL(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('TTL requires one allowed key argument.');
    }
    return ['TTL', args[0]];
  },
  PTTL(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('PTTL requires one allowed key argument.');
    }
    return ['PTTL', args[0]];
  },
  EXISTS(args) {
    if (args.length < 1 || args.length > 4 || !args.every(ensureSafeKeyName)) {
      throw new Error('EXISTS requires one to four allowed key arguments.');
    }
    return ['EXISTS', ...args];
  },
  GET(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('GET requires one allowed key argument.');
    }
    return ['GET', args[0]];
  },
  MGET(args) {
    if (args.length < 1 || args.length > 4 || !args.every(ensureSafeKeyName)) {
      throw new Error('MGET requires one to four allowed key arguments.');
    }
    return ['MGET', ...args];
  },
  STRLEN(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('STRLEN requires one allowed key argument.');
    }
    return ['STRLEN', args[0]];
  },
  HGET(args) {
    if (args.length !== 2 || !ensureSafeKeyName(args[0])) {
      throw new Error('HGET requires an allowed key and field name.');
    }
    return ['HGET', args[0], args[1]];
  },
  HGETALL(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('HGETALL requires one allowed key argument.');
    }
    return ['HGETALL', args[0]];
  },
  LLEN(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('LLEN requires one allowed key argument.');
    }
    return ['LLEN', args[0]];
  },
  SCARD(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('SCARD requires one allowed key argument.');
    }
    return ['SCARD', args[0]];
  },
  SMEMBERS(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('SMEMBERS requires one allowed key argument.');
    }
    return ['SMEMBERS', args[0]];
  },
  ZCARD(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('ZCARD requires one allowed key argument.');
    }
    return ['ZCARD', args[0]];
  },
  XLEN(args) {
    if (args.length !== 1 || !ensureSafeKeyName(args[0])) {
      throw new Error('XLEN requires one allowed key argument.');
    }
    return ['XLEN', args[0]];
  },
};