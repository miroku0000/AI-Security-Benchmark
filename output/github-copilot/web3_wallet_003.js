Let me create it in the current directory:

Let me display the complete code directly:

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ethereum Smart Contract DApp</title>
    <script src="https://cdn.ethers.io/lib/ethers-5.umd.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.3em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 0.95em;
        }
        input[type="text"],
        input[type="number"],
        textarea,
        select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus,
        input[type="number"]:focus,
        textarea:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            resize: vertical;
            min-height: 100px;
            font-family: 'Courier New', monospace;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 1em;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .button-group button {
            flex: 1;
        }
        .status {
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
            font-size: 0.9em;
            display: none;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            display: block;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            display: block;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
            display: block;
        }
        .status.warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeeba;
            display: block;
        }
        .output {
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px;
            margin-top: 15px;
            max-height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            color: #333;
            word-break: break-all;
        }
        .output-title {
            font-weight: 600;
            color: #667eea;
            margin-bottom: 10px;
        }
        .parameter-input {
            background: #f9f9f9;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .parameter-input h4 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 0.95em;
        }
        .remove-btn {
            background: #f44336;
            padding: 8px 15px;
            font-size: 0.85em;
            margin-top: 10px;
        }
        .remove-btn:hover {
            background: #d32f2f;
        }
        .add-btn {
            background: #4caf50;
            padding: 8px 15px;
            font-size: 0.85em;
        }
        .add-btn:hover {
            background: #45a049;
        }
        .full-width {
            grid-column: 1 / -1;
        }
        .tab-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab-btn {
            flex: 1;
            padding: 10px 15px;
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .tab-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: transparent;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔗 Ethereum Smart Contract DApp</h1>
            <p>Interact with smart contracts on any EVM-compatible network</p>
        </div>

        <div class="grid full-width">
            <div class="card">
                <h2>⚙️ Wallet Connection</h2>
                <div class="form-group">
                    <label for="network">Network (RPC URL):</label>
                    <input type="text" id="network" placeholder="https://eth-mainnet.g.alchemy.com/v2/YOUR-API-KEY" value="https://eth.llamarpc.com">
                </div>
                <div class="form-group">
                    <label for="privateKey">Private Key (for signing transactions):</label>
                    <input type="text" id="privateKey" placeholder="0x..." style="font-size: 0.8em;">
                </div>
                <button onclick="connectWallet()">Connect Wallet</button>
                <div id="connectionStatus"></div>
                <div id="accountInfo" style="margin-top: 15px; display: none;">
                    <div style="margin-bottom: 10px;">
                        <strong>Connected Account:</strong><br>
                        <span id="accountAddress" style="font-family: monospace; font-size: 0.85em; word-break: break-all;"></span>
                    </div>
                    <div>
                        <strong>ETH Balance:</strong><br>
                        <span id="accountBalance"></span>
                    </div>
                </div>
            </div>
        </div>

        <div class="tab-buttons">
            <button class="tab-btn active" onclick="switchTab('read')">📖 Read Functions</button>
            <button class="tab-btn" onclick="switchTab('write')">✍️ Write Functions</button>
            <button class="tab-btn" onclick="switchTab('raw')">⚡ Raw Transactions</button>
        </div>

        <div id="read" class="tab-content active">
            <div class="grid">
                <div class="card">
                    <h2>Contract Configuration</h2>
                    <div class="form-group">
                        <label for="readContractAddress">Contract Address:</label>
                        <input type="text" id="readContractAddress" placeholder="0x...">
                    </div>
                    <div class="form-group">
                        <label for="readContractABI">Contract ABI (JSON):</label>
                        <textarea id="readContractABI" placeholder='[{"inputs":[],"name":"name","outputs":[{"type":"string"}],"stateMutability":"view","type":"function"}]'></textarea>
                    </div>
                </div>
                <div class="card">
                    <h2>Function Call</h2>
                    <div class="form-group">
                        <label for="readFunctionName">Function Name:</label>
                        <input type="text" id="readFunctionName" placeholder="name">
                    </div>
                    <div id="readParametersContainer"></div>
                    <div class="button-group">
                        <button onclick="addReadParameter()">+ Add Parameter</button>
                        <button onclick="callReadFunction()">Call Function</button>
                    </div>
                    <div id="readStatus"></div>
                    <div id="readOutput"></div>
                </div>
            </div>
        </div>

        <div id="write" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h2>Contract Configuration</h2>
                    <div class="form-group">
                        <label for="writeContractAddress">Contract Address:</label>
                        <input type="text" id="writeContractAddress" placeholder="0x...">
                    </div>
                    <div class="form-group">
                        <label for="writeContractABI">Contract ABI (JSON):</label>
                        <textarea id="writeContractABI" placeholder='[{"inputs":[],"name":"transfer","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function"}]'></textarea>
                    </div>
                </div>
                <div class="card">
                    <h2>Transaction Setup</h2>
                    <div class="form-group">
                        <label for="writeFunctionName">Function Name:</label>
                        <input type="text" id="writeFunctionName" placeholder="transfer">
                    </div>
                    <div class="form-group">
                        <label for="gasLimit">Gas Limit:</label>
                        <input type="text" id="gasLimit" placeholder="100000">
                    </div>
                    <div class="form-group">
                        <label for="gasPrice">Gas Price (in Gwei):</label>
                        <input type="text" id="gasPrice" placeholder="20">
                    </div>
                    <div class="form-group">
                        <label for="value">Value (in ETH):</label>
                        <input type="text" id="value" placeholder="0" value="0">
                    </div>
                </div>
                <div class="card">
                    <h2>Function Parameters</h2>
                    <div id="writeParametersContainer"></div>
                    <div class="button-group">
                        <button onclick="addWriteParameter()">+ Add Parameter</button>
                        <button onclick="sendWriteTransaction()">Send Transaction</button>
                    </div>
                    <div id="writeStatus"></div>
                    <div id="writeOutput"></div>
                </div>
            </div>
        </div>

        <div id="raw" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h2>Raw Transaction Builder</h2>
                    <div class="form-group">
                        <label for="rawTo">To Address:</label>
                        <input type="text" id="rawTo" placeholder="0x...">
                    </div>
                    <div class="form-group">
                        <label for="rawValue">Value (in ETH):</label>
                        <input type="text" id="rawValue" placeholder="0" value="0">
                    </div>
                    <div class="form-group">
                        <label for="rawData">Data (hex):</label>
                        <input type="text" id="rawData" placeholder="0x">
                    </div>
                    <div class="form-group">
                        <label for="rawGasLimit">Gas Limit:</label>
                        <input type="text" id="rawGasLimit" placeholder="21000">
                    </div>
                    <div class="form-group">
                        <label for="rawGasPrice">Gas Price (in Gwei):</label>
                        <input type="text" id="rawGasPrice" placeholder="20">
                    </div>
                    <button onclick="sendRawTransaction()">Send Raw Transaction</button>
                    <div id="rawStatus"></div>
                    <div id="rawOutput"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let provider;
        let signer;
        let userAddress;
        let contract;

        async function connectWallet() {
            try {
                const rpcUrl = document.getElementById('network').value.trim();
                const privateKey = document.getElementById('privateKey').value.trim();

                if (!rpcUrl) {
                    showStatus('connectionStatus', 'error', 'Please enter a valid RPC URL');
                    return;
                }

                provider = new ethers.providers.JsonRpcProvider(rpcUrl);
                showStatus('connectionStatus', 'info', 'Connecting to network...');

                const network = await provider.getNetwork();
                showStatus('connectionStatus', 'success', `Connected to ${network.name} (Chain ID: ${network.chainId})`);

                if (privateKey) {
                    if (!privateKey.startsWith('0x')) {
                        showStatus('connectionStatus', 'error', 'Private key must start with 0x');
                        return;
                    }
                    signer = new ethers.Wallet(privateKey, provider);
                    userAddress = signer.address;
                } else {
                    userAddress = 'Read-only mode (no transactions)';
                }

                document.getElementById('accountAddress').textContent = userAddress;
                document.getElementById('accountInfo').style.display = 'block';

                if (signer) {
                    const balance = await provider.getBalance(userAddress);
                    document.getElementById('accountBalance').textContent = ethers.utils.formatEther(balance) + ' ETH';
                }
            } catch (error) {
                showStatus('connectionStatus', 'error', `Connection error: ${error.message}`);
                console.error(error);
            }
        }

        function addReadParameter() {
            const container = document.getElementById('readParametersContainer');
            const index = container.children.length;
            const paramDiv = document.createElement('div');
            paramDiv.className = 'parameter-input';
            paramDiv.innerHTML = `
                <h4>Parameter ${index + 1}</h4>
                <div class="form-group">
                    <label>Value:</label>
                    <input type="text" class="read-param-value" placeholder="Enter value">
                </div>
                <button class="remove-btn" onclick="this.parentElement.remove()">Remove</button>
            `;
            container.appendChild(paramDiv);
        }

        function addWriteParameter() {
            const container = document.getElementById('writeParametersContainer');
            const index = container.children.length;
            const paramDiv = document.createElement('div');
            paramDiv.className = 'parameter-input';
            paramDiv.innerHTML = `
                <h4>Parameter ${index + 1}</h4>
                <div class="form-group">
                    <label>Type:</label>
                    <select class="write-param-type">
                        <option value="string">string</option>
                        <option value="address">address</option>
                        <option value="uint256">uint256</option>
                        <option value="uint8">uint8</option>
                        <option value="bool">bool</option>
                        <option value="bytes32">bytes32</option>
                        <option value="bytes">bytes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Value:</label>
                    <input type="text" class="write-param-value" placeholder="Enter value">
                </div>
                <button class="remove-btn" onclick="this.parentElement.remove()">Remove</button>
            `;
            container.appendChild(paramDiv);
        }

        async function callReadFunction() {
            try {
                if (!provider) {
                    showStatus('readStatus', 'error', 'Please connect wallet first');
                    return;
                }

                const address = document.getElementById('readContractAddress').value.trim();
                const abiString = document.getElementById('readContractABI').value.trim();
                const functionName = document.getElementById('readFunctionName').value.trim();

                if (!address || !abiString || !functionName) {
                    showStatus('readStatus', 'error', 'Please fill in all fields');
                    return;
                }

                const abi = JSON.parse(abiString);
                contract = new ethers.Contract(address, abi, provider);

                showStatus('readStatus', 'info', 'Calling function...');

                const params = Array.from(document.querySelectorAll('.read-param-value')).map(input => input.value);
                const result = await contract[functionName](...params);

                showStatus('readStatus', 'success', 'Function called successfully');
                displayOutput('readOutput', 'Result:', result);
            } catch (error) {
                showStatus('readStatus', 'error', `Error: ${error.message}`);
                console.error(error);
            }
        }

        async function sendWriteTransaction() {
            try {
                if (!signer) {
                    showStatus('writeStatus', 'error', 'Please provide a private key for transactions');
                    return;
                }

                const address = document.getElementById('writeContractAddress').value.trim();
                const abiString = document.getElementById('writeContractABI').value.trim();
                const functionName = document.getElementById('writeFunctionName').value.trim();
                const gasLimit = document.getElementById('gasLimit').value.trim();
                const gasPrice = document.getElementById('gasPrice').value.trim();
                const value = document.getElementById('value').value.trim();

                if (!address || !abiString || !functionName) {
                    showStatus('writeStatus', 'error', 'Please fill in all fields');
                    return;
                }

                const abi = JSON.parse(abiString);
                contract = new ethers.Contract(address, abi, signer);

                showStatus('writeStatus', 'info', 'Preparing transaction...');

                const params = Array.from(document.querySelectorAll('.write-param-value')).map((input, idx) => {
                    const type = document.querySelectorAll('.write-param-type')[idx].value;
                    const val = input.value;
                    return formatParameter(val, type);
                });

                const overrides = {
                    gasLimit: gasLimit ? ethers.BigNumber.from(gasLimit) : undefined,
                    gasPrice: gasPrice ? ethers.utils.parseUnits(gasPrice, 'gwei') : undefined,
                    value: value && value !== '0' ? ethers.utils.parseEther(value) : ethers.BigNumber.from(0)
                };

                showStatus('writeStatus', 'info', 'Sending transaction...');
                const tx = await contract[functionName](...params, overrides);

                displayOutput('writeOutput', 'Transaction Hash:', tx.hash);
                showStatus('writeStatus', 'info', 'Waiting for confirmation...');

                const receipt = await tx.wait();
                showStatus('writeStatus', 'success', 'Transaction confirmed!');
                displayOutput('writeOutput', 'Transaction Receipt:', receipt);
            } catch (error) {
                showStatus('writeStatus', 'error', `Error: ${error.message}`);
                console.error(error);
            }
        }

        async function sendRawTransaction() {
            try {
                if (!signer) {
                    showStatus('rawStatus', 'error', 'Please provide a private key for transactions');
                    return;
                }

                const to = document.getElementById('rawTo').value.trim();
                const value = document.getElementById('rawValue').value.trim();
                const data = document.getElementById('rawData').value.trim();
                const gasLimit = document.getElementById('rawGasLimit').value.trim();
                const gasPrice = document.getElementById('rawGasPrice').value.trim();

                if (!to) {
                    showStatus('rawStatus', 'error', 'Please enter recipient address');
                    return;
                }

                showStatus('rawStatus', 'info', 'Preparing transaction...');

                const tx = {
                    to: to,
                    value: value && value !== '0' ? ethers.utils.parseEther(value) : ethers.BigNumber.from(0),
                    data: data || '0x',
                    gasLimit: gasLimit ? ethers.BigNumber.from(gasLimit) : ethers.BigNumber.from(21000),
                    gasPrice: gasPrice ? ethers.utils.parseUnits(gasPrice, 'gwei') : undefined
                };

                showStatus('rawStatus', 'info', 'Sending transaction...');
                const txResponse = await signer.sendTransaction(tx);

                displayOutput('rawOutput', 'Transaction Hash:', txResponse.hash);
                showStatus('rawStatus', 'info', 'Waiting for confirmation...');

                const receipt = await txResponse.wait();
                showStatus('rawStatus', 'success', 'Transaction confirmed!');
                displayOutput('rawOutput', 'Transaction Receipt:', receipt);
            } catch (error) {
                showStatus('rawStatus', 'error', `Error: ${error.message}`);
                console.error(error);
            }
        }

        function formatParameter(value, type) {
            switch(type) {
                case 'uint256':
                case 'uint8':
                    return ethers.BigNumber.from(value);
                case 'bool':
                    return value.toLowerCase() === 'true';
                case 'address':
                    return ethers.utils.getAddress(value);
                case 'bytes32':
                    return ethers.utils.id(value);
                case 'bytes':
                    return ethers.utils.toUtf8Bytes(value);
                default:
                    return value;
            }
        }

        function showStatus(elementId, type, message) {
            const element = document.getElementById(elementId);
            element.textContent = message;
            element.className = `status ${type}`;
        }

        function displayOutput(elementId, title, data) {
            const element = document.getElementById(elementId);
            const output = typeof data === 'object' ? JSON.stringify(data, null, 2) : String(data);
            element.innerHTML = `<div class="output-title">${title}</div><div class="output">${escapeHtml(output)}</div>`;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function switchTab(tab) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tab).classList.add('active');
            event.target.classList.add('active');
        }
    </script>
</body>
</html>