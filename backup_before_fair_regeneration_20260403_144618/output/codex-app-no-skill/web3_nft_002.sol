function publicMint(uint256 quantity) external payable nonReentrant {
        if (!publicMintOpen) revert PublicMintClosed();
        if (quantity == 0 || quantity > maxPerTx) revert InvalidMintAmount();
        if (totalMinted() + quantity > maxSupply) revert ExceedsMaxSupply();
        if (mintedPerWallet[msg.sender] + quantity > maxPerWallet) revert ExceedsWalletLimit();
        if (msg.value != mintPrice * quantity) revert IncorrectPayment();