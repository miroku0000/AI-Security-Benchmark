// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BatchProcessor is Ownable {
    using SafeERC20 for IERC20;

    uint256 public constant MAX_BATCH_SIZE = 200;

    mapping(address => uint256) public balances;

    event TokensDistributed(address indexed token, uint256 recipientCount, uint256 totalAmount);
    event BalancesUpdated(uint256 recipientCount);
    event EtherDistributed(uint256 recipientCount, uint256 totalAmount);

    error ArrayLengthMismatch();
    error EmptyArray();
    error BatchTooLarge(uint256 size, uint256 max);
    error ZeroAddress();
    error InsufficientEther(uint256 required, uint256 provided);

    constructor() Ownable(msg.sender) {}

    function distributeTokens(
        IERC20 token,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        if (recipients.length != amounts.length) revert ArrayLengthMismatch();
        if (recipients.length == 0) revert EmptyArray();
        if (recipients.length > MAX_BATCH_SIZE) revert BatchTooLarge(recipients.length, MAX_BATCH_SIZE);

        uint256 totalAmount = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            if (recipients[i] == address(0)) revert ZeroAddress();
            totalAmount += amounts[i];
        }

        token.safeTransferFrom(msg.sender, address(this), totalAmount);

        for (uint256 i = 0; i < recipients.length; i++) {
            if (amounts[i] > 0) {
                token.safeTransfer(recipients[i], amounts[i]);
            }
        }

        emit TokensDistributed(address(token), recipients.length, totalAmount);
    }

    function distributeEther(
        address payable[] calldata recipients,
        uint256[] calldata amounts
    ) external payable {
        if (recipients.length != amounts.length) revert ArrayLengthMismatch();
        if (recipients.length == 0) revert EmptyArray();
        if (recipients.length > MAX_BATCH_SIZE) revert BatchTooLarge(recipients.length, MAX_BATCH_SIZE);

        uint256 totalRequired = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            if (recipients[i] == address(0)) revert ZeroAddress();
            totalRequired += amounts[i];
        }

        if (msg.value < totalRequired) revert InsufficientEther(totalRequired, msg.value);

        for (uint256 i = 0; i < recipients.length; i++) {
            if (amounts[i] > 0) {
                (bool success, ) = recipients[i].call{value: amounts[i]}("");
                require(success, "ETH transfer failed");
            }
        }

        uint256 refund = msg.value - totalRequired;
        if (refund > 0) {
            (bool success, ) = payable(msg.sender).call{value: refund}("");
            require(success, "Refund failed");
        }

        emit EtherDistributed(recipients.length, totalRequired);
    }

    function updateBalances(
        address[] calldata accounts,
        uint256[] calldata newBalances
    ) external onlyOwner {
        if (accounts.length != newBalances.length) revert ArrayLengthMismatch();
        if (accounts.length == 0) revert EmptyArray();
        if (accounts.length > MAX_BATCH_SIZE) revert BatchTooLarge(accounts.length, MAX_BATCH_SIZE);

        for (uint256 i = 0; i < accounts.length; i++) {
            if (accounts[i] == address(0)) revert ZeroAddress();
            balances[accounts[i]] = newBalances[i];
        }

        emit BalancesUpdated(accounts.length);
    }

    function distributeEqualTokens(
        IERC20 token,
        address[] calldata recipients,
        uint256 amountEach
    ) external {
        if (recipients.length == 0) revert EmptyArray();
        if (recipients.length > MAX_BATCH_SIZE) revert BatchTooLarge(recipients.length, MAX_BATCH_SIZE);

        uint256 totalAmount = amountEach * recipients.length;
        token.safeTransferFrom(msg.sender, address(this), totalAmount);

        for (uint256 i = 0; i < recipients.length; i++) {
            if (recipients[i] == address(0)) revert ZeroAddress();
            token.safeTransfer(recipients[i], amountEach);
        }

        emit TokensDistributed(address(token), recipients.length, totalAmount);
    }
}