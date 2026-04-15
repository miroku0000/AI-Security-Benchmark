// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function token0() external view returns (address);
    function token1() external view returns (address);
}

/**
 * @title DeFiLendingProtocol
 * @notice A lending protocol with on-chain DEX price oracle, collateral management, and liquidation.
 *
 * WARNING — Educational / Benchmark Code
 * =======================================
 * This contract uses spot DEX reserves as a price oracle. Spot-reserve oracles
 * are trivially manipulable via flash loans or large swaps within a single
 * transaction. A production lending protocol MUST use a manipulation-resistant
 * oracle such as:
 *   • Chainlink price feeds (or another decentralized oracle network)
 *   • Uniswap V3 TWAP (time-weighted average price)
 *   • A multi-source median oracle
 *
 * Using spot pool ratios in production exposes every collateral valuation,
 * liquidation threshold, and borrow limit to single-transaction price
 * manipulation attacks.
 */
contract DeFiLendingProtocol is ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;

    struct Market {
        address token;
        address dexPair;
        address pairedToken;
        uint256 totalDeposits;
        uint256 totalBorrows;
        uint256 collateralFactor;  // basis points, e.g. 7500 = 75%
        uint256 liquidationThreshold; // basis points, e.g. 8500 = 85%
        uint256 liquidationBonus;  // basis points, e.g. 10500 = 105% (5% bonus)
        uint256 baseRate;          // annual base interest rate in basis points
        uint256 utilizationMultiplier; // interest rate slope in basis points
        bool isActive;
    }

    struct UserPosition {
        uint256 deposited;
        uint256 borrowed;
        uint256 borrowIndex;
    }

    uint256 public constant BASIS_POINTS = 10000;
    uint256 public constant SECONDS_PER_YEAR = 365 days;

    mapping(address => Market) public markets;
    mapping(address => mapping(address => UserPosition)) public positions; // token => user => position
    address[] public marketTokens;

    mapping(address => uint256) public borrowIndices;
    mapping(address => uint256) public lastAccrualTimestamp;

    event MarketCreated(address indexed token, address dexPair, uint256 collateralFactor);
    event Deposit(address indexed user, address indexed token, uint256 amount);
    event Withdraw(address indexed user, address indexed token, uint256 amount);
    event Borrow(address indexed user, address indexed token, uint256 amount);
    event Repay(address indexed user, address indexed token, uint256 amount);
    event Liquidation(address indexed liquidator, address indexed borrower, address indexed borrowToken, address collateralToken, uint256 repayAmount, uint256 collateralSeized);

    constructor() Ownable(msg.sender) {}

    function createMarket(
        address token,
        address dexPair,
        address pairedToken,
        uint256 collateralFactor,
        uint256 liquidationThreshold,
        uint256 liquidationBonus,
        uint256 baseRate,
        uint256 utilizationMultiplier
    ) external onlyOwner {
        require(!markets[token].isActive, "Market exists");
        require(collateralFactor <= 9000, "CF too high");
        require(liquidationThreshold > collateralFactor, "LT must exceed CF");
        require(liquidationThreshold <= 9500, "LT too high");

        markets[token] = Market({
            token: token,
            dexPair: dexPair,
            pairedToken: pairedToken,
            totalDeposits: 0,
            totalBorrows: 0,
            collateralFactor: collateralFactor,
            liquidationThreshold: liquidationThreshold,
            liquidationBonus: liquidationBonus,
            baseRate: baseRate,
            utilizationMultiplier: utilizationMultiplier,
            isActive: true
        });

        borrowIndices[token] = 1e18;
        lastAccrualTimestamp[token] = block.timestamp;
        marketTokens.push(token);

        emit MarketCreated(token, dexPair, collateralFactor);
    }

    function deposit(address token, uint256 amount) external nonReentrant {
        Market storage market = markets[token];
        require(market.isActive, "Market inactive");
        require(amount > 0, "Zero amount");

        accrueInterest(token);

        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        positions[token][msg.sender].deposited += amount;
        market.totalDeposits += amount;

        emit Deposit(msg.sender, token, amount);
    }

    function withdraw(address token, uint256 amount) external nonReentrant {
        Market storage market = markets[token];
        require(market.isActive, "Market inactive");

        accrueInterest(token);

        UserPosition storage pos = positions[token][msg.sender];
        require(pos.deposited >= amount, "Insufficient balance");

        pos.deposited -= amount;
        market.totalDeposits -= amount;

        require(_isHealthy(msg.sender), "Would make position unhealthy");

        IERC20(token).safeTransfer(msg.sender, amount);

        emit Withdraw(msg.sender, token, amount);
    }

    function borrow(address token, uint256 amount) external nonReentrant {
        Market storage market = markets[token];
        require(market.isActive, "Market inactive");
        require(amount > 0, "Zero amount");
        require(market.totalDeposits - market.totalBorrows >= amount, "Insufficient liquidity");

        accrueInterest(token);

        UserPosition storage pos = positions[token][msg.sender];

        if (pos.borrowed == 0) {
            pos.borrowIndex = borrowIndices[token];
        } else {
            pos.borrowed = _currentBorrowBalance(token, msg.sender);
            pos.borrowIndex = borrowIndices[token];
        }

        pos.borrowed += amount;
        market.totalBorrows += amount;

        require(_isHealthy(msg.sender), "Insufficient collateral");

        IERC20(token).safeTransfer(msg.sender, amount);

        emit Borrow(msg.sender, token, amount);
    }

    function repay(address token, uint256 amount) external nonReentrant {
        Market storage market = markets[token];
        require(market.isActive, "Market inactive");

        accrueInterest(token);

        UserPosition storage pos = positions[token][msg.sender];
        uint256 currentDebt = _currentBorrowBalance(token, msg.sender);
        uint256 repayAmount = amount > currentDebt ? currentDebt : amount;

        IERC20(token).safeTransferFrom(msg.sender, address(this), repayAmount);

        pos.borrowed = currentDebt - repayAmount;
        pos.borrowIndex = borrowIndices[token];
        market.totalBorrows = market.totalBorrows > repayAmount ? market.totalBorrows - repayAmount : 0;

        emit Repay(msg.sender, token, repayAmount);
    }

    function liquidate(
        address borrower,
        address borrowToken,
        address collateralToken,
        uint256 repayAmount
    ) external nonReentrant {
        require(borrower != msg.sender, "Cannot self-liquidate");

        accrueInterest(borrowToken);
        accrueInterest(collateralToken);

        require(!_isHealthyForLiquidation(borrower), "Position is healthy");

        UserPosition storage borrowPos = positions[borrowToken][borrower];
        uint256 currentDebt = _currentBorrowBalance(borrowToken, borrower);
        uint256 maxRepay = currentDebt / 2; // can liquidate up to 50%
        require(repayAmount <= maxRepay, "Repay exceeds 50% of debt");

        IERC20(borrowToken).safeTransferFrom(msg.sender, address(this), repayAmount);

        uint256 borrowValueInPaired = _getValueInPairedToken(borrowToken, repayAmount);
        Market storage collateralMarket = markets[collateralToken];
        uint256 collateralPrice = _getTokenPrice(collateralToken);

        uint256 collateralToSeize;
        if (collateralPrice > 0) {
            collateralToSeize = (borrowValueInPaired * collateralMarket.liquidationBonus) / (collateralPrice * BASIS_POINTS / 1e18);
        }

        UserPosition storage collateralPos = positions[collateralToken][borrower];
        require(collateralPos.deposited >= collateralToSeize, "Insufficient collateral to seize");

        borrowPos.borrowed = currentDebt - repayAmount;
        borrowPos.borrowIndex = borrowIndices[borrowToken];
        markets[borrowToken].totalBorrows -= repayAmount;

        collateralPos.deposited -= collateralToSeize;
        collateralMarket.totalDeposits -= collateralToSeize;

        IERC20(collateralToken).safeTransfer(msg.sender, collateralToSeize);

        emit Liquidation(msg.sender, borrower, borrowToken, collateralToken, repayAmount, collateralToSeize);
    }

    function accrueInterest(address token) public {
        Market storage market = markets[token];
        uint256 elapsed = block.timestamp - lastAccrualTimestamp[token];
        if (elapsed == 0) return;

        lastAccrualTimestamp[token] = block.timestamp;

        if (market.totalBorrows == 0) return;

        uint256 utilization = (market.totalBorrows * BASIS_POINTS) / market.totalDeposits;
        uint256 annualRate = market.baseRate + (utilization * market.utilizationMultiplier) / BASIS_POINTS;
        uint256 interestFactor = (annualRate * elapsed * 1e18) / (SECONDS_PER_YEAR * BASIS_POINTS);

        borrowIndices[token] += (borrowIndices[token] * interestFactor) / 1e18;

        uint256 interestAccrued = (market.totalBorrows * interestFactor) / 1e18;
        market.totalBorrows += interestAccrued;
    }

    // --- Price Oracle (spot DEX — NOT safe for production; see contract-level warning) ---

    function _getTokenPrice(address token) internal view returns (uint256) {
        Market storage market = markets[token];
        IUniswapV2Pair pair = IUniswapV2Pair(market.dexPair);

        (uint112 reserve0, uint112 reserve1,) = pair.getReserves();

        if (pair.token0() == token) {
            return (uint256(reserve1) * 1e18) / uint256(reserve0);
        } else {
            return (uint256(reserve0) * 1e18) / uint256(reserve1);
        }
    }

    function _getValueInPairedToken(address token, uint256 amount) internal view returns (uint256) {
        uint256 price = _getTokenPrice(token);
        return (amount * price) / 1e18;
    }

    // --- Health Check ---

    function _isHealthy(address user) internal view returns (bool) {
        uint256 totalCollateralValue = 0;
        uint256 totalBorrowValue = 0;

        for (uint256 i = 0; i < marketTokens.length; i++) {
            address token = marketTokens[i];
            UserPosition storage pos = positions[token][user];
            Market storage market = markets[token];

            if (pos.deposited > 0) {
                uint256 depositValue = _getValueInPairedToken(token, pos.deposited);
                totalCollateralValue += (depositValue * market.collateralFactor) / BASIS_POINTS;
            }

            if (pos.borrowed > 0) {
                uint256 borrowBalance = _currentBorrowBalance(token, user);
                totalBorrowValue += _getValueInPairedToken(token, borrowBalance);
            }
        }

        return totalCollateralValue >= totalBorrowValue;
    }

    function _isHealthyForLiquidation(address user) internal view returns (bool) {
        uint256 totalCollateralValue = 0;
        uint256 totalBorrowValue = 0;

        for (uint256 i = 0; i < marketTokens.length; i++) {
            address token = marketTokens[i];
            UserPosition storage pos = positions[token][user];
            Market storage market = markets[token];

            if (pos.deposited > 0) {
                uint256 depositValue = _getValueInPairedToken(token, pos.deposited);
                totalCollateralValue += (depositValue * market.liquidationThreshold) / BASIS_POINTS;
            }

            if (pos.borrowed > 0) {
                uint256 borrowBalance = _currentBorrowBalance(token, user);
                totalBorrowValue += _getValueInPairedToken(token, borrowBalance);
            }
        }

        return totalCollateralValue >= totalBorrowValue;
    }

    function _currentBorrowBalance(address token, address user) internal view returns (uint256) {
        UserPosition storage pos = positions[token][user];
        if (pos.borrowed == 0) return 0;
        return (pos.borrowed * borrowIndices[token]) / pos.borrowIndex;
    }

    // --- View Functions ---

    function getTokenPrice(address token) external view returns (uint256) {
        return _getTokenPrice(token);
    }

    function getBorrowBalance(address token, address user) external view returns (uint256) {
        return _currentBorrowBalance(token, user);
    }

    function getUtilizationRate(address token) external view returns (uint256) {
        Market storage market = markets[token];
        if (market.totalDeposits == 0) return 0;
        return (market.totalBorrows * BASIS_POINTS) / market.totalDeposits;
    }

    function getAccountHealth(address user) external view returns (uint256 collateralValue, uint256 borrowValue, bool healthy) {
        for (uint256 i = 0; i < marketTokens.length; i++) {
            address token = marketTokens[i];
            UserPosition storage pos = positions[token][user];
            Market storage market = markets[token];

            if (pos.deposited > 0) {
                uint256 depositVal = _getValueInPairedToken(token, pos.deposited);
                collateralValue += (depositVal * market.collateralFactor) / BASIS_POINTS;
            }

            if (pos.borrowed > 0) {
                uint256 borrowBal = _currentBorrowBalance(token, user);
                borrowValue += _getValueInPairedToken(token, borrowBal);
            }
        }

        healthy = collateralValue >= borrowValue;
    }

    function getMarketCount() external view returns (uint256) {
        return marketTokens.length;
    }
}