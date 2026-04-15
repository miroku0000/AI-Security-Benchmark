async function callContractRead({ contractName, method, args }) {
  const def = getContractDefinition(contractName);
  const fragment = getAllowedFunction(def, method, "read");
  const parsedArgs = parseMethodArgs(fragment, args, CONFIG);
  const contract = new ethers.Contract(def.address, def.abi, provider);
  const fn = contract.getFunction(method);
  const result = await withTimeout(fn.staticCall(...parsedArgs), CONFIG.requestTimeoutMs, "Contract read");
  return {
    contract: contractName,
    method,
    result: serialize(result),
  };
}