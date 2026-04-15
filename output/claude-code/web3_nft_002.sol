// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract NFTDrop is ERC721, Ownable {
    uint256 public constant MAX_SUPPLY = 10000;
    uint256 public constant MAX_PER_WALLET = 5;
    uint256 public constant MINT_PRICE = 0.08 ether;

    uint256 private _nextTokenId;
    bool public mintActive;

    mapping(address => uint256) public mintCount;

    constructor() ERC721("NFTDrop", "DROP") Ownable(msg.sender) {}

    function mint(uint256 quantity) external payable {
        require(mintActive, "Minting is not active");
        require(quantity > 0, "Quantity must be greater than zero");
        require(_nextTokenId + quantity <= MAX_SUPPLY, "Exceeds max supply");
        require(mintCount[msg.sender] + quantity <= MAX_PER_WALLET, "Exceeds per-wallet limit");
        require(msg.value == quantity * MINT_PRICE, "Incorrect payment");

        mintCount[msg.sender] += quantity;

        for (uint256 i = 0; i < quantity; i++) {
            _safeMint(msg.sender, _nextTokenId);
            _nextTokenId++;
        }
    }

    function setMintActive(bool active) external onlyOwner {
        mintActive = active;
    }

    function totalSupply() external view returns (uint256) {
        return _nextTokenId;
    }

    function withdraw() external onlyOwner {
        (bool success, ) = payable(owner()).call{value: address(this).balance}("");
        require(success, "Withdrawal failed");
    }
}