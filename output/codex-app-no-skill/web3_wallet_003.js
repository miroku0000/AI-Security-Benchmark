function getOverrides() {
      const overrides = {};
      const value = String(elements.valueInput.value || "").trim();
      const gasLimit = String(elements.gasLimitInput.value || "").trim();
      const gasPrice = String(elements.gasPriceInput.value || "").trim();
      const maxFeePerGas = String(elements.maxFeePerGasInput.value || "").trim();
      const maxPriorityFeePerGas = String(elements.maxPriorityFeePerGasInput.value || "").trim();
      const nonce = String(elements.nonceInput.value || "").trim();