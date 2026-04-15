const reportRequestSchema = z.object({
  filename: z
    .string()
    .trim()
    .min(1)
    .max(100)
    .regex(/^[A-Za-z0-9._-]+$/, "filename contains invalid characters")
    .transform((value) => (value.toLowerCase().endsWith(".pdf") ? value : `${value}.pdf`)),
  url: z
    .string()
    .trim()
    .min(1)
    .max(2048)
    .url()
    .transform((value) => new URL(value))
    .superRefine((value, ctx) => {
      if (!["http:", "https:"].includes(value.protocol)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "only http and https URLs are allowed" });
      }
      if (value.username || value.password) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "URLs with embedded credentials are not allowed" });
      }
      if (value.hash) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "URL fragments are not allowed" });
      }
      if (!isHostnameAllowed(value.hostname)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "URL host is not allowed" });
      }
    }),
});