import 'dotenv/config';
import express from 'express';
import { ethers } from 'ethers';

const RPC_URL = process.env.RPC_URL;
const PRIVATE_KEY_RAW = process.env.PRIVATE_KEY;

function normalizePrivateKey(key) {
  if (!key) return null;
  const trimmed = String(key).trim();
  return trimmed.startsWith('0x') ? trimmed : `0x${trimmed}`;
}

export function createSignerFromEnv() {
  if (!RPC_URL) throw new Error('RPC_URL is required');
  const pk = normalizePrivateKey(PRIVATE_KEY_RAW);
  if (!pk) throw new Error('PRIVATE_KEY is required');
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const wallet = new ethers.Wallet(pk, provider);
  return { provider, wallet };
}

export async function getBalanceEth(address, provider) {
  const p = provider ?? createSignerFromEnv().provider;
  const bal = await p.getBalance(ethers.getAddress(address));
  return ethers.formatEther(bal);
}

export async function sendEth(wallet, toAddress, amountEth, txOverrides = {}) {
  const w = wallet ?? createSignerFromEnv().wallet;
  const tx = await w.sendTransaction({
    to: ethers.getAddress(toAddress),
    value: ethers.parseEther(String(amountEth)),
    ...txOverrides,
  });
  const receipt = await tx.wait();
  return { transactionHash: tx.hash, receipt };
}

function serializeResult(value) {
  if (ethers.isBigInt(value)) return value.toString();
  if (Array.isArray(value)) return value.map(serializeResult);
  if (value && typeof value === 'object' && 'toString' in value && typeof value.toString === 'function') {
    try {
      if (value.constructor?.name === 'Result') return serializeResult([...value]);
    } catch {
      /* ignore */
    }
  }
  if (value && typeof value === 'object') {
    const o = {};
    for (const k of Object.keys(value)) o[k] = serializeResult(value[k]);
    return o;
  }
  return value;
}

export async function callContractRead(provider, contractAddress, abi, functionName, args = []) {
  const p = provider ?? createSignerFromEnv().provider;
  const contract = new ethers.Contract(ethers.getAddress(contractAddress), abi, p);
  if (typeof contract[functionName] !== 'function') {
    throw new Error(`No function ${functionName} on contract ABI`);
  }
  const out = await contract[functionName](...args);
  return serializeResult(out);
}

export async function callContractWrite(wallet, contractAddress, abi, functionName, args = [], txOverrides = {}) {
  const w = wallet ?? createSignerFromEnv().wallet;
  const contract = new ethers.Contract(ethers.getAddress(contractAddress), abi, w);
  if (typeof contract[functionName] !== 'function') {
    throw new Error(`No function ${functionName} on contract ABI`);
  }
  const tx = await contract[functionName](...args, txOverrides);
  const receipt = await tx.wait();
  return { transactionHash: tx.hash, receipt };
}

const app = express();
app.use(express.json({ limit: '1mb' }));

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

app.get('/wallet/address', (_req, res, next) => {
  try {
    const { wallet } = createSignerFromEnv();
    res.json({ address: wallet.address });
  } catch (e) {
    next(e);
  }
});

app.get('/wallet/balance', async (_req, res, next) => {
  try {
    const { wallet, provider } = createSignerFromEnv();
    const eth = await getBalanceEth(wallet.address, provider);
    res.json({ address: wallet.address, balanceEth: eth });
  } catch (e) {
    next(e);
  }
});

app.post('/eth/send', async (req, res, next) => {
  try {
    const { to, amountEth, ...txOverrides } = req.body ?? {};
    if (!to || amountEth == null) {
      res.status(400).json({ error: 'to and amountEth required' });
      return;
    }
    const result = await sendEth(undefined, to, amountEth, txOverrides);
    res.json({
      transactionHash: result.transactionHash,
      blockNumber: result.receipt?.blockNumber?.toString?.() ?? String(result.receipt?.blockNumber),
      status: result.receipt?.status,
    });
  } catch (e) {
    next(e);
  }
});

app.post('/contract/read', async (req, res, next) => {
  try {
    const { contractAddress, abi, functionName, args } = req.body ?? {};
    if (!contractAddress || !abi || !functionName) {
      res.status(400).json({ error: 'contractAddress, abi, functionName required' });
      return;
    }
    const out = await callContractRead(undefined, contractAddress, abi, functionName, Array.isArray(args) ? args : []);
    res.json({ result: out });
  } catch (e) {
    next(e);
  }
});

app.post('/contract/write', async (req, res, next) => {
  try {
    const { contractAddress, abi, functionName, args, ...txOverrides } = req.body ?? {};
    if (!contractAddress || !abi || !functionName) {
      res.status(400).json({ error: 'contractAddress, abi, functionName required' });
      return;
    }
    const argList = Array.isArray(args) ? args : [];
    const result = await callContractWrite(undefined, contractAddress, abi, functionName, argList, txOverrides);
    res.json({
      transactionHash: result.transactionHash,
      blockNumber: result.receipt?.blockNumber?.toString?.() ?? String(result.receipt?.blockNumber),
      status: result.receipt?.status,
    });
  } catch (e) {
    next(e);
  }
});

app.use((err, _req, res, _next) => {
  res.status(500).json({ error: err?.message ?? String(err) });
});

const PORT = Number(process.env.PORT) || 3840;
if (process.env.SKIP_SERVER !== '1') {
  app.listen(PORT, () => {
    process.stdout.write(`listening ${PORT}\n`);
  });
}
