function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract BatchAirdropPayments {
    address public owner;

    mapping(address => uint256) public creditBalance;

    bool private _entered;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event BatchTokenFromSender(address indexed token, address indexed payer, uint256 count, uint256 total);
    event BatchTokenFromContract(address indexed token, uint256 count, uint256 total);
    event BatchEther(address indexed payer, uint256 count, uint256 total);
    event CreditsBatchUpdated(uint256 count);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier nonReentrant() {
        require(!_entered, "reentrancy");
        _entered = true;
        _;
        _entered = false;
    }

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function batchTransferTokenFromSender(
        IERC20 token,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external nonReentrant {
        uint256 n = recipients.length;
        require(n == amounts.length, "len");
        uint256 total;
        for (uint256 i; i < n; ) {
            uint256 a = amounts[i];
            total += a;
            require(token.transferFrom(msg.sender, recipients[i], a), "tf");
            unchecked {
                ++i;
            }
        }
        emit BatchTokenFromSender(address(token), msg.sender, n, total);
    }

    function batchTransferTokenFromContract(
        IERC20 token,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external onlyOwner nonReentrant {
        uint256 n = recipients.length;
        require(n == amounts.length, "len");
        uint256 total;
        for (uint256 i; i < n; ) {
            total += amounts[i];
            unchecked {
                ++i;
            }
        }
        require(token.balanceOf(address(this)) >= total, "bal");
        for (uint256 i; i < n; ) {
            require(token.transfer(recipients[i], amounts[i]), "tr");
            unchecked {
                ++i;
            }
        }
        emit BatchTokenFromContract(address(token), n, total);
    }

    function batchSendEther(
        address payable[] calldata recipients,
        uint256[] calldata amounts
    ) external payable nonReentrant {
        uint256 n = recipients.length;
        require(n == amounts.length, "len");
        uint256 total;
        for (uint256 i; i < n; ) {
            total += amounts[i];
            unchecked {
                ++i;
            }
        }
        require(msg.value == total, "val");
        for (uint256 i; i < n; ) {
            (bool ok, ) = recipients[i].call{value: amounts[i]}("");
            require(ok, "eth");
            unchecked {
                ++i;
            }
        }
        emit BatchEther(msg.sender, n, total);
    }

    function batchUpdateCredits(
        address[] calldata accounts,
        uint256[] calldata newBalances
    ) external onlyOwner {
        uint256 n = accounts.length;
        require(n == newBalances.length, "len");
        for (uint256 i; i < n; ) {
            creditBalance[accounts[i]] = newBalances[i];
            unchecked {
                ++i;
            }
        }
        emit CreditsBatchUpdated(n);
    }

    function withdrawEther(address payable to, uint256 amount) external onlyOwner nonReentrant {
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "eth");
    }

    function withdrawToken(IERC20 token, address to, uint256 amount) external onlyOwner nonReentrant {
        require(token.transfer(to, amount), "tr");
    }

    receive() external payable {}
}