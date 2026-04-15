// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title GameLottery
 * @notice A lottery and randomized reward system for a blockchain gaming platform.
 * @dev WARNING: This contract uses block.timestamp and blockhash for randomness,
 *      which are manipulable by miners/validators. For production use, integrate
 *      Chainlink VRF or another verifiable randomness oracle. On-chain randomness
 *      derived from block data is NOT secure against motivated adversaries.
 */
contract GameLottery is Ownable, ReentrancyGuard {
    enum LotteryState { OPEN, CLOSED, CALCULATING_WINNER }

    struct Lottery {
        uint256 id;
        uint256 ticketPrice;
        uint256 prizePool;
        uint256 startTime;
        uint256 endTime;
        address[] players;
        address winner;
        LotteryState state;
        uint256 commitBlock;
    }

    uint256 public currentLotteryId;
    mapping(uint256 => Lottery) public lotteries;
    mapping(uint256 => mapping(address => uint256)) public playerTicketCount;

    uint256 public platformFeePercent = 5; // 5% fee
    uint256 public accumulatedFees;

    uint256 public constant MAX_TICKETS_PER_PLAYER = 10;
    uint256 public constant MIN_PLAYERS = 2;
    uint256 public constant REVEAL_DELAY = 1; // blocks to wait after commit

    event LotteryCreated(uint256 indexed lotteryId, uint256 ticketPrice, uint256 endTime);
    event TicketPurchased(uint256 indexed lotteryId, address indexed player, uint256 ticketCount);
    event WinnerSelectionCommitted(uint256 indexed lotteryId, uint256 commitBlock);
    event WinnerSelected(uint256 indexed lotteryId, address indexed winner, uint256 prize);
    event FeesWithdrawn(address indexed owner, uint256 amount);

    constructor() Ownable(msg.sender) {}

    /**
     * @notice Creates a new lottery round.
     * @param _ticketPrice Price per ticket in wei.
     * @param _duration Duration in seconds.
     */
    function createLottery(uint256 _ticketPrice, uint256 _duration) external onlyOwner {
        require(_ticketPrice > 0, "Ticket price must be > 0");
        require(_duration > 0, "Duration must be > 0");

        currentLotteryId++;
        Lottery storage lottery = lotteries[currentLotteryId];
        lottery.id = currentLotteryId;
        lottery.ticketPrice = _ticketPrice;
        lottery.startTime = block.timestamp;
        lottery.endTime = block.timestamp + _duration;
        lottery.state = LotteryState.OPEN;

        emit LotteryCreated(currentLotteryId, _ticketPrice, lottery.endTime);
    }

    /**
     * @notice Purchase tickets for the current lottery.
     * @param _lotteryId The lottery to enter.
     * @param _ticketCount Number of tickets to buy.
     */
    function buyTickets(uint256 _lotteryId, uint256 _ticketCount) external payable nonReentrant {
        Lottery storage lottery = lotteries[_lotteryId];
        require(lottery.state == LotteryState.OPEN, "Lottery not open");
        require(block.timestamp < lottery.endTime, "Lottery ended");
        require(_ticketCount > 0, "Must buy at least 1 ticket");
        require(
            playerTicketCount[_lotteryId][msg.sender] + _ticketCount <= MAX_TICKETS_PER_PLAYER,
            "Exceeds max tickets per player"
        );
        require(msg.value == lottery.ticketPrice * _ticketCount, "Incorrect ETH amount");

        playerTicketCount[_lotteryId][msg.sender] += _ticketCount;
        for (uint256 i = 0; i < _ticketCount; i++) {
            lottery.players.push(msg.sender);
        }
        lottery.prizePool += msg.value;

        emit TicketPurchased(_lotteryId, msg.sender, _ticketCount);
    }

    /**
     * @notice Commit phase: close the lottery and record the block number.
     *         The winner will be determined using the blockhash of a future block
     *         to reduce miner manipulation (commit-reveal pattern).
     * @param _lotteryId The lottery to close.
     */
    function commitWinnerSelection(uint256 _lotteryId) external onlyOwner {
        Lottery storage lottery = lotteries[_lotteryId];
        require(lottery.state == LotteryState.OPEN, "Lottery not open");
        require(block.timestamp >= lottery.endTime, "Lottery not ended yet");
        require(lottery.players.length >= MIN_PLAYERS, "Not enough players");

        lottery.state = LotteryState.CALCULATING_WINNER;
        lottery.commitBlock = block.number;

        emit WinnerSelectionCommitted(_lotteryId, block.number);
    }

    /**
     * @notice Reveal phase: select the winner using the blockhash of the committed
     *         future block. Must be called within 256 blocks of the commit.
     * @dev blockhash() only works for the most recent 256 blocks. If this window
     *      is missed, the owner must call resetCommit() and recommit.
     * @param _lotteryId The lottery to finalize.
     */
    function revealWinner(uint256 _lotteryId) external onlyOwner nonReentrant {
        Lottery storage lottery = lotteries[_lotteryId];
        require(lottery.state == LotteryState.CALCULATING_WINNER, "Not in calculating state");
        require(lottery.commitBlock > 0, "No commit recorded");

        uint256 revealBlock = lottery.commitBlock + REVEAL_DELAY;
        require(block.number > revealBlock, "Too early to reveal");
        require(block.number <= revealBlock + 256, "Blockhash expired, must recommit");

        bytes32 blockHash = blockhash(revealBlock);
        require(blockHash != bytes32(0), "Blockhash unavailable");

        // Generate pseudo-random index from future blockhash + lottery-specific entropy
        uint256 randomIndex = uint256(
            keccak256(abi.encodePacked(blockHash, _lotteryId, lottery.prizePool))
        ) % lottery.players.length;

        address winner = lottery.players[randomIndex];
        lottery.winner = winner;
        lottery.state = LotteryState.CLOSED;

        uint256 fee = (lottery.prizePool * platformFeePercent) / 100;
        uint256 prize = lottery.prizePool - fee;
        accumulatedFees += fee;

        (bool sent, ) = winner.call{value: prize}("");
        require(sent, "Prize transfer failed");

        emit WinnerSelected(_lotteryId, winner, prize);
    }

    /**
     * @notice Reset the commit if the 256-block window was missed.
     * @param _lotteryId The lottery to reset.
     */
    function resetCommit(uint256 _lotteryId) external onlyOwner {
        Lottery storage lottery = lotteries[_lotteryId];
        require(lottery.state == LotteryState.CALCULATING_WINNER, "Not in calculating state");
        require(
            block.number > lottery.commitBlock + REVEAL_DELAY + 256,
            "Reveal window still open"
        );

        lottery.commitBlock = block.number;

        emit WinnerSelectionCommitted(_lotteryId, block.number);
    }

    /**
     * @notice Refund all players if lottery didn't meet minimum participants.
     * @param _lotteryId The lottery to cancel.
     */
    function cancelAndRefund(uint256 _lotteryId) external onlyOwner nonReentrant {
        Lottery storage lottery = lotteries[_lotteryId];
        require(
            lottery.state == LotteryState.OPEN || lottery.state == LotteryState.CALCULATING_WINNER,
            "Lottery already closed"
        );
        require(block.timestamp >= lottery.endTime, "Lottery not ended yet");

        lottery.state = LotteryState.CLOSED;

        // Refund each unique player proportionally to their tickets
        address[] memory players = lottery.players;
        uint256 ticketPrice = lottery.ticketPrice;

        // Track refunded addresses to avoid double refund
        mapping(address => bool) storage refunded = playerTicketCount[_lotteryId];
        // Re-use the mapping: we'll iterate and clear

        for (uint256 i = 0; i < players.length; i++) {
            address player = players[i];
            uint256 tickets = playerTicketCount[_lotteryId][player];
            if (tickets > 0) {
                playerTicketCount[_lotteryId][player] = 0;
                uint256 refundAmount = tickets * ticketPrice;
                (bool sent, ) = player.call{value: refundAmount}("");
                require(sent, "Refund failed");
            }
        }
    }

    /**
     * @notice Withdraw accumulated platform fees.
     */
    function withdrawFees() external onlyOwner nonReentrant {
        uint256 amount = accumulatedFees;
        require(amount > 0, "No fees to withdraw");
        accumulatedFees = 0;

        (bool sent, ) = owner().call{value: amount}("");
        require(sent, "Fee withdrawal failed");

        emit FeesWithdrawn(owner(), amount);
    }

    /**
     * @notice Update the platform fee percentage.
     * @param _newFeePercent New fee percentage (max 10%).
     */
    function setFeePercent(uint256 _newFeePercent) external onlyOwner {
        require(_newFeePercent <= 10, "Fee too high");
        platformFeePercent = _newFeePercent;
    }

    // --- View functions ---

    function getPlayers(uint256 _lotteryId) external view returns (address[] memory) {
        return lotteries[_lotteryId].players;
    }

    function getPlayerCount(uint256 _lotteryId) external view returns (uint256) {
        return lotteries[_lotteryId].players.length;
    }

    function getLotteryState(uint256 _lotteryId) external view returns (LotteryState) {
        return lotteries[_lotteryId].state;
    }

    receive() external payable {}
}