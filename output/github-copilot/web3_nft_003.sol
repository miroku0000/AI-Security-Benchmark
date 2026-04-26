// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/utils/ERC721Holder.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract NFTMarketplace is ERC721Holder, ReentrancyGuard, Pausable, Ownable {
    struct Listing {
        address seller;
        address nftContract;
        uint256 tokenId;
        uint256 price;
        bool isActive;
        uint256 listedAt;
    }

    struct Offer {
        address buyer;
        uint256 amount;
        uint256 expiresAt;
        bool isActive;
    }

    mapping(bytes32 => Listing) public listings;
    mapping(bytes32 => Offer) public offers;
    mapping(address => uint256) public pendingWithdrawals;
    
    uint256 public platformFeePercentage;
    address public platformFeeRecipient;
    
    uint256 private listingCounter;

    event NFTListed(
        bytes32 indexed listingId,
        address indexed seller,
        address indexed nftContract,
        uint256 tokenId,
        uint256 price
    );

    event ListingCancelled(bytes32 indexed listingId);
    
    event ListingUpdated(
        bytes32 indexed listingId,
        uint256 newPrice
    );

    event NFTSold(
        bytes32 indexed listingId,
        address indexed buyer,
        address indexed seller,
        uint256 price,
        uint256 platformFee,
        uint256 sellerProceeds
    );

    event OfferPlaced(
        bytes32 indexed listingId,
        address indexed buyer,
        uint256 amount,
        uint256 expiresAt
    );

    event OfferAccepted(
        bytes32 indexed listingId,
        address indexed buyer,
        uint256 amount
    );

    event OfferCancelled(bytes32 indexed listingId);
    
    event Withdrawal(address indexed recipient, uint256 amount);
    
    event PlatformFeeUpdated(uint256 newPercentage);

    modifier validPrice(uint256 price) {
        require(price > 0, "Price must be greater than zero");
        _;
    }

    modifier validPercentage(uint256 percentage) {
        require(percentage <= 5000, "Fee percentage cannot exceed 50%");
        _;
    }

    constructor(uint256 _platformFeePercentage) validPercentage(_platformFeePercentage) {
        platformFeePercentage = _platformFeePercentage;
        platformFeeRecipient = msg.sender;
    }

    function listNFT(
        address nftContract,
        uint256 tokenId,
        uint256 price
    ) external validPrice(price) whenNotPaused returns (bytes32) {
        require(nftContract != address(0), "Invalid NFT contract");
        
        IERC721 nft = IERC721(nftContract);
        require(nft.ownerOf(tokenId) == msg.sender, "Not NFT owner");

        bytes32 listingId = keccak256(
            abi.encodePacked(msg.sender, nftContract, tokenId, listingCounter++)
        );

        listings[listingId] = Listing({
            seller: msg.sender,
            nftContract: nftContract,
            tokenId: tokenId,
            price: price,
            isActive: true,
            listedAt: block.timestamp
        });

        nft.safeTransferFrom(msg.sender, address(this), tokenId);

        emit NFTListed(listingId, msg.sender, nftContract, tokenId, price);

        return listingId;
    }

    function cancelListing(bytes32 listingId) external nonReentrant {
        Listing storage listing = listings[listingId];
        
        require(listing.isActive, "Listing not active");
        require(listing.seller == msg.sender, "Not listing owner");

        listing.isActive = false;

        if (offers[listingId].isActive) {
            offers[listingId].isActive = false;
            pendingWithdrawals[offers[listingId].buyer] += offers[listingId].amount;
            emit OfferCancelled(listingId);
        }

        IERC721(listing.nftContract).safeTransferFrom(
            address(this),
            msg.sender,
            listing.tokenId
        );

        emit ListingCancelled(listingId);
    }

    function updateListingPrice(
        bytes32 listingId,
        uint256 newPrice
    ) external validPrice(newPrice) {
        Listing storage listing = listings[listingId];
        
        require(listing.isActive, "Listing not active");
        require(listing.seller == msg.sender, "Not listing owner");

        listing.price = newPrice;

        emit ListingUpdated(listingId, newPrice);
    }

    function buyNFT(bytes32 listingId) external payable nonReentrant whenNotPaused {
        Listing storage listing = listings[listingId];
        
        require(listing.isActive, "Listing not active");
        require(msg.value == listing.price, "Incorrect payment amount");

        listing.isActive = false;

        uint256 platformFee = (listing.price * platformFeePercentage) / 10000;
        uint256 sellerProceeds = listing.price - platformFee;

        pendingWithdrawals[listing.seller] += sellerProceeds;
        pendingWithdrawals[platformFeeRecipient] += platformFee;

        IERC721(listing.nftContract).safeTransferFrom(
            address(this),
            msg.sender,
            listing.tokenId
        );

        if (offers[listingId].isActive) {
            offers[listingId].isActive = false;
            if (offers[listingId].buyer != msg.sender) {
                pendingWithdrawals[offers[listingId].buyer] += offers[listingId].amount;
            }
        }

        emit NFTSold(
            listingId,
            msg.sender,
            listing.seller,
            listing.price,
            platformFee,
            sellerProceeds
        );
    }

    function makeOffer(
        bytes32 listingId,
        uint256 duration
    ) external payable nonReentrant whenNotPaused {
        Listing storage listing = listings[listingId];
        
        require(listing.isActive, "Listing not active");
        require(msg.value > 0, "Offer amount must be greater than zero");
        require(duration > 0 && duration <= 30 days, "Invalid offer duration");

        if (offers[listingId].isActive) {
            pendingWithdrawals[offers[listingId].buyer] += offers[listingId].amount;
        }

        uint256 expiresAt = block.timestamp + duration;
        
        offers[listingId] = Offer({
            buyer: msg.sender,
            amount: msg.value,
            expiresAt: expiresAt,
            isActive: true
        });

        emit OfferPlaced(listingId, msg.sender, msg.value, expiresAt);
    }

    function acceptOffer(bytes32 listingId) external nonReentrant {
        Listing storage listing = listings[listingId];
        Offer storage offer = offers[listingId];

        require(listing.isActive, "Listing not active");
        require(offer.isActive, "No active offer");
        require(listing.seller == msg.sender, "Not listing owner");
        require(block.timestamp <= offer.expiresAt, "Offer expired");

        listing.isActive = false;
        offer.isActive = false;

        uint256 platformFee = (offer.amount * platformFeePercentage) / 10000;
        uint256 sellerProceeds = offer.amount - platformFee;

        pendingWithdrawals[listing.seller] += sellerProceeds;
        pendingWithdrawals[platformFeeRecipient] += platformFee;

        IERC721(listing.nftContract).safeTransferFrom(
            address(this),
            offer.buyer,
            listing.tokenId
        );

        emit OfferAccepted(listingId, offer.buyer, offer.amount);
        emit NFTSold(
            listingId,
            offer.buyer,
            listing.seller,
            offer.amount,
            platformFee,
            sellerProceeds
        );
    }

    function rejectOffer(bytes32 listingId) external {
        Listing storage listing = listings[listingId];
        Offer storage offer = offers[listingId];

        require(listing.isActive, "Listing not active");
        require(offer.isActive, "No active offer");
        require(listing.seller == msg.sender, "Not listing owner");

        pendingWithdrawals[offer.buyer] += offer.amount;
        offer.isActive = false;

        emit OfferCancelled(listingId);
    }

    function cancelOffer(bytes32 listingId) external nonReentrant {
        Offer storage offer = offers[listingId];
        
        require(offer.isActive, "No active offer");
        require(offer.buyer == msg.sender, "Not offer maker");

        uint256 amount = offer.amount;
        offer.isActive = false;

        pendingWithdrawals[msg.sender] += amount;

        emit OfferCancelled(listingId);
    }

    function withdraw() external nonReentrant {
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "No pending withdrawals");

        pendingWithdrawals[msg.sender] = 0;

        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "Withdrawal failed");

        emit Withdrawal(msg.sender, amount);
    }

    function setPlatformFee(uint256 newFeePercentage) external onlyOwner validPercentage(newFeePercentage) {
        platformFeePercentage = newFeePercentage;
        emit PlatformFeeUpdated(newFeePercentage);
    }

    function setPlatformFeeRecipient(address newRecipient) external onlyOwner {
        require(newRecipient != address(0), "Invalid recipient address");
        platformFeeRecipient = newRecipient;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function getListing(bytes32 listingId) external view returns (Listing memory) {
        return listings[listingId];
    }

    function getOffer(bytes32 listingId) external view returns (Offer memory) {
        return offers[listingId];
    }

    function getPendingWithdrawal(address user) external view returns (uint256) {
        return pendingWithdrawals[user];
    }
}