// Harness — Hardhat config. Uses the bundled in-process EVM (no external
// node required). Compiles Solidity 0.8.x.
require('@nomicfoundation/hardhat-toolbox');

module.exports = {
    solidity: '0.8.20',
    paths: {
        sources: './contracts',
        tests: './test',
        cache: './cache',
        artifacts: './artifacts',
    },
};
