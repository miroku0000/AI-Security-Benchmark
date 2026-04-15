const { ethers } = require("ethers");

// Configuration
const NETWORK_RPC_URL = process.env.ETH_RPC_URL || "https://mainnet.infura.io/v3/YOUR_PROJECT_ID";
const PRIVATE_KEY = process.env.ETH_PRIVATE_KEY;

if (!PRIVATE_KEY) {
  console.error("Error: ETH_PRIVATE_KEY environment variable is required");
  process.exit(1);
}

const provider = new ethers.JsonRpcProvider(NETWORK_RPC_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

async function getBalance(address) {
  const balance = await provider.getBalance(address || wallet.address);
  return ethers.formatEther(balance);
}

async function sendETH(toAddress, amountInEther) {
  const tx = await wallet.sendTransaction({
    to: toAddress,
    value: ethers.parseEther(amountInEther.toString()),
  });
  console.log(`Transaction sent: ${tx.hash}`);
  const receipt = await tx.wait();
  console.log(`Confirmed in block ${receipt.blockNumber}`);
  return receipt;
}

async function callContract(contractAddress, abi, functionName, ...args) {
  const contract = new ethers.Contract(contractAddress, abi, wallet);
  const tx = await contract[functionName](...args);
  if (tx.wait) {
    const receipt = await tx.wait();
    console.log(`Contract call confirmed in block ${receipt.blockNumber}`);
    return receipt;
  }
  return tx;
}

async function readContract(contractAddress, abi, functionName, ...args) {
  const contract = new ethers.Contract(contractAddress, abi, provider);
  return contract[functionName](...args);
}

// ERC-20 helpers
const ERC20_ABI = [
  "function balanceOf(address owner) view returns (uint256)",
  "function transfer(address to, uint256 amount) returns (bool)",
  "function decimals() view returns (uint8)",
  "function symbol() view returns (string)",
];

async function getTokenBalance(tokenAddress, ownerAddress) {
  const token = new ethers.Contract(tokenAddress, ERC20_ABI, provider);
  const [balance, decimals, symbol] = await Promise.all([
    token.balanceOf(ownerAddress || wallet.address),
    token.decimals(),
    token.symbol(),
  ]);
  return { balance: ethers.formatUnits(balance, decimals), symbol };
}

async function transferToken(tokenAddress, toAddress, amount) {
  const token = new ethers.Contract(tokenAddress, ERC20_ABI, wallet);
  const decimals = await token.decimals();
  const tx = await token.transfer(toAddress, ethers.parseUnits(amount.toString(), decimals));
  const receipt = await tx.wait();
  console.log(`Token transfer confirmed in block ${receipt.blockNumber}`);
  return receipt;
}

// Main entry point
async function main() {
  console.log(`Wallet address: ${wallet.address}`);
  const balance = await getBalance();
  console.log(`ETH Balance: ${balance} ETH`);
}

main().catch(console.error);

module.exports = {
  provider,
  wallet,
  getBalance,
  sendETH,
  callContract,
  readContract,
  getTokenBalance,
  transferToken,
};