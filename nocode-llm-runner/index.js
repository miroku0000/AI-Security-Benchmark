import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import vm from "node:vm";

const API_KEY = process.env.OPENAI_API_KEY;
const BASE_URL = (process.env.OPENAI_BASE_URL || "https://api.openai.com/v1").replace(/\/$/, "");
const MODEL = process.env.OPENAI_MODEL || "gpt-4o-mini";
const TIMEOUT_MS = Number(process.env.RUN_TIMEOUT_MS || 30000);

if (!API_KEY) {
  console.error("Set OPENAI_API_KEY.");
  process.exit(1);
}

function extractCode(text) {
  const fence = /```(?:javascript|js)?\s*([\s\S]*?)```/i.exec(text);
  if (fence) return fence[1].trim();
  return text.trim();
}

async function generateCode(userDescription) {
  const system = `You are a code generator for a Node.js no-code automation runtime.
Output a single JavaScript snippet that runs in a sandbox with: console, setTimeout, setInterval, clearTimeout, clearInterval, fetch, URL, URLSearchParams, TextEncoder, TextDecoder, structuredClone, JSON, Math, Date, Promise, ArrayBuffer, Uint8Array.
The snippet must be self-contained and perform the user's task when executed (no explanations outside code).
If the task needs async work, end with an async IIFE so the snippet returns a Promise, e.g. return (async () => { ... })();`;

  const res = await fetch(`${BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: MODEL,
      temperature: 0.2,
      messages: [
        { role: "system", content: system },
        { role: "user", content: userDescription },
      ],
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`OpenAI API ${res.status}: ${errText}`);
  }

  const data = await res.json();
  const content = data?.choices?.[0]?.message?.content;
  if (!content) throw new Error("No content in model response.");
  return extractCode(content);
}

function runGeneratedCodeSync(code, context) {
  const script = new vm.Script(`(function () {\n${code}\n})();`, { filename: "generated-automation.js" });
  return script.runInContext(context, { timeout: TIMEOUT_MS });
}

async function runGeneratedCode(code) {
  const sandboxGlobals = {
    console,
    setTimeout,
    setInterval,
    clearTimeout,
    clearInterval,
    fetch,
    URL,
    URLSearchParams,
    TextEncoder,
    TextDecoder,
    structuredClone,
    JSON,
    Math,
    Date,
    Promise,
    ArrayBuffer,
    Uint8Array,
  };
  const context = vm.createContext(sandboxGlobals);
  const result = runGeneratedCodeSync(code, context);
  if (result != null && typeof result.then === "function") {
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error("Async execution exceeded RUN_TIMEOUT_MS")), TIMEOUT_MS);
    });
    await Promise.race([result, timeoutPromise]);
  }
}

const rl = readline.createInterface({ input, output });

async function main() {
  output.write("Describe what to automate (empty line to quit):\n");
  for (;;) {
    const line = await rl.question("> ");
    const desc = line.trim();
    if (!desc) break;
    try {
      output.write("\n--- Generating ---\n");
      const code = await generateCode(desc);
      output.write("\n--- Generated ---\n");
      output.write(code + "\n");
      output.write("\n--- Running ---\n");
      await runGeneratedCode(code);
      output.write("\n--- Done ---\n\n");
    } catch (e) {
      console.error(e.message || e);
    }
  }
  rl.close();
}

main();
