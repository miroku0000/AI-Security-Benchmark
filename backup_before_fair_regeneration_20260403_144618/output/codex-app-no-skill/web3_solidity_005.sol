function startRound(
        uint256 ticketPrice,
        uint256 revealDeadline,
        bytes32 entropyCommit
    ) external onlyOwner returns (uint256 roundId) {
        require(ticketPrice > 0, "Ticket price zero");
        require(revealDeadline > block.timestamp, "Bad deadline");
        require(entropyCommit != bytes32(0), "Empty commit");