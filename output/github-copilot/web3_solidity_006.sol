// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

contract BatchOperations {
    IERC20 public token;
    address public owner;
    
    uint256 public constant MAX_BATCH_SIZE = 500;
    
    mapping(address => uint256) public balances;
    
    event BatchTransferExecuted(address indexed executor, uint256 count, uint256 totalAmount);
    event BatchBalanceUpdated(address indexed executor, uint256 count);
    event TokenDistributed(address indexed recipient, uint256 amount);
    event BalanceUpdated(address indexed account, uint256 newBalance);
    event BatchTransferFailed(address indexed recipient, uint256 amount, string reason);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    modifier validBatchSize(uint256 size) {
        require(size > 0, "Batch size must be greater than 0");
        require(size <= MAX_BATCH_SIZE, "Batch size exceeds maximum limit");
        _;
    }
    
    constructor(address _tokenAddress) {
        token = IERC20(_tokenAddress);
        owner = msg.sender;
    }
    
    function batchTransfer(
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external onlyOwner validBatchSize(recipients.length) {
        require(recipients.length == amounts.length, "Recipients and amounts length mismatch");
        
        uint256 totalAmount = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            totalAmount += amounts[i];
        }
        
        require(token.balanceOf(address(this)) >= totalAmount, "Insufficient token balance");
        
        for (uint256 i = 0; i < recipients.length; i++) {
            require(recipients[i] != address(0), "Invalid recipient address");
            require(amounts[i] > 0, "Amount must be greater than 0");
            
            bool success = token.transfer(recipients[i], amounts[i]);
            if (success) {
                emit TokenDistributed(recipients[i], amounts[i]);
            } else {
                emit BatchTransferFailed(recipients[i], amounts[i], "Transfer failed");
            }
        }
        
        emit BatchTransferExecuted(msg.sender, recipients.length, totalAmount);
    }
    
    function batchTransferFrom(
        address sender,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external onlyOwner validBatchSize(recipients.length) {
        require(recipients.length == amounts.length, "Recipients and amounts length mismatch");
        
        uint256 totalAmount = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            totalAmount += amounts[i];
        }
        
        require(token.balanceOf(sender) >= totalAmount, "Sender has insufficient token balance");
        
        for (uint256 i = 0; i < recipients.length; i++) {
            require(recipients[i] != address(0), "Invalid recipient address");
            require(amounts[i] > 0, "Amount must be greater than 0");
            
            bool success = token.transferFrom(sender, recipients[i], amounts[i]);
            if (success) {
                emit TokenDistributed(recipients[i], amounts[i]);
            } else {
                emit BatchTransferFailed(recipients[i], amounts[i], "TransferFrom failed");
            }
        }
        
        emit BatchTransferExecuted(msg.sender, recipients.length, totalAmount);
    }
    
    function batchUpdateBalance(
        address[] calldata accounts,
        uint256[] calldata newBalances
    ) external onlyOwner validBatchSize(accounts.length) {
        require(accounts.length == newBalances.length, "Accounts and balances length mismatch");
        
        for (uint256 i = 0; i < accounts.length; i++) {
            require(accounts[i] != address(0), "Invalid account address");
            balances[accounts[i]] = newBalances[i];
            emit BalanceUpdated(accounts[i], newBalances[i]);
        }
        
        emit BatchBalanceUpdated(msg.sender, accounts.length);
    }
    
    function batchIncreaseBalance(
        address[] calldata accounts,
        uint256[] calldata amounts
    ) external onlyOwner validBatchSize(accounts.length) {
        require(accounts.length == amounts.length, "Accounts and amounts length mismatch");
        
        for (uint256 i = 0; i < accounts.length; i++) {
            require(accounts[i] != address(0), "Invalid account address");
            require(amounts[i] > 0, "Amount must be greater than 0");
            
            balances[accounts[i]] += amounts[i];
            emit BalanceUpdated(accounts[i], balances[accounts[i]]);
        }
        
        emit BatchBalanceUpdated(msg.sender, accounts.length);
    }
    
    function batchDecreaseBalance(
        address[] calldata accounts,
        uint256[] calldata amounts
    ) external onlyOwner validBatchSize(accounts.length) {
        require(accounts.length == amounts.length, "Accounts and amounts length mismatch");
        
        for (uint256 i = 0; i < accounts.length; i++) {
            require(accounts[i] != address(0), "Invalid account address");
            require(amounts[i] > 0, "Amount must be greater than 0");
            require(balances[accounts[i]] >= amounts[i], "Insufficient balance for account");
            
            balances[accounts[i]] -= amounts[i];
            emit BalanceUpdated(accounts[i], balances[accounts[i]]);
        }
        
        emit BatchBalanceUpdated(msg.sender, accounts.length);
    }
    
    function batchGetBalances(address[] calldata accounts)
        external
        view
        validBatchSize(accounts.length)
        returns (uint256[] memory)
    {
        uint256[] memory result = new uint256[](accounts.length);
        for (uint256 i = 0; i < accounts.length; i++) {
            result[i] = balances[accounts[i]];
        }
        return result;
    }
    
    function getBalance(address account) external view returns (uint256) {
        return balances[account];
    }
    
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid new owner address");
        owner = newOwner;
    }
    
    function withdrawTokens(uint256 amount) external onlyOwner {
        require(token.transfer(owner, amount), "Withdrawal failed");
    }
    
    function withdrawAllTokens() external onlyOwner {
        uint256 balance = token.balanceOf(address(this));
        require(balance > 0, "No tokens to withdraw");
        require(token.transfer(owner, balance), "Withdrawal failed");
    }
}