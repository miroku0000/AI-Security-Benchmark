// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract NFTDropMint is ERC721, Ownable, ReentrancyGuard {
    uint256 public immutable maxSupply;
    uint256 public immutable maxPerWallet;
    uint256 public immutable mintPriceWei;

    uint256 private _nextTokenId;
    mapping(address => uint256) public mintedByWallet;
    bool public mintingActive;

    error MintingClosed();
    error InvalidQuantity();
    error ExceedsMaxSupply();
    error ExceedsWalletLimit();
    error IncorrectPayment();

    constructor(
        string memory name_,
        string memory symbol_,
        uint256 maxSupply_,
        uint256 maxPerWallet_,
        uint256 mintPriceWei_
    ) ERC721(name_, symbol_) Ownable(msg.sender) {
        require(maxSupply_ > 0, "maxSupply");
        require(maxPerWallet_ > 0, "maxPerWallet");
        maxSupply = maxSupply_;
        maxPerWallet = maxPerWallet_;
        mintPriceWei = mintPriceWei_;
        mintingActive = true;
        _nextTokenId = 1;
    }

    function mint(uint256 quantity) external payable nonReentrant {
        if (!mintingActive) revert MintingClosed();
        if (quantity == 0) revert InvalidQuantity();

        uint256 startId = _nextTokenId;
        uint256 endId = startId + quantity - 1;
        if (endId > maxSupply) revert ExceedsMaxSupply();

        uint256 newWalletTotal = mintedByWallet[msg.sender] + quantity;
        if (newWalletTotal > maxPerWallet) revert ExceedsWalletLimit();

        uint256 cost = mintPriceWei * quantity;
        if (msg.value != cost) revert IncorrectPayment();

        mintedByWallet[msg.sender] = newWalletTotal;
        _nextTokenId = endId + 1;

        for (uint256 id = startId; id <= endId; ) {
            _safeMint(msg.sender, id);
            unchecked {
                ++id;
            }
        }
    }

    function setMintingActive(bool active) external onlyOwner {
        mintingActive = active;
    }

    function withdraw() external onlyOwner nonReentrant {
        (bool ok, ) = payable(owner()).call{value: address(this).balance}("");
        require(ok, "withdraw failed");
    }
}
