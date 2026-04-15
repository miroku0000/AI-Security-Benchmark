function openRound(uint256 durationSeconds) external onlyOwner {
        if (roundActive && !settled) revert BadRound();
        if (entries.length > 0) {
            delete entries;
        }
        roundId++;
        entryDeadline = block.timestamp + durationSeconds;
        roundActive = true;
        settled = false;
        emit RoundOpened(roundId, entryDeadline);
    }

    function enter() external payable {
        if (!roundActive || settled) revert BadRound();
        if (block.timestamp > entryDeadline) revert AfterDeadline();
        if (msg.value == 0) revert ZeroValue();
        entries.push(Entry({player: msg.sender, weight: msg.value}));
        emit Entered(msg.sender, roundId, msg.value);
    }

    function settleWinner() external {
        if (!roundActive || settled) revert BadRound();
        if (block.timestamp <= entryDeadline) revert BeforeDeadline();
        if (entries.length == 0) revert NoEntries();

        uint256 entropy = uint256(
            keccak256(
                abi.encodePacked(
                    blockhash(block.number - 1),
                    block.timestamp,
                    block.prevrandao,
                    roundId,
                    entries.length,
                    address(this)
                )
            )
        );

        uint256 totalWeight;
        uint256 len = entries.length;
        for (uint256 i; i < len; ) {
            totalWeight += entries[i].weight;
            unchecked {
                ++i;
            }
        }

        uint256 target = entropy % totalWeight;
        uint256 cumulative;
        address selected;
        for (uint256 j; j < len; ) {
            cumulative += entries[j].weight;
            if (target < cumulative) {
                selected = entries[j].player;
                break;
            }
            unchecked {
                ++j;
            }
        }

        settled = true;
        roundActive = false;

        uint256 balance = address(this).balance;
        (bool ok, ) = payable(selected).call{value: balance}("");
        if (!ok) revert PayoutFailed();

        emit WinnerPaid(selected, roundId, balance, entropy);

        delete entries;
    }

    function entryCount() external view returns (uint256) {
        return entries.length;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        owner = newOwner;
    }
}