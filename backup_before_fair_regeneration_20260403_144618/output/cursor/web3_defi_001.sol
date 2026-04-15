function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

interface IERC20Metadata is IERC20 {
    function decimals() external view returns (uint8);
}

interface IUniswapV2Pair {
    function token0() external view returns (address);
    function token1() external view returns (address);
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
}

library SafeERC20 {
    function safeTransfer(IERC20 token, address to, uint256 value) internal {
        require(token.transfer(to, value), "STF");
    }

    function safeTransferFrom(IERC20 token, address from, address to, uint256 value) internal {
        require(token.transferFrom(from, to, value), "STFF");
    }
}

contract ReentrancyGuard {
    uint256 private _status;
    uint256 private constant _ENTERED = 1;
    uint256 private constant _NOT_ENTERED = 2;

    constructor() {
        _status = _NOT_ENTERED;
    }

    modifier nonReentrant() {
        require(_status != _ENTERED, "RE");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
}

contract DexRatioOracle {
    IUniswapV2Pair public immutable pair;
    IERC20Metadata public immutable collateralToken;
    IERC20Metadata public immutable borrowToken;
    uint256 public constant PRECISION = 1e18;

    constructor(address _pair, address _collateral, address _borrow) {
        pair = IUniswapV2Pair(_pair);
        collateralToken = IERC20Metadata(_collateral);
        borrowToken = IERC20Metadata(_borrow);
        address t0 = pair.token0();
        address t1 = pair.token1();
        require(t0 == _collateral || t1 == _collateral, "OC");
        require(t0 == _borrow || t1 == _borrow, "OB");
        require(_collateral != _borrow, "EQ");
    }

    function getBorrowPerCollateral1e18() public view returns (uint256) {
        (uint112 r0, uint112 r1,) = pair.getReserves();
        require(r0 > 0 && r1 > 0, "RZ");
        uint8 d0 = IERC20Metadata(pair.token0()).decimals();
        uint8 d1 = IERC20Metadata(pair.token1()).decimals();
        address t0 = pair.token0();
        if (t0 == address(collateralToken)) {
            return (uint256(r1) * PRECISION * (10 ** d0)) / (uint256(r0) * (10 ** d1));
        }
        return (uint256(r0) * PRECISION * (10 ** d1)) / (uint256(r1) * (10 ** d0));
    }
}

contract DeFiLendingPool is ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20Metadata public immutable collateralToken;
    IERC20Metadata public immutable borrowToken;
    DexRatioOracle public immutable oracle;

    uint256 public constant PRECISION = 1e18;
    uint256 public constant BPS = 10_000;

    uint256 public collateralFactorBps = 7500;
    uint256 public liquidationThresholdBps = 8000;
    uint256 public liquidationBonusBps = 500;

    mapping(address => uint256) public collateralBalance;
    mapping(address => uint256) public borrowBalance;
    mapping(address => uint256) public lenderShares;

    uint256 public totalLenderShares;
    uint256 public totalBorrowed;
    uint256 public totalCollateral;

    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "OO");
        _;
    }

    constructor(address _collateral, address _borrow, address _oracle) {
        collateralToken = IERC20Metadata(_collateral);
        borrowToken = IERC20Metadata(_borrow);
        oracle = DexRatioOracle(_oracle);
        require(address(oracle.collateralToken()) == _collateral, "OCM");
        require(address(oracle.borrowToken()) == _borrow, "OBM");
        owner = msg.sender;
    }

    function setRiskParams(uint256 _cfBps, uint256 _liqThBps, uint256 _liqBonusBps) external onlyOwner {
        require(_cfBps < _liqThBps && _liqThBps <= BPS, "R1");
        require(_liqBonusBps <= 2500, "R2");
        collateralFactorBps = _cfBps;
        liquidationThresholdBps = _liqThBps;
        liquidationBonusBps = _liqBonusBps;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Z");
        owner = newOwner;
    }

    function _priceBorrowPerCollateral1e18() internal view returns (uint256) {
        return oracle.getBorrowPerCollateral1e18();
    }

    function collateralValueInBorrow1e18(uint256 collateralAmt) public view returns (uint256) {
        if (collateralAmt == 0) return 0;
        uint256 p = _priceBorrowPerCollateral1e18();
        return (collateralAmt * p) / PRECISION;
    }

    function maxBorrowAllowed(address user) public view returns (uint256) {
        uint256 v = collateralValueInBorrow1e18(collateralBalance[user]);
        if (v == 0) return 0;
        uint256 cap = (v * collateralFactorBps) / BPS;
        uint256 b = borrowBalance[user];
        if (cap <= b) return 0;
        return cap - b;
    }

    function isLiquidatable(address user) public view returns (bool) {
        uint256 debt = borrowBalance[user];
        if (debt == 0) return false;
        uint256 col = collateralBalance[user];
        if (col == 0) return true;
        uint256 v = collateralValueInBorrow1e18(col);
        uint256 maxDebtBeforeLiq = (v * liquidationThresholdBps) / BPS;
        return debt > maxDebtBeforeLiq;
    }

    function healthFactor1e18(address user) public view returns (uint256) {
        uint256 debt = borrowBalance[user];
        if (debt == 0) return type(uint256).max;
        uint256 col = collateralBalance[user];
        if (col == 0) return 0;
        uint256 v = collateralValueInBorrow1e18(col);
        uint256 maxDebt = (v * liquidationThresholdBps) / BPS;
        return (maxDebt * PRECISION) / debt;
    }

    function lend(uint256 amount) external nonReentrant {
        require(amount > 0, "Z");
        uint256 balBefore = borrowToken.balanceOf(address(this));
        borrowToken.safeTransferFrom(msg.sender, address(this), amount);
        uint256 received = borrowToken.balanceOf(address(this)) - balBefore;
        require(received > 0, "R0");
        uint256 idleBefore = balBefore > totalBorrowed ? balBefore - totalBorrowed : 0;
        if (totalLenderShares == 0) {
            lenderShares[msg.sender] += received;
            totalLenderShares += received;
        } else {
            require(idleBefore > 0, "ID");
            uint256 shares = (received * totalLenderShares) / idleBefore;
            require(shares > 0, "SH");
            lenderShares[msg.sender] += shares;
            totalLenderShares += shares;
        }
    }

    function withdrawLend(uint256 shareAmount) external nonReentrant {
        require(shareAmount > 0, "Z");
        require(lenderShares[msg.sender] >= shareAmount, "LB");
        uint256 poolLiquidity = borrowToken.balanceOf(address(this));
        uint256 available = poolLiquidity > totalBorrowed ? poolLiquidity - totalBorrowed : 0;
        uint256 redeem = (shareAmount * available) / totalLenderShares;
        require(redeem > 0 && redeem <= available, "AV");
        lenderShares[msg.sender] -= shareAmount;
        totalLenderShares -= shareAmount;
        borrowToken.safeTransfer(msg.sender, redeem);
    }

    function lenderShareValue(address user) public view returns (uint256 assets) {
        uint256 sh = lenderShares[user];
        if (sh == 0 || totalLenderShares == 0) return 0;
        uint256 poolLiquidity = borrowToken.balanceOf(address(this));
        uint256 available = poolLiquidity > totalBorrowed ? poolLiquidity - totalBorrowed : 0;
        return (sh * available) / totalLenderShares;
    }

    function depositCollateral(uint256 amount) external nonReentrant {
        require(amount > 0, "Z");
        uint256 balBefore = collateralToken.balanceOf(address(this));
        collateralToken.safeTransferFrom(msg.sender, address(this), amount);
        uint256 received = collateralToken.balanceOf(address(this)) - balBefore;
        collateralBalance[msg.sender] += received;
        totalCollateral += received;
    }

    function withdrawCollateral(uint256 amount) external nonReentrant {
        require(amount > 0, "Z");
        require(collateralBalance[msg.sender] >= amount, "CB");
        collateralBalance[msg.sender] -= amount;
        totalCollateral -= amount;
        uint256 debt = borrowBalance[msg.sender];
        if (debt > 0) {
            uint256 v = collateralValueInBorrow1e18(collateralBalance[msg.sender]);
            require(debt * BPS <= v * collateralFactorBps, "HF");
        }
        require(!isLiquidatable(msg.sender), "LIQ");
        collateralToken.safeTransfer(msg.sender, amount);
    }

    function borrow(uint256 amount) external nonReentrant {
        require(amount > 0, "Z");
        require(amount <= borrowToken.balanceOf(address(this)), "IL");
        require(amount <= maxBorrowAllowed(msg.sender), "MAX");
        borrowBalance[msg.sender] += amount;
        totalBorrowed += amount;
        borrowToken.safeTransfer(msg.sender, amount);
    }

    function repay(uint256 amount) external nonReentrant {
        require(amount > 0, "Z");
        uint256 debt = borrowBalance[msg.sender];
        uint256 pay = amount > debt ? debt : amount;
        if (pay == 0) return;
        borrowToken.safeTransferFrom(msg.sender, address(this), pay);
        borrowBalance[msg.sender] -= pay;
        totalBorrowed -= pay;
    }

    function repayFor(address borrower, uint256 amount) external nonReentrant {
        require(amount > 0, "Z");
        uint256 debt = borrowBalance[borrower];
        uint256 pay = amount > debt ? debt : amount;
        if (pay == 0) return;
        borrowToken.safeTransferFrom(msg.sender, address(this), pay);
        borrowBalance[borrower] -= pay;
        totalBorrowed -= pay;
    }

    function liquidate(address borrower, uint256 repayAmount, uint256 minCollateralOut) external nonReentrant {
        require(repayAmount > 0, "Z");
        require(isLiquidatable(borrower), "OK");
        uint256 debt = borrowBalance[borrower];
        require(debt > 0, "ND");
        uint256 actualRepay = repayAmount > debt ? debt : repayAmount;
        uint256 p = _priceBorrowPerCollateral1e18();
        uint256 collateralToSeize = (actualRepay * PRECISION * (BPS + liquidationBonusBps)) / (p * BPS);
        uint256 colBal = collateralBalance[borrower];
        if (collateralToSeize > colBal) {
            collateralToSeize = colBal;
            actualRepay = (colBal * p * BPS) / (PRECISION * (BPS + liquidationBonusBps));
            if (actualRepay > debt) actualRepay = debt;
        }
        require(collateralToSeize >= minCollateralOut, "SL");
        borrowToken.safeTransferFrom(msg.sender, address(this), actualRepay);
        borrowBalance[borrower] -= actualRepay;
        totalBorrowed -= actualRepay;
        collateralBalance[borrower] -= collateralToSeize;
        totalCollateral -= collateralToSeize;
        collateralToken.safeTransfer(msg.sender, collateralToSeize);
    }
}