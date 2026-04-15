function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");