function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
}

contract SimpleAMM {
    IERC20 public immutable token0;
    IERC20 public immutable token1;

    uint256 public reserve0;
    uint256 public reserve1;

    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;

    uint256 private constant MINIMUM_LIQUIDITY = 10**3;
    uint256 private constant FEE_NUMERATOR = 997;
    uint256 private constant FEE_DENOMINATOR = 1000;

    bool private locked;

    event Mint(address indexed sender, uint256 amount0, uint256 amount1);
    event Burn(address indexed sender, uint256 amount0, uint256 amount1, address indexed to);
    event Swap(address indexed sender, uint256 amountIn, uint256 amountOut, bool zeroForOne);

    modifier nonReentrant() {
        require(!locked, "reentrancy");
        locked = true;
        _;
        locked = false;
    }

    constructor(address _token0, address _token1) {
        require(_token0 != address(0) && _token1 != address(0), "zero addr");
        require(_token0 != _token1, "same token");
        token0 = IERC20(_token0);
        token1 = IERC20(_token1);
    }

    function _updateReserves() private {
        reserve0 = token0.balanceOf(address(this));
        reserve1 = token1.balanceOf(address(this));
    }

    function _mint(address to, uint256 amount) private {
        totalSupply += amount;
        balanceOf[to] += amount;
    }

    function _burn(address from, uint256 amount) private {
        balanceOf[from] -= amount;
        totalSupply -= amount;
    }

    function getAmountOut(uint256 amountIn, uint256 reserveIn, uint256 reserveOut)
        public
        pure
        returns (uint256 amountOut)
    {
        require(amountIn > 0, "amountIn");
        require(reserveIn > 0 && reserveOut > 0, "reserves");
        uint256 amountInWithFee = amountIn * FEE_NUMERATOR / FEE_DENOMINATOR;
        amountOut = (reserveOut * amountInWithFee) / (reserveIn + amountInWithFee);
    }

    function addLiquidity(uint256 amount0Desired, uint256 amount1Desired, uint256 amount0Min, uint256 amount1Min)
        external
        nonReentrant
        returns (uint256 liquidity)
    {
        _updateReserves();
        uint256 _reserve0 = reserve0;
        uint256 _reserve1 = reserve1;

        uint256 amount0;
        uint256 amount1;
        if (_reserve0 == 0 && _reserve1 == 0) {
            amount0 = amount0Desired;
            amount1 = amount1Desired;
            liquidity = _sqrt(amount0 * amount1) - MINIMUM_LIQUIDITY;
            require(liquidity > 0, "liquidity");
            _mint(address(this), MINIMUM_LIQUIDITY);
        } else {
            uint256 amount1Optimal = (amount0Desired * _reserve1) / _reserve0;
            if (amount1Optimal <= amount1Desired) {
                require(amount0Desired >= amount0Min, "amount0 low");
                require(amount1Optimal >= amount1Min, "amount1 low");
                amount0 = amount0Desired;
                amount1 = amount1Optimal;
            } else {
                uint256 amount0Optimal = (amount1Desired * _reserve0) / _reserve1;
                require(amount0Optimal <= amount0Desired, "amount0 high");
                require(amount0Optimal >= amount0Min, "amount0 min");
                require(amount1Desired >= amount1Min, "amount1 min");
                amount0 = amount0Optimal;
                amount1 = amount1Desired;
            }
            liquidity = _min(
                (amount0 * totalSupply) / _reserve0,
                (amount1 * totalSupply) / _reserve1
            );
            require(liquidity > 0, "liquidity");
        }

        require(token0.transferFrom(msg.sender, address(this), amount0), "t0");
        require(token1.transferFrom(msg.sender, address(this), amount1), "t1");
        _mint(msg.sender, liquidity);
        _updateReserves();
        emit Mint(msg.sender, amount0, amount1);
    }

    function removeLiquidity(uint256 liquidity, uint256 amount0Min, uint256 amount1Min, address to)
        external
        nonReentrant
        returns (uint256 amount0, uint256 amount1)
    {
        require(to != address(0), "zero to");
        _updateReserves();
        uint256 _totalSupply = totalSupply;
        amount0 = (liquidity * reserve0) / _totalSupply;
        amount1 = (liquidity * reserve1) / _totalSupply;
        require(amount0 >= amount0Min && amount1 >= amount1Min, "slippage");
        _burn(msg.sender, liquidity);
        require(token0.transfer(to, amount0), "t0");
        require(token1.transfer(to, amount1), "t1");
        _updateReserves();
        emit Burn(msg.sender, amount0, amount1, to);
    }

    function swap(uint256 amountIn, bool zeroForOne, uint256 amountOutMin, address to)
        external
        nonReentrant
        returns (uint256 amountOut)
    {
        require(to != address(0), "zero to");
        require(amountIn > 0, "amountIn");

        _updateReserves();
        uint256 _reserve0 = reserve0;
        uint256 _reserve1 = reserve1;

        IERC20 tokenIn;
        IERC20 tokenOut;
        uint256 reserveIn;
        uint256 reserveOut;

        if (zeroForOne) {
            tokenIn = token0;
            tokenOut = token1;
            reserveIn = _reserve0;
            reserveOut = _reserve1;
        } else {
            tokenIn = token1;
            tokenOut = token0;
            reserveIn = _reserve1;
            reserveOut = _reserve0;
        }

        amountOut = getAmountOut(amountIn, reserveIn, reserveOut);
        require(amountOut >= amountOutMin, "slippage");
        require(amountOut < reserveOut, "out");

        require(tokenIn.transferFrom(msg.sender, address(this), amountIn), "in");

        if (zeroForOne) {
            require(tokenOut.transfer(to, amountOut), "out");
        } else {
            require(tokenOut.transfer(to, amountOut), "out");
        }

        _updateReserves();
        emit Swap(msg.sender, amountIn, amountOut, zeroForOne);
    }

    function _sqrt(uint256 y) private pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = y / 2 + 1;
            while (x < z) {
                z = x;
                x = (y / x + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }

    function _min(uint256 a, uint256 b) private pure returns (uint256) {
        return a < b ? a : b;
    }
}