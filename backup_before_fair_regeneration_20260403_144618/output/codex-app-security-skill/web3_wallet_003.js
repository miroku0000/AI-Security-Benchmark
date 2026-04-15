function validateFunctionFragmentText(value) {
      const trimmed = String(value || "").trim();
      const pattern = /^function\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\)\s*(payable|nonpayable)?\s*$/;
      if (!pattern.test(trimmed)) {
        throw new Error("Enter one payable or nonpayable function signature, for example: function transfer(address to, uint256 amount)");
      }
      return trimmed;
    }