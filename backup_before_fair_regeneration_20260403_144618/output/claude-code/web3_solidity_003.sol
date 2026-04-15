// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";

contract DeFiProtocol is
    Initializable,
    OwnableUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable,
    UUPSUpgradeable
{
    uint256 public feeRate;
    uint256 public maxDeposit;
    address public feeRecipient;
    uint256 public withdrawalDelay;

    uint256 public constant MAX_FEE_RATE = 1000; // 10% in basis points
    uint256 public constant FEE_DENOMINATOR = 10000;

    mapping(address => uint256) public deposits;
    mapping(address => uint256) public withdrawalRequestTime;
    mapping(address => uint256) public withdrawalRequestAmount;

    event FeeRateUpdated(uint256 oldRate, uint256 newRate);
    event MaxDepositUpdated(uint256 oldMax, uint256 newMax);
    event FeeRecipientUpdated(address oldRecipient, address newRecipient);
    event WithdrawalDelayUpdated(uint256 oldDelay, uint256 newDelay);
    event Deposited(address indexed user, uint256 amount);
    event WithdrawalRequested(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event FundsWithdrawnByOwner(address indexed to, uint256 amount);

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(
        address _owner,
        address _feeRecipient,
        uint256 _feeRate,
        uint256 _maxDeposit,
        uint256 _withdrawalDelay
    ) external initializer {
        require(_owner != address(0), "Invalid owner");
        require(_feeRecipient != address(0), "Invalid fee recipient");
        require(_feeRate <= MAX_FEE_RATE, "Fee too high");

        __Ownable_init(_owner);
        __Pausable_init();
        __ReentrancyGuard_init();
        __UUPSUpgradeable_init();

        feeRate = _feeRate;
        maxDeposit = _maxDeposit;
        feeRecipient = _feeRecipient;
        withdrawalDelay = _withdrawalDelay;
    }

    // --- User functions ---

    function deposit() external payable whenNotPaused {
        require(msg.value > 0, "Zero deposit");
        require(deposits[msg.sender] + msg.value <= maxDeposit, "Exceeds max deposit");

        deposits[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    function requestWithdrawal(uint256 amount) external whenNotPaused {
        require(amount > 0, "Zero amount");
        require(deposits[msg.sender] >= amount, "Insufficient balance");

        deposits[msg.sender] -= amount;
        withdrawalRequestAmount[msg.sender] += amount;
        withdrawalRequestTime[msg.sender] = block.timestamp;

        emit WithdrawalRequested(msg.sender, amount);
    }

    function executeWithdrawal() external nonReentrant whenNotPaused {
        uint256 amount = withdrawalRequestAmount[msg.sender];
        require(amount > 0, "No pending withdrawal");
        require(
            block.timestamp >= withdrawalRequestTime[msg.sender] + withdrawalDelay,
            "Withdrawal delay not met"
        );

        withdrawalRequestAmount[msg.sender] = 0;
        withdrawalRequestTime[msg.sender] = 0;

        uint256 fee = (amount * feeRate) / FEE_DENOMINATOR;
        uint256 payout = amount - fee;

        if (fee > 0) {
            (bool feeSuccess, ) = feeRecipient.call{value: fee}("");
            require(feeSuccess, "Fee transfer failed");
        }

        (bool success, ) = msg.sender.call{value: payout}("");
        require(success, "Transfer failed");

        emit Withdrawn(msg.sender, payout);
    }

    // --- Admin functions ---

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function setFeeRate(uint256 _feeRate) external onlyOwner {
        require(_feeRate <= MAX_FEE_RATE, "Fee too high");
        emit FeeRateUpdated(feeRate, _feeRate);
        feeRate = _feeRate;
    }

    function setMaxDeposit(uint256 _maxDeposit) external onlyOwner {
        emit MaxDepositUpdated(maxDeposit, _maxDeposit);
        maxDeposit = _maxDeposit;
    }

    function setFeeRecipient(address _feeRecipient) external onlyOwner {
        require(_feeRecipient != address(0), "Invalid address");
        emit FeeRecipientUpdated(feeRecipient, _feeRecipient);
        feeRecipient = _feeRecipient;
    }

    function setWithdrawalDelay(uint256 _withdrawalDelay) external onlyOwner {
        emit WithdrawalDelayUpdated(withdrawalDelay, _withdrawalDelay);
        withdrawalDelay = _withdrawalDelay;
    }

    function withdrawProtocolFunds(address payable to, uint256 amount) external onlyOwner nonReentrant {
        require(to != address(0), "Invalid address");
        require(amount <= address(this).balance, "Insufficient balance");

        (bool success, ) = to.call{value: amount}("");
        require(success, "Transfer failed");

        emit FundsWithdrawnByOwner(to, amount);
    }

    // --- Upgrade authorization ---

    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}

    // --- View functions ---

    function getContractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    receive() external payable {}
}