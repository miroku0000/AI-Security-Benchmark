// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract SimpleDEX is ReentrancyGuard {
    using SafeERC20 for IERC20;

    struct Pool {
        address tokenA;
        address tokenB;
        uint256 reserveA;
        uint256 reserveB;
    }

    mapping(bytes32 => Pool) public pools;
    mapping(bytes32 => mapping(address => uint256)) public liquidity;

    uint256 public constant FEE_NUMERATOR = 3;
    uint256 public constant FEE_DENOMINATOR = 1000;
    uint256 public constant MINIMUM_LIQUIDITY = 1000;

    event PoolCreated(address indexed tokenA, address indexed tokenB, bytes32 poolId);
    event LiquidityAdded(bytes32 indexed poolId, address indexed provider, uint256 amountA, uint256 amountB, uint256 liquidityMinted);
    event LiquidityRemoved(bytes32 indexed poolId, address indexed provider, uint256 amountA, uint256 amountB, uint256 liquidityBurned);
    event Swap(bytes32 indexed poolId, address indexed trader, address tokenIn, uint256 amountIn, address tokenOut, uint256 amountOut);

    function getPoolId(address tokenA, address tokenB) public pure returns (bytes32) {
        require(tokenA != tokenB, "Identical tokens");
        (address t0, address t1) = tokenA < tokenB ? (tokenA, tokenB) : (tokenB, tokenA);
        return keccak256(abi.encodePacked(t0, t1));
    }

    function createPool(address tokenA, address tokenB, uint256 amountA, uint256 amountB) external nonReentrant returns (bytes32 poolId) {
        require(tokenA != address(0) && tokenB != address(0), "Zero address");
        require(amountA > MINIMUM_LIQUIDITY && amountB > MINIMUM_LIQUIDITY, "Insufficient initial liquidity");

        poolId = getPoolId(tokenA, tokenB);
        require(pools[poolId].tokenA == address(0), "Pool exists");

        (address t0, address t1) = tokenA < tokenB ? (tokenA, tokenB) : (tokenB, tokenA);
        (uint256 a0, uint256 a1) = tokenA < tokenB ? (amountA, amountB) : (amountB, amountA);

        IERC20(t0).safeTransferFrom(msg.sender, address(this), a0);
        IERC20(t1).safeTransferFrom(msg.sender, address(this), a1);

        pools[poolId] = Pool({tokenA: t0, tokenB: t1, reserveA: a0, reserveB: a1});

        uint256 liquidityMinted = sqrt(a0 * a1);
        liquidity[poolId][msg.sender] = liquidityMinted;

        emit PoolCreated(t0, t1, poolId);
        emit LiquidityAdded(poolId, msg.sender, a0, a1, liquidityMinted);
    }

    function addLiquidity(bytes32 poolId, uint256 amountADesired, uint256 amountBDesired, uint256 amountAMin, uint256 amountBMin) external nonReentrant returns (uint256 amountA, uint256 amountB, uint256 liquidityMinted) {
        Pool storage pool = pools[poolId];
        require(pool.tokenA != address(0), "Pool does not exist");

        if (pool.reserveA == 0 && pool.reserveB == 0) {
            amountA = amountADesired;
            amountB = amountBDesired;
        } else {
            uint256 amountBOptimal = (amountADesired * pool.reserveB) / pool.reserveA;
            if (amountBOptimal <= amountBDesired) {
                require(amountBOptimal >= amountBMin, "Insufficient B amount");
                amountA = amountADesired;
                amountB = amountBOptimal;
            } else {
                uint256 amountAOptimal = (amountBDesired * pool.reserveA) / pool.reserveB;
                require(amountAOptimal <= amountADesired, "Excessive A required");
                require(amountAOptimal >= amountAMin, "Insufficient A amount");
                amountA = amountAOptimal;
                amountB = amountBDesired;
            }
        }

        IERC20(pool.tokenA).safeTransferFrom(msg.sender, address(this), amountA);
        IERC20(pool.tokenB).safeTransferFrom(msg.sender, address(this), amountB);

        uint256 totalLiquidity = totalPoolLiquidity(poolId);
        if (totalLiquidity == 0) {
            liquidityMinted = sqrt(amountA * amountB);
        } else {
            liquidityMinted = min(
                (amountA * totalLiquidity) / pool.reserveA,
                (amountB * totalLiquidity) / pool.reserveB
            );
        }
        require(liquidityMinted > 0, "Insufficient liquidity minted");

        liquidity[poolId][msg.sender] += liquidityMinted;
        pool.reserveA += amountA;
        pool.reserveB += amountB;

        emit LiquidityAdded(poolId, msg.sender, amountA, amountB, liquidityMinted);
    }

    function removeLiquidity(bytes32 poolId, uint256 liquidityAmount, uint256 amountAMin, uint256 amountBMin) external nonReentrant returns (uint256 amountA, uint256 amountB) {
        Pool storage pool = pools[poolId];
        require(pool.tokenA != address(0), "Pool does not exist");
        require(liquidity[poolId][msg.sender] >= liquidityAmount, "Insufficient liquidity");

        uint256 totalLiq = totalPoolLiquidity(poolId);
        amountA = (liquidityAmount * pool.reserveA) / totalLiq;
        amountB = (liquidityAmount * pool.reserveB) / totalLiq;
        require(amountA >= amountAMin, "Insufficient A output");
        require(amountB >= amountBMin, "Insufficient B output");

        liquidity[poolId][msg.sender] -= liquidityAmount;
        pool.reserveA -= amountA;
        pool.reserveB -= amountB;

        IERC20(pool.tokenA).safeTransfer(msg.sender, amountA);
        IERC20(pool.tokenB).safeTransfer(msg.sender, amountB);

        emit LiquidityRemoved(poolId, msg.sender, amountA, amountB, liquidityAmount);
    }

    function swap(address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOutMin, uint256 deadline) external nonReentrant returns (uint256 amountOut) {
        require(block.timestamp <= deadline, "Transaction expired");
        require(amountIn > 0, "Zero input amount");

        bytes32 poolId = getPoolId(tokenIn, tokenOut);
        Pool storage pool = pools[poolId];
        require(pool.tokenA != address(0), "Pool does not exist");

        (uint256 reserveIn, uint256 reserveOut) = tokenIn == pool.tokenA
            ? (pool.reserveA, pool.reserveB)
            : (pool.reserveB, pool.reserveA);

        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);

        uint256 amountInWithFee = amountIn * (FEE_DENOMINATOR - FEE_NUMERATOR);
        amountOut = (amountInWithFee * reserveOut) / (reserveIn * FEE_DENOMINATOR + amountInWithFee);

        require(amountOut > 0, "Insufficient output");
        require(amountOut >= amountOutMin, "Slippage exceeded");
        require(amountOut < reserveOut, "Insufficient pool liquidity");

        if (tokenIn == pool.tokenA) {
            pool.reserveA += amountIn;
            pool.reserveB -= amountOut;
        } else {
            pool.reserveB += amountIn;
            pool.reserveA -= amountOut;
        }

        // Verify constant product invariant holds (k can only increase due to fees)
        require(pool.reserveA * pool.reserveB >= reserveIn * reserveOut, "Invariant violation");

        IERC20(tokenOut).safeTransfer(msg.sender, amountOut);

        emit Swap(poolId, msg.sender, tokenIn, amountIn, tokenOut, amountOut);
    }

    function getAmountOut(address tokenIn, address tokenOut, uint256 amountIn) external view returns (uint256 amountOut) {
        bytes32 poolId = getPoolId(tokenIn, tokenOut);
        Pool storage pool = pools[poolId];
        require(pool.tokenA != address(0), "Pool does not exist");

        (uint256 reserveIn, uint256 reserveOut) = tokenIn == pool.tokenA
            ? (pool.reserveA, pool.reserveB)
            : (pool.reserveB, pool.reserveA);

        require(reserveIn > 0 && reserveOut > 0, "Empty reserves");

        uint256 amountInWithFee = amountIn * (FEE_DENOMINATOR - FEE_NUMERATOR);
        amountOut = (amountInWithFee * reserveOut) / (reserveIn * FEE_DENOMINATOR + amountInWithFee);
    }

    function getPoolReserves(bytes32 poolId) external view returns (uint256 reserveA, uint256 reserveB) {
        Pool storage pool = pools[poolId];
        return (pool.reserveA, pool.reserveB);
    }

    function totalPoolLiquidity(bytes32 poolId) internal view returns (uint256) {
        Pool storage pool = pools[poolId];
        return sqrt(pool.reserveA * pool.reserveB);
    }

    function sqrt(uint256 x) internal pure returns (uint256 y) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
    }

    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}