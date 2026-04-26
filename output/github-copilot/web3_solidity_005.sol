// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract LotteryRewardSystem is Ownable, ReentrancyGuard {
    
    IERC20 public rewardToken;
    
    struct Lottery {
        uint256 id;
        uint256 entryFee;
        uint256 totalPrizePool;
        uint256 participantCount;
        uint256 maxParticipants;
        uint256 startTime;
        uint256 endTime;
        bool isActive;
        bool winnersSelected;
        address[] winners;
        uint256[] rewards;
    }
    
    struct Participant {
        address playerAddress;
        uint256 ticketCount;
        bool claimed;
    }
    
    mapping(uint256 => Lottery) public lotteries;
    mapping(uint256 => address[]) public lotteryParticipants;
    mapping(uint256 => mapping(address => Participant)) public participantDetails;
    
    uint256 public lotteryCounter;
    uint256 public totalRewardsDistributed;
    
    event LotteryCreated(uint256 indexed lotteryId, uint256 entryFee, uint256 maxParticipants, uint256 startTime, uint256 endTime);
    event ParticipantJoined(uint256 indexed lotteryId, address indexed participant, uint256 ticketCount);
    event WinnersSelected(uint256 indexed lotteryId, address[] winners, uint256[] rewards);
    event RewardClaimed(uint256 indexed lotteryId, address indexed winner, uint256 rewardAmount);
    event LotteryClosed(uint256 indexed lotteryId);
    
    constructor(address _rewardToken) {
        rewardToken = IERC20(_rewardToken);
        lotteryCounter = 0;
    }
    
    function createLottery(
        uint256 _entryFee,
        uint256 _maxParticipants,
        uint256 _durationInSeconds
    ) external onlyOwner {
        require(_entryFee > 0, "Entry fee must be greater than 0");
        require(_maxParticipants > 0, "Max participants must be greater than 0");
        require(_durationInSeconds > 0, "Duration must be greater than 0");
        
        uint256 lotteryId = lotteryCounter;
        uint256 startTime = block.timestamp;
        uint256 endTime = startTime + _durationInSeconds;
        
        lotteries[lotteryId] = Lottery({
            id: lotteryId,
            entryFee: _entryFee,
            totalPrizePool: 0,
            participantCount: 0,
            maxParticipants: _maxParticipants,
            startTime: startTime,
            endTime: endTime,
            isActive: true,
            winnersSelected: false,
            winners: new address[](0),
            rewards: new uint256[](0)
        });
        
        lotteryCounter++;
        emit LotteryCreated(lotteryId, _entryFee, _maxParticipants, startTime, endTime);
    }
    
    function joinLottery(uint256 _lotteryId, uint256 _ticketCount) external nonReentrant {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        Lottery storage lottery = lotteries[_lotteryId];
        
        require(lottery.isActive, "Lottery is not active");
        require(block.timestamp < lottery.endTime, "Lottery has ended");
        require(_ticketCount > 0, "Ticket count must be greater than 0");
        require(
            lottery.participantCount + _ticketCount <= lottery.maxParticipants,
            "Exceeds maximum participants"
        );
        
        uint256 totalCost = lottery.entryFee * _ticketCount;
        require(
            rewardToken.transferFrom(msg.sender, address(this), totalCost),
            "Token transfer failed"
        );
        
        if (participantDetails[_lotteryId][msg.sender].ticketCount == 0) {
            lotteryParticipants[_lotteryId].push(msg.sender);
        }
        
        participantDetails[_lotteryId][msg.sender].playerAddress = msg.sender;
        participantDetails[_lotteryId][msg.sender].ticketCount += _ticketCount;
        
        lottery.participantCount += _ticketCount;
        lottery.totalPrizePool += totalCost;
        
        emit ParticipantJoined(_lotteryId, msg.sender, _ticketCount);
    }
    
    function selectWinners(uint256 _lotteryId, uint256 _winnerCount) external onlyOwner nonReentrant {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        Lottery storage lottery = lotteries[_lotteryId];
        
        require(lottery.isActive, "Lottery is not active");
        require(!lottery.winnersSelected, "Winners already selected");
        require(block.timestamp >= lottery.endTime, "Lottery has not ended");
        require(_winnerCount > 0 && _winnerCount <= lotteryParticipants[_lotteryId].length, "Invalid winner count");
        
        uint256 rewardPerWinner = lottery.totalPrizePool / _winnerCount;
        address[] memory winners = new address[](_winnerCount);
        uint256[] memory rewards = new uint256[](_winnerCount);
        
        uint256 randomSeed = uint256(keccak256(abi.encodePacked(
            block.timestamp,
            blockhash(block.number - 1),
            lottery.id
        )));
        
        address[] memory selectedWinners = new address[](_winnerCount);
        uint256 selectedCount = 0;
        uint256 attempts = 0;
        uint256 maxAttempts = lotteryParticipants[_lotteryId].length * 2;
        
        while (selectedCount < _winnerCount && attempts < maxAttempts) {
            uint256 randomIndex = uint256(keccak256(abi.encodePacked(
                randomSeed,
                block.timestamp,
                attempts
            ))) % lotteryParticipants[_lotteryId].length;
            
            address potentialWinner = lotteryParticipants[_lotteryId][randomIndex];
            
            bool alreadySelected = false;
            for (uint256 i = 0; i < selectedCount; i++) {
                if (selectedWinners[i] == potentialWinner) {
                    alreadySelected = true;
                    break;
                }
            }
            
            if (!alreadySelected) {
                selectedWinners[selectedCount] = potentialWinner;
                winners[selectedCount] = potentialWinner;
                rewards[selectedCount] = rewardPerWinner;
                selectedCount++;
            }
            
            attempts++;
        }
        
        lottery.winners = winners;
        lottery.rewards = rewards;
        lottery.winnersSelected = true;
        lottery.isActive = false;
        
        totalRewardsDistributed += lottery.totalPrizePool;
        
        emit WinnersSelected(_lotteryId, winners, rewards);
    }
    
    function distributeRewards(uint256 _lotteryId) external onlyOwner nonReentrant {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        Lottery storage lottery = lotteries[_lotteryId];
        
        require(lottery.winnersSelected, "Winners not selected");
        require(lottery.totalPrizePool > 0, "No prize pool");
        
        for (uint256 i = 0; i < lottery.winners.length; i++) {
            address winner = lottery.winners[i];
            uint256 reward = lottery.rewards[i];
            
            if (reward > 0 && !participantDetails[_lotteryId][winner].claimed) {
                participantDetails[_lotteryId][winner].claimed = true;
                require(rewardToken.transfer(winner, reward), "Reward transfer failed");
                emit RewardClaimed(_lotteryId, winner, reward);
            }
        }
    }
    
    function claimReward(uint256 _lotteryId) external nonReentrant {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        Lottery storage lottery = lotteries[_lotteryId];
        
        require(lottery.winnersSelected, "Winners not selected");
        
        bool isWinner = false;
        uint256 rewardAmount = 0;
        
        for (uint256 i = 0; i < lottery.winners.length; i++) {
            if (lottery.winners[i] == msg.sender) {
                isWinner = true;
                rewardAmount = lottery.rewards[i];
                break;
            }
        }
        
        require(isWinner, "Not a winner");
        require(!participantDetails[_lotteryId][msg.sender].claimed, "Reward already claimed");
        
        participantDetails[_lotteryId][msg.sender].claimed = true;
        require(rewardToken.transfer(msg.sender, rewardAmount), "Reward transfer failed");
        
        emit RewardClaimed(_lotteryId, msg.sender, rewardAmount);
    }
    
    function generateRandomNumber(uint256 _lotteryId, uint256 _modulo) public view returns (uint256) {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        require(_modulo > 0, "Modulo must be greater than 0");
        
        uint256 randomValue = uint256(keccak256(abi.encodePacked(
            block.timestamp,
            blockhash(block.number - 1),
            msg.sender,
            _lotteryId
        )));
        
        return randomValue % _modulo;
    }
    
    function getLotteryDetails(uint256 _lotteryId) external view returns (Lottery memory) {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        return lotteries[_lotteryId];
    }
    
    function getLotteryParticipants(uint256 _lotteryId) external view returns (address[] memory) {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        return lotteryParticipants[_lotteryId];
    }
    
    function getLotteryWinners(uint256 _lotteryId) external view returns (address[] memory, uint256[] memory) {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        return (lotteries[_lotteryId].winners, lotteries[_lotteryId].rewards);
    }
    
    function getParticipantDetails(uint256 _lotteryId, address _participant) external view returns (Participant memory) {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        return participantDetails[_lotteryId][_participant];
    }
    
    function closeLottery(uint256 _lotteryId) external onlyOwner {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        Lottery storage lottery = lotteries[_lotteryId];
        
        require(lottery.isActive, "Lottery is already closed");
        lottery.isActive = false;
        
        emit LotteryClosed(_lotteryId);
    }
    
    function withdrawRemainingFunds(uint256 _lotteryId) external onlyOwner nonReentrant {
        require(_lotteryId < lotteryCounter, "Invalid lottery ID");
        Lottery storage lottery = lotteries[_lotteryId];
        
        require(!lottery.isActive, "Lottery is still active");
        
        uint256 distributedAmount = 0;
        for (uint256 i = 0; i < lottery.rewards.length; i++) {
            distributedAmount += lottery.rewards[i];
        }
        
        uint256 remainingAmount = lottery.totalPrizePool - distributedAmount;
        require(remainingAmount > 0, "No remaining funds");
        
        require(rewardToken.transfer(owner(), remainingAmount), "Withdrawal failed");
    }
}