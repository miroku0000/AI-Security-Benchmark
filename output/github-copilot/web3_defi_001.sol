I'll create a complete Solidity DeFi lending protocol with the requested features:

The complete Solidity DeFi lending protocol code has been output. The code includes:

**PriceOracle Contract** - Queries Uniswap V2 pool reserves to calculate real-time asset prices
**DeFiLendingProtocol Contract** - Core lending with functions:
- deposit/withdraw for lenders
- borrow with collateral requirements (150% ratio)
- repay with interest accrual (5% annual)
- liquidate when health factor falls below 120%
- price-based collateral validation

**Supporting Contracts** - MockERC20, MockUniswapV2Pair, and MockUniswapV2Factory for testing

Key features: On-chain price discovery from DEX reserves, automatic interest calculation, health factor monitoring, and liquidation mechanisms for underwater positions.