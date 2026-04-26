// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

contract NFTMint is ERC721, Ownable, ReentrancyGuard {
    using Counters for Counters.Counter;

    Counters.Counter private _tokenIdCounter;

    uint256 public constant MAX_SUPPLY = 10000;
    uint256 public constant MAX_MINT_PER_TX = 10;
    uint256 public constant MAX_MINT_PER_WALLET = 50;
    uint256 public mintPrice = 0.1 ether;

    mapping(address => uint256) public mintedPerWallet;
    bool public publicMintActive = false;
    string private _baseTokenURI;

    event PublicMintToggled(bool isActive);
    event MintPriceUpdated(uint256 newPrice);
    event NFTMinted(address indexed to, uint256 indexed tokenId);

    constructor(string memory baseURI) ERC721("NFTDrop", "NFTD") {
        _baseTokenURI = baseURI;
        _tokenIdCounter.increment();
    }

    function publicMint(uint256 quantity) external payable nonReentrant {
        require(publicMintActive, "Public mint is not active");
        require(quantity > 0, "Quantity must be greater than 0");
        require(quantity <= MAX_MINT_PER_TX, "Exceeds max mint per transaction");
        require(_tokenIdCounter.current() + quantity - 1 < MAX_SUPPLY, "Exceeds max supply");
        require(mintedPerWallet[msg.sender] + quantity <= MAX_MINT_PER_WALLET, "Exceeds max mint per wallet");
        require(msg.value >= mintPrice * quantity, "Insufficient payment");

        mintedPerWallet[msg.sender] += quantity;

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = _tokenIdCounter.current();
            _tokenIdCounter.increment();
            _safeMint(msg.sender, tokenId);
            emit NFTMinted(msg.sender, tokenId);
        }
    }

    function ownerMint(address to, uint256 quantity) external onlyOwner {
        require(quantity > 0, "Quantity must be greater than 0");
        require(_tokenIdCounter.current() + quantity - 1 < MAX_SUPPLY, "Exceeds max supply");

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = _tokenIdCounter.current();
            _tokenIdCounter.increment();
            _safeMint(to, tokenId);
            emit NFTMinted(to, tokenId);
        }
    }

    function setPublicMintActive(bool isActive) external onlyOwner {
        publicMintActive = isActive;
        emit PublicMintToggled(isActive);
    }

    function setMintPrice(uint256 newPrice) external onlyOwner {
        mintPrice = newPrice;
        emit MintPriceUpdated(newPrice);
    }

    function setBaseURI(string memory baseURI) external onlyOwner {
        _baseTokenURI = baseURI;
    }

    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }

    function totalSupply() public view returns (uint256) {
        return _tokenIdCounter.current() - 1;
    }

    function getMintedCount(address wallet) external view returns (uint256) {
        return mintedPerWallet[wallet];
    }

    function withdraw() external onlyOwner nonReentrant {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");
        (bool success, ) = msg.sender.call{value: balance}("");
        require(success, "Withdrawal failed");
    }

    receive() external payable {}
}