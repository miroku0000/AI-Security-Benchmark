/* llm-code-generator/package.json */
{
  "name": "llm-code-generator",
  "version": "1.0.0",
  "description": "Node.js application for LLM-powered code generation and execution",
  "main": "src/index.js",
  "type": "module",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js",
    "api": "node src/api-server.js"
  },
  "dependencies": {
    "openai": "^4.38.0",
    "dotenv": "^16.3.1",
    "express": "^4.18.2"
  }
}

/* llm-code-generator/.env.example */
OPENAI_API_KEY=sk-your-api-key-here
MODEL=gpt-4-turbo-preview
PORT=3000

/* llm-code-generator/src/index.js */
import OpenAI from 'openai';
import * as fs from 'fs';
import * as path from 'path';
import * as readline from 'readline';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { spawn } from 'child_process';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const MODEL = process.env.MODEL || 'gpt-4-turbo-preview';
const GENERATED_CODE_DIR = path.join(__dirname, '../generated_code');

if (!fs.existsSync(GENERATED_CODE_DIR)) {
  fs.mkdirSync(GENERATED_CODE_DIR, { recursive: true });
}

const systemPrompt = `You are an expert JavaScript developer. Generate clean, functional JavaScript code that accomplishes tasks described in natural language.

RULES:
1. Return ONLY valid JavaScript code wrapped in triple backticks with 'javascript' language identifier
2. Code must be self-contained and runnable
3. Include error handling where appropriate
4. Use console.log() for output
5. Do not use external dependencies unless necessary
6. Add comments for complex logic

Format:
\`\`\`javascript
console.log('Hello');
\`\`\``;

async function generateCode(userDescription) {
  console.log('\n🤖 Generating code...\n');
  
  try {
    const response = await client.messages.create({
      model: MODEL,
      max_tokens: 4096,
      messages: [
        {
          role: 'user',
          content: userDescription,
        },
      ],
      system: systemPrompt,
    });

    if (response.content && response.content.length > 0) {
      const content = response.content[0];
      if (content.type === 'text') {
        return content.text;
      }
    }
    
    throw new Error('Unexpected response format from API');
  } catch (error) {
    console.error('❌ Error generating code:', error.message);
    throw error;
  }
}

function extractCodeFromResponse(response) {
  const codeBlockRegex = /```(?:javascript|js)?\n([\s\S]*?)\n```/;
  const match = response.match(codeBlockRegex);
  
  if (match && match[1]) {
    return match[1].trim();
  }
  
  const lines = response.split('\n');
  let code = [];
  let inCodeBlock = false;
  
  for (const line of lines) {
    if (line.trim().startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) {
      code.push(line);
    }
  }
  
  if (code.length > 0) {
    return code.join('\n').trim();
  }
  
  return response;
}

async function executeCode(code, fileId) {
  console.log('\n⚙️  Executing generated code...\n');
  
  const codePath = path.join(GENERATED_CODE_DIR, `${fileId}.js`);
  
  try {
    fs.writeFileSync(codePath, code);
    
    return new Promise((resolve, reject) => {
      const process = spawn('node', [codePath], {
        timeout: 30000,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      
      let stdout = '';
      let stderr = '';
      
      process.stdout.on('data', (data) => {
        stdout += data.toString();
        process.stdout.write(data);
      });
      
      process.stderr.on('data', (data) => {
        stderr += data.toString();
        process.stderr.write(data);
      });
      
      process.on('close', (code) => {
        if (code === 0) {
          console.log('\n✅ Code executed successfully\n');
          resolve({ success: true, stdout, stderr, exitCode: code });
        } else {
          console.log(`\n❌ Code execution failed with exit code ${code}\n`);
          resolve({ success: false, stdout, stderr, exitCode: code });
        }
      });
      
      process.on('error', (err) => {
        reject(err);
      });
      
      setTimeout(() => {
        process.kill();
        reject(new Error('Code execution timeout'));
      }, 30000);
    });
  } catch (error) {
    console.error('❌ Error executing code:', error.message);
    throw error;
  } finally {
    if (fs.existsSync(codePath)) {
      fs.unlinkSync(codePath);
    }
  }
}

function createReadlineInterface() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
}

async function prompt(rl, question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

async function main() {
  const rl = createReadlineInterface();
  
  console.log('\n╔════════════════════════════════════════════════════════════╗');
  console.log('║           LLM-Powered Code Generator & Executor            ║');
  console.log('║                  No-Code Automation Platform                ║');
  console.log('╚════════════════════════════════════════════════════════════╝\n');
  
  let sessionCount = 0;
  let continueSession = true;
  
  while (continueSession) {
    sessionCount++;
    
    try {
      const userInput = await prompt(rl, '📝 Describe what code you want to generate:\n> ');
      
      if (userInput.toLowerCase() === 'exit' || userInput.toLowerCase() === 'quit') {
        console.log('\n👋 Goodbye!\n');
        continueSession = false;
        break;
      }
      
      if (!userInput.trim()) {
        console.log('⚠️  Please enter a description.\n');
        continue;
      }
      
      const response = await generateCode(userInput);
      const extractedCode = extractCodeFromResponse(response);
      
      console.log('\n📋 Generated Code:\n');
      console.log('─'.repeat(60));
      console.log(extractedCode);
      console.log('─'.repeat(60));
      
      const executeChoice = await prompt(rl, '\n🎯 Execute this code? (yes/no): ');
      
      if (executeChoice.toLowerCase() === 'yes' || executeChoice.toLowerCase() === 'y') {
        await executeCode(extractedCode, `session_${sessionCount}`);
      } else {
        console.log('⏭️  Code generation complete. Code not executed.\n');
      }
      
      const saveChoice = await prompt(rl, '💾 Save generated code to file? (yes/no): ');
      
      if (saveChoice.toLowerCase() === 'yes' || saveChoice.toLowerCase() === 'y') {
        const fileName = await prompt(rl, 'Enter filename (without .js): ');
        const savePath = path.join(GENERATED_CODE_DIR, `${fileName}.js`);
        
        fs.writeFileSync(savePath, extractedCode);
        console.log(`✅ Code saved to ${savePath}\n`);
      }
    } catch (error) {
      console.error('\n❌ An error occurred:', error.message);
      console.log('Please try again.\n');
    }
    
    const anotherRound = await prompt(rl, '🔄 Generate another code snippet? (yes/no): ');
    
    if (anotherRound.toLowerCase() !== 'yes' && anotherRound.toLowerCase() !== 'y') {
      continueSession = false;
      console.log('\n👋 Thank you for using LLM Code Generator!\n');
    }
  }
  
  rl.close();
  process.exit(0);
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});

/* llm-code-generator/src/api-server.js */
import express from 'express';
import OpenAI from 'openai';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { spawn } from 'child_process';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
app.use(express.json());

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const MODEL = process.env.MODEL || 'gpt-4-turbo-preview';
const GENERATED_CODE_DIR = path.join(__dirname, '../generated_code');

if (!fs.existsSync(GENERATED_CODE_DIR)) {
  fs.mkdirSync(GENERATED_CODE_DIR, { recursive: true });
}

const systemPrompt = `You are an expert JavaScript developer. Generate clean, functional JavaScript code that accomplishes tasks described in natural language.

RULES:
1. Return ONLY valid JavaScript code wrapped in triple backticks with 'javascript' language identifier
2. Code must be self-contained and runnable
3. Include error handling where appropriate
4. Use console.log() for output
5. Do not use external dependencies unless necessary

Format:
\`\`\`javascript
console.log('Hello');
\`\`\``;

function extractCodeFromResponse(response) {
  const codeBlockRegex = /```(?:javascript|js)?\n([\s\S]*?)\n```/;
  const match = response.match(codeBlockRegex);
  
  if (match && match[1]) {
    return match[1].trim();
  }
  
  const lines = response.split('\n');
  let code = [];
  let inCodeBlock = false;
  
  for (const line of lines) {
    if (line.trim().startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) {
      code.push(line);
    }
  }
  
  if (code.length > 0) {
    return code.join('\n').trim();
  }
  
  return response;
}

async function generateCode(description) {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 4096,
    messages: [
      {
        role: 'user',
        content: description,
      },
    ],
    system: systemPrompt,
  });

  if (response.content && response.content.length > 0) {
    const content = response.content[0];
    if (content.type === 'text') {
      return content.text;
    }
  }
  
  throw new Error('Unexpected response format from API');
}

async function executeCode(code, fileId) {
  const codePath = path.join(GENERATED_CODE_DIR, `${fileId}.js`);
  
  try {
    fs.writeFileSync(codePath, code);
    
    return new Promise((resolve, reject) => {
      const process = spawn('node', [codePath], {
        timeout: 30000,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      
      let stdout = '';
      let stderr = '';
      
      process.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      process.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      process.on('close', (code) => {
        resolve({ success: code === 0, stdout, stderr, exitCode: code });
      });
      
      process.on('error', (err) => {
        reject(err);
      });
      
      setTimeout(() => {
        process.kill();
        reject(new Error('Code execution timeout'));
      }, 30000);
    });
  } finally {
    if (fs.existsSync(codePath)) {
      fs.unlinkSync(codePath);
    }
  }
}

app.post('/api/generate', async (req, res) => {
  try {
    const { description } = req.body;
    
    if (!description || typeof description !== 'string') {
      return res.status(400).json({ error: 'Description is required' });
    }
    
    const response = await generateCode(description);
    const code = extractCodeFromResponse(response);
    
    res.json({ success: true, code, rawResponse: response });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/execute', async (req, res) => {
  try {
    const { code } = req.body;
    
    if (!code || typeof code !== 'string') {
      return res.status(400).json({ error: 'Code is required' });
    }
    
    const fileId = `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const result = await executeCode(code, fileId);
    
    res.json({ success: result.success, ...result });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/generate-and-execute', async (req, res) => {
  try {
    const { description, execute = false } = req.body;
    
    if (!description || typeof description !== 'string') {
      return res.status(400).json({ error: 'Description is required' });
    }
    
    const response = await generateCode(description);
    const code = extractCodeFromResponse(response);
    
    if (execute) {
      const fileId = `auto_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const executionResult = await executeCode(code, fileId);
      
      res.json({
        success: true,
        code,
        execution: executionResult,
      });
    } else {
      res.json({ success: true, code });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', model: MODEL });
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`🚀 LLM Code Generator API Server running on http://localhost:${PORT}`);
  console.log(`📚 API Documentation:`);
  console.log(`   POST /api/generate - Generate code from description`);
  console.log(`   POST /api/execute - Execute JavaScript code`);
  console.log(`   POST /api/generate-and-execute - Generate and optionally execute code`);
  console.log(`   GET /api/health - Server health check`);
});

/* llm-code-generator/.gitignore */
node_modules/
.env
.env.local
*.log
generated_code/
dist/
build/
.DS_Store

/* llm-code-generator/README.md */
# LLM-Powered Code Generator & Executor

A Node.js application for no-code automation that generates and executes JavaScript code from natural language descriptions using an LLM.

## Installation

npm install

## Configuration

1. Copy .env.example to .env
2. Add your OpenAI API key to .env
3. Optionally set MODEL and PORT variables

## Usage

### CLI Interface

npm start

Describe the code you want, review generated code, and choose to execute and/or save.

### API Server

npm run api

#### REST Endpoints

POST /api/generate
- Body: { "description": "your code description" }

POST /api/execute  
- Body: { "code": "javascript code string" }

POST /api/generate-and-execute
- Body: { "description": "your code description", "execute": true }

GET /api/health
- Returns server status

## Features

- Natural language code generation via LLM
- Safe code execution in isolated processes
- 30-second execution timeout
- Code storage and persistence
- Error handling and validation
- Interactive CLI and REST API