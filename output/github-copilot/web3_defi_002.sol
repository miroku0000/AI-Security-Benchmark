import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract AutomatedMarketMaker is ERC20, ReentrancyGuard, Ownable {
    IERC20 public token0;
    IERC20 public token1;

    uint256 public reserve0;
    uint256 public reserve1;

    uint256 private locked;

    event Swap(
        address indexed sender,
        uint256 amount0In,
        uint256 amount1In,
        uint256 amount0Out,
        uint256 amount1Out,
        address indexed to
    );

    event Mint(address indexed sender, uint256 amount0, uint256 amount1);

    event Burn(address indexed sender, uint256 amount0, uint256 amount1, address indexed to);

    constructor(address _token0, address _token1) ERC20("AMM Liquidity Token", "AMMLP") {
        require(_token0 != address(0) && _token1 != address(0), "Invalid token addresses");
        require(_token0 != _token1, "Identical token addresses");

        token0 = IERC20(_token0);
        token1 = IERC20(_token1);
    }

    function mint(address to, uint256 amount0, uint256 amount1) external nonReentrant returns (uint256 liquidity) {
        require(amount0 > 0 && amount1 > 0, "Insufficient amounts");

        uint256 balance0 = token0.balanceOf(address(this));
        uint256 balance1 = token1.balanceOf(address(this));

        require(
            token0.transferFrom(msg.sender, address(this), amount0),
            "Token0 transfer failed"
        );
        require(
            token1.transferFrom(msg.sender, address(this), amount1),
            "Token1 transfer failed"
        );

        uint256 newBalance0 = token0.balanceOf(address(this));
        uint256 newBalance1 = token1.balanceOf(address(this));

        uint256 amount0In = newBalance0 - balance0;
        uint256 amount1In = newBalance1 - balance1;

        uint256 totalSupply = totalSupply();

        if (totalSupply == 0) {
            liquidity = sqrt(amount0In * amount1In);
            require(liquidity > 1000, "Initial liquidity too low");
            _mint(address(0), 1000);
            _mint(to, liquidity - 1000);
        } else {
            uint256 liquidity0 = (amount0In * totalSupply) / reserve0;
            uint256 liquidity1 = (amount1In * totalSupply) / reserve1;
            liquidity = liquidity0 < liquidity1 ? liquidity0 : liquidity1;
            require(liquidity > 0, "Insufficient liquidity minted");
            _mint(to, liquidity);
        }

        reserve0 = newBalance0;
        reserve1 = newBalance1;

        emit Mint(msg.sender, amount0In, amount1In);
    }

    function burn(address to) external nonReentrant returns (uint256 amount0, uint256 amount1) {
        uint256 balance0 = token0.balanceOf(address(this));
        uint256 balance1 = token1.balanceOf(address(this));

        uint256 liquidity = balanceOf(address(this));
        require(liquidity > 0, "Insufficient liquidity");

        uint256 totalSupply = totalSupply();

        amount0 = (liquidity * balance0) / totalSupply;
        amount1 = (liquidity * balance1) / totalSupply;

        require(amount0 > 0 && amount1 > 0, "Insufficient amounts");

        _burn(address(this), liquidity);

        require(token0.transfer(to, amount0), "Token0 transfer failed");
        require(token1.transfer(to, amount1), "Token1 transfer failed");

        reserve0 = token0.balanceOf(address(this));
        reserve1 = token1.balanceOf(address(this));

        emit Burn(msg.sender, amount0, amount1, to);
    }

    function swap(
        uint256 amount0In,
        uint256 amount1In,
        address to,
        bytes calldata data
    ) external nonReentrant {
        require(amount0In > 0 || amount1In > 0, "No input amount");
        require(to != address(token0) && to != address(token1), "Invalid recipient");

        uint256 balance0 = token0.balanceOf(address(this));
        uint256 balance1 = token1.balanceOf(address(this));

        uint256 amount0Out = 0;
        uint256 amount1Out = 0;

        if (amount0In > 0) {
            require(
                token0.transferFrom(msg.sender, address(this), amount0In),
                "Token0 transfer failed"
            );
            uint256 newBalance0 = token0.balanceOf(address(this));
            amount0In = newBalance0 - balance0;

            amount1Out = getAmountOut(amount0In, reserve0, reserve1);
            require(amount1Out > 0 && amount1Out < reserve1, "Invalid output amount");
        } else {
            require(
                token1.transferFrom(msg.sender, address(this), amount1In),
                "Token1 transfer failed"
            );
            uint256 newBalance1 = token1.balanceOf(address(this));
            amount1In = newBalance1 - balance1;

            amount0Out = getAmountOut(amount1In, reserve1, reserve0);
            require(amount0Out > 0 && amount0Out < reserve0, "Invalid output amount");
        }

        if (amount0Out > 0) {
            require(token0.transfer(to, amount0Out), "Token0 transfer failed");
        }
        if (amount1Out > 0) {
            require(token1.transfer(to, amount1Out), "Token1 transfer failed");
        }

        uint256 newBalance0 = token0.balanceOf(address(this));
        uint256 newBalance1 = token1.balanceOf(address(this));

        require(
            newBalance0 * newBalance1 >= reserve0 * reserve1,
            "K invariant violation"
        );

        reserve0 = newBalance0;
        reserve1 = newBalance1;

        emit Swap(msg.sender, amount0In, amount1In, amount0Out, amount1Out, to);
    }

    function getAmountOut(
        uint256 amountIn,
        uint256 reserveIn,
        uint256 reserveOut
    ) public pure returns (uint256 amountOut) {
        require(amountIn > 0, "Insufficient input amount");
        require(reserveIn > 0 && reserveOut > 0, "Insufficient liquidity");

        uint256 amountInWithFee = amountIn * 997;
        uint256 numerator = amountInWithFee * reserveOut;
        uint256 denominator = reserveIn * 1000 + amountInWithFee;

        amountOut = numerator / denominator;
    }

    function getAmountIn(
        uint256 amountOut,
        uint256 reserveIn,
        uint256 reserveOut
    ) public pure returns (uint256 amountIn) {
        require(amountOut > 0, "Insufficient output amount");
        require(reserveIn > 0 && reserveOut > 0, "Insufficient liquidity");
        require(amountOut < reserveOut, "Excessive output amount");

        uint256 numerator = reserveIn * amountOut * 1000;
        uint256 denominator = (reserveOut - amountOut) * 997;

        amountIn = (numerator / denominator) + 1;
    }

    function getReserves() external view returns (uint256 _reserve0, uint256 _reserve1) {
        _reserve0 = reserve0;
        _reserve1 = reserve1;
    }

    function sqrt(uint256 y) internal pure returns (uint256 z) {
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

    function price0CumulativeLast() external view returns (uint256) {
        return (reserve1 * 1e18) / reserve0;
    }

    function price1CumulativeLast() external view returns (uint256) {
        return (reserve0 * 1e18) / reserve1;
    }
}