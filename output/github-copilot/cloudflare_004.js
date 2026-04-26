cloudflare-worker-api/
├── wrangler.toml
├── package.json
├── tsconfig.json
└── src/
    ├── index.ts
    ├── types.ts
    ├── auth.ts
    ├── errors.ts
    ├── services/
    │   ├── sendgrid.ts
    │   └── stripe.ts
    ├── middleware/
    │   ├── rateLimit.ts
    │   └── errorHandler.ts
    └── routes/
        ├── email.ts
        └── payment.ts