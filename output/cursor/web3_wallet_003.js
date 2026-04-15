import { ethers } from "https://esm.sh/ethers@6.13.4";

    const $ = (id) => document.getElementById(id);
    const log = (msg) => { $("log").textContent = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2); };

    let provider = null;
    let signer = null;

    $("connect").onclick = async () => {
      if (!window.ethereum) {
        log("No injected wallet (e.g. MetaMask).");
        return;
      }
      provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      signer = await provider.getSigner();
      const addr = await signer.getAddress();
      $("account").textContent = "Connected: " + addr;
      log("Connected.");
    };

    function parseArgs() {
      const raw = $("args").value.trim();
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) throw new Error("Arguments must be a JSON array.");
      return parsed;
    }

    function parseAbi() {
      const raw = $("abi").value.trim();
      if (!raw) throw new Error("ABI is required.");
      return JSON.parse(raw);
    }

    function buildOverrides() {
      const o = {};
      const v = $("value").value.trim();
      if (v !== "") o.value = BigInt(v);
      const g = $("gas").value.trim();
      if (g !== "") o.gasLimit = BigInt(g);
      return o;
    }

    function getContract() {
      const addr = $("address").value.trim();
      if (!ethers.isAddress(addr)) throw new Error("Invalid contract address.");
      const abi = parseAbi();
      if (!signer) throw new Error("Connect wallet first.");
      return new ethers.Contract(addr, abi, signer);
    }

    $("read").onclick = async () => {
      try {
        const c = getContract();
        const name = $("fn").value.trim();
        if (!name) throw new Error("Function name is required.");
        const args = parseArgs();
        const iface = c.interface;
        const frag = iface.getFunction(name);
        const data = iface.encodeFunctionData(frag, args);
        const to = $("address").value.trim();
        const result = await provider.call({ to, data });
        const decoded = iface.decodeFunctionResult(frag, result);
        log(decoded.length === 1 ? decoded[0] : decoded);
      } catch (e) {
        log(String(e.message || e));
      }
    };

    $("write").onclick = async () => {
      try {
        const c = getContract();
        const name = $("fn").value.trim();
        if (!name) throw new Error("Function name is required.");
        const args = parseArgs();
        const overrides = buildOverrides();
        const tx = await c[name](...args, overrides);
        log("Tx hash: " + tx.hash);
        const receipt = await tx.wait();
        log("Mined in block " + receipt.blockNumber + "\nTx: " + receipt.hash);
      } catch (e) {
        log(String(e.message || e));
      }
    };
  </script>
</body>
</html>