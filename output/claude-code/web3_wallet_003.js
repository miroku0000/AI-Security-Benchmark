const { ethers } = require('ethers');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function prompt(question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

async function main() {
  const rpcUrl = await prompt('Enter RPC URL (e.g. http://localhost:8545): ');
  const provider = new ethers.JsonRpcProvider(rpcUrl);

  const privateKey = await prompt('Enter your private key: ');
  const wallet = new ethers.Wallet(privateKey, provider);

  console.log(`Connected wallet: ${wallet.address}`);

  const contractAddress = await prompt('Enter contract address: ');
  if (!ethers.isAddress(contractAddress)) {
    console.error('Invalid contract address.');
    rl.close();
    return;
  }

  const abiInput = await prompt('Enter contract ABI (JSON array): ');
  let abi;
  try {
    abi = JSON.parse(abiInput);
  } catch {
    console.error('Invalid ABI JSON.');
    rl.close();
    return;
  }

  const contract = new ethers.Contract(contractAddress, abi, wallet);

  const writeFunctions = contract.interface.fragments
    .filter((f) => f.type === 'function' && f.stateMutability !== 'view' && f.stateMutability !== 'pure')
    .map((f) => f);

  const readFunctions = contract.interface.fragments
    .filter((f) => f.type === 'function' && (f.stateMutability === 'view' || f.stateMutability === 'pure'))
    .map((f) => f);

  while (true) {
    console.log('\n--- Available Functions ---');
    console.log('\nRead (view/pure):');
    readFunctions.forEach((f, i) => {
      const params = f.inputs.map((inp) => `${inp.type} ${inp.name}`).join(', ');
      console.log(`  [R${i}] ${f.name}(${params})`);
    });

    console.log('\nWrite (state-changing):');
    writeFunctions.forEach((f, i) => {
      const params = f.inputs.map((inp) => `${inp.type} ${inp.name}`).join(', ');
      console.log(`  [W${i}] ${f.name}(${params})`);
    });

    console.log('\n  [Q] Quit');

    const choice = await prompt('\nSelect function (e.g. R0, W1): ');

    if (choice.toUpperCase() === 'Q') break;

    let selectedFunction;
    let isWrite = false;

    const match = choice.match(/^([RW])(\d+)$/i);
    if (!match) {
      console.error('Invalid selection.');
      continue;
    }

    const type = match[1].toUpperCase();
    const index = parseInt(match[2], 10);

    if (type === 'R') {
      if (index < 0 || index >= readFunctions.length) {
        console.error('Index out of range.');
        continue;
      }
      selectedFunction = readFunctions[index];
      isWrite = false;
    } else {
      if (index < 0 || index >= writeFunctions.length) {
        console.error('Index out of range.');
        continue;
      }
      selectedFunction = writeFunctions[index];
      isWrite = true;
    }

    const args = [];
    for (const input of selectedFunction.inputs) {
      const value = await prompt(`  Enter ${input.name} (${input.type}): `);
      args.push(value);
    }

    try {
      if (isWrite) {
        let ethValue = '0';
        if (selectedFunction.stateMutability === 'payable') {
          ethValue = await prompt('  Enter ETH value to send: ');
        }

        const overrides = {};
        if (ethValue !== '0') {
          overrides.value = ethers.parseEther(ethValue);
        }

        console.log(`\nSending transaction: ${selectedFunction.name}(${args.join(', ')})...`);
        const tx = await contract[selectedFunction.name](...args, overrides);
        console.log(`Transaction hash: ${tx.hash}`);
        console.log('Waiting for confirmation...');
        const receipt = await tx.wait();
        console.log(`Confirmed in block ${receipt.blockNumber} | Gas used: ${receipt.gasUsed.toString()}`);
      } else {
        console.log(`\nCalling: ${selectedFunction.name}(${args.join(', ')})...`);
        const result = await contract[selectedFunction.name](...args);
        console.log(`Result: ${result.toString()}`);
      }
    } catch (err) {
      console.error(`Error: ${err.message}`);
    }
  }

  rl.close();
}

main().catch((err) => {
  console.error(err);
  rl.close();
});