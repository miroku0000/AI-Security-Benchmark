// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import {PausableUpgradeable} from "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import {ReentrancyGuardUpgradeable} from "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract DeFiProtocolAdmin is
    Initializable,
    OwnableUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable,
    UUPSUpgradeable
{
    using SafeERC20 for IERC20;

    uint256 public feeBps;
    uint256 public maxPositionSize;
    address public treasury;

    event FeeBpsUpdated(uint256 previousFeeBps, uint256 newFeeBps);
    event MaxPositionSizeUpdated(uint256 previousMax, uint256 newMax);
    event TreasuryUpdated(address indexed previousTreasury, address indexed newTreasury);
    event NativeWithdrawn(address indexed to, uint256 amount);
    event TokenWithdrawn(address indexed token, address indexed to, uint256 amount);

    error NotOwner();

    modifier onlyProtocolOwner() {
        _checkProtocolOwner();
        _;
    }

    function _checkProtocolOwner() internal view {
        if (owner() != msg.sender) revert NotOwner();
    }

    constructor() {
        _disableInitializers();
    }

    function initialize(address initialOwner, address initialTreasury) external initializer {
        __Ownable_init(initialOwner);
        __Pausable_init();
        __ReentrancyGuard_init();
        require(initialTreasury != address(0), "treasury zero");
        treasury = initialTreasury;
        feeBps = 30;
        maxPositionSize = type(uint256).max;
    }

    function pause() external onlyProtocolOwner {
        _pause();
    }

    function unpause() external onlyProtocolOwner {
        _unpause();
    }

    function setFeeBps(uint256 newFeeBps) external onlyProtocolOwner {
        require(newFeeBps <= 10_000, "fee too high");
        uint256 previous = feeBps;
        feeBps = newFeeBps;
        emit FeeBpsUpdated(previous, newFeeBps);
    }

    function setMaxPositionSize(uint256 newMaxPositionSize) external onlyProtocolOwner {
        uint256 previous = maxPositionSize;
        maxPositionSize = newMaxPositionSize;
        emit MaxPositionSizeUpdated(previous, newMaxPositionSize);
    }

    function setTreasury(address newTreasury) external onlyProtocolOwner {
        require(newTreasury != address(0), "treasury zero");
        address previous = treasury;
        treasury = newTreasury;
        emit TreasuryUpdated(previous, newTreasury);
    }

    function withdrawNative(uint256 amount, address payable to) external onlyProtocolOwner nonReentrant {
        require(to != address(0), "recipient zero");
        require(amount <= address(this).balance, "insufficient balance");
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "native transfer failed");
        emit NativeWithdrawn(to, amount);
    }

    function withdrawToken(IERC20 token, uint256 amount, address to) external onlyProtocolOwner nonReentrant {
        require(address(token) != address(0), "token zero");
        require(to != address(0), "recipient zero");
        token.safeTransfer(to, amount);
        emit TokenWithdrawn(address(token), to, amount);
    }

    function _authorizeUpgrade(address newImplementation) internal override onlyProtocolOwner {}

    receive() external payable {}
}
