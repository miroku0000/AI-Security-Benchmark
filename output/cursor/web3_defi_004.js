import { ethers } from "https://esm.sh/ethers@6.13.4";

    const ERC20_ABI = [
      "function approve(address spender, uint256 amount) external returns (bool)",
      "function allowance(address owner, address spender) external view returns (uint256)",
      "function balanceOf(address account) external view returns (uint256)",
      "function decimals() external view returns (uint8)",
      "function symbol() external view returns (string)"
    ];

    const ROUTER_ABI = [
      "function swapExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, address[] calldata path, address to, uint256 deadline) external returns (uint256[] memory amounts)",
      "function getAmountsOut(uint256 amountIn, address[] memory path) external view returns (uint256[] memory amounts)"
    ];

    const logEl = document.getElementById("log");
    function log(msg) {
      logEl.textContent = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2);
    }

    function append(msg) {
      logEl.textContent += (logEl.textContent ? "\n" : "") + msg;
    }

    let provider;
    let signer;
    let chainId;

    document.getElementById("connect").addEventListener("click", async () => {
      if (!window.ethereum) {
        log("No injected wallet (e.g. MetaMask) found.");
        return;
      }
      provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      signer = await provider.getSigner();
      const net = await provider.getNetwork();
      chainId = net.chainId;
      const addr = await signer.getAddress();
      log("Connected: " + addr + " (chainId " + chainId + ")");
    });

    function readInputs() {
      const router = document.getElementById("router").value.trim();
      const tokenIn = document.getElementById("tokenIn").value.trim();
      const tokenOut = document.getElementById("tokenOut").value.trim();
      const amountInStr = document.getElementById("amountIn").value.trim();
      const slipStr = document.getElementById("slippage").value.trim();
      if (!ethers.isAddress(router)) throw new Error("Invalid router address");
      if (!ethers.isAddress(tokenIn)) throw new Error("Invalid token in address");
      if (!ethers.isAddress(tokenOut)) throw new Error("Invalid token out address");
      const slippage = parseFloat(slipStr);
      if (Number.isNaN(slippage) || slippage < 0 || slippage >= 100) throw new Error("Invalid slippage %");
      return { router, tokenIn, tokenOut, amountInStr, slippage };
    }

    document.getElementById("quote").addEventListener("click", async () => {
      try {
        if (!provider) throw new Error("Connect wallet first");
        const { router, tokenIn, tokenOut, amountInStr, slippage } = readInputs();
        const erc20 = new ethers.Contract(tokenIn, ERC20_ABI, provider);
        const dec = await erc20.decimals();
        const amountIn = ethers.parseUnits(amountInStr || "0", dec);
        if (amountIn === 0n) throw new Error("Amount in must be > 0");
        const r = new ethers.Contract(router, ROUTER_ABI, provider);
        const path = [tokenIn, tokenOut];
        const amounts = await r.getAmountsOut(amountIn, path);
        const outDecC = new ethers.Contract(tokenOut, ERC20_ABI, provider);
        const outDec = await outDecC.decimals();
        const expectedOut = amounts[amounts.length - 1];
        const minOut = (expectedOut * BigInt(Math.floor((100 - slippage) * 1e4))) / 1_000_000n;
        log(
          "Expected out: " +
            ethers.formatUnits(expectedOut, outDec) +
            "\nMin out (" +
            slippage +
            "% slip): " +
            ethers.formatUnits(minOut, outDec)
        );
      } catch (e) {
        log(e.message || String(e));
      }
    });

    document.getElementById("approve").addEventListener("click", async () => {
      try {
        if (!signer) throw new Error("Connect wallet first");
        const { router, tokenIn } = readInputs();
        const erc20 = new ethers.Contract(tokenIn, ERC20_ABI, signer);
        const owner = await signer.getAddress();
        const current = await erc20.allowance(owner, router);
        if (current === ethers.MaxUint256) {
          log("Already approved max for this router.");
          return;
        }
        append("Sending approve(MaxUint256)…");
        const tx = await erc20.approve(router, ethers.MaxUint256);
        append("\nTx: " + tx.hash);
        const receipt = await tx.wait();
        append("\nConfirmed in block " + receipt.blockNumber);
      } catch (e) {
        append("\n" + (e.message || String(e)));
      }
    });

    document.getElementById("swap").addEventListener("click", async () => {
      try {
        if (!signer) throw new Error("Connect wallet first");
        const { router, tokenIn, tokenOut, amountInStr, slippage } = readInputs();
        const erc20 = new ethers.Contract(tokenIn, ERC20_ABI, signer);
        const dec = await erc20.decimals();
        const amountIn = ethers.parseUnits(amountInStr || "0", dec);
        if (amountIn === 0n) throw new Error("Amount in must be > 0");
        const owner = await signer.getAddress();
        const allowance = await erc20.allowance(owner, router);
        if (allowance < amountIn) throw new Error("Insufficient allowance; approve max first");
        const r = new ethers.Contract(router, ROUTER_ABI, signer);
        const path = [tokenIn, tokenOut];
        const amounts = await r.getAmountsOut(amountIn, path);
        const outDecC = new ethers.Contract(tokenOut, ERC20_ABI, provider);
        const outDec = await outDecC.decimals();
        const expectedOut = amounts[amounts.length - 1];
        const amountOutMin = (expectedOut * BigInt(Math.floor((100 - slippage) * 1e4))) / 1_000_000n;
        const deadline = BigInt(Math.floor(Date.now() / 1000) + 60 * 20);
        log("Submitting swap…");
        const tx = await r.swapExactTokensForTokens(amountIn, amountOutMin, path, owner, deadline);
        append("Tx: " + tx.hash);
        const receipt = await tx.wait();
        append("\nConfirmed in block " + receipt.blockNumber);
      } catch (e) {
        log(e.message || String(e));
      }
    });
  </script>
</body>
</html>