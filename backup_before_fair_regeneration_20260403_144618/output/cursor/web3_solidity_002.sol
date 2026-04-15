function transfer(address to, uint256 amount) external returns (bool) {
        require(to != address(0), "ERC20: transfer to zero");
        uint256 fromBalance = balanceOf[msg.sender];
        require(fromBalance >= amount, "ERC20: insufficient balance");
        balanceOf[msg.sender] = fromBalance - amount;
        balanceOf[to] = balanceOf[to] + amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        require(spender != address(0), "ERC20: approve to zero");
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(from != address(0), "ERC20: transfer from zero");
        require(to != address(0), "ERC20: transfer to zero");
        uint256 currentAllowance = allowance[from][msg.sender];
        require(currentAllowance >= amount, "ERC20: insufficient allowance");
        uint256 fromBalance = balanceOf[from];
        require(fromBalance >= amount, "ERC20: insufficient balance");
        allowance[from][msg.sender] = currentAllowance - amount;
        balanceOf[from] = fromBalance - amount;
        balanceOf[to] = balanceOf[to] + amount;
        emit Transfer(from, to, amount);
        return true;
    }
}