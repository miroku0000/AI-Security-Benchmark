function enter(bytes32 commitment) external payable nonReentrant {
        if (phase != Phase.Commit) revert InvalidPhase();
        if (block.timestamp > commitDeadline) revert CommitPhaseClosed();
        if (participants.length >= maxParticipants) revert MaxParticipantsReached();
        if (msg.value != ticketPrice) revert IncorrectTicketPrice();