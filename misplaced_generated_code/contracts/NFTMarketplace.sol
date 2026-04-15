// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {IERC721Receiver} from "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract NFTMarketplace is IERC721Receiver, ReentrancyGuard, Ownable {
    struct Listing {
        address seller;
        uint256 price;
    }

    uint256 public feeBps;
    address public feeRecipient;

    mapping(address collection => mapping(uint256 tokenId => Listing)) private _listings;

    event Listed(address indexed collection, uint256 indexed tokenId, address indexed seller, uint256 price);
    event Sale(
        address indexed collection,
        uint256 indexed tokenId,
        address indexed buyer,
        address seller,
        uint256 price,
        uint256 feeAmount,
        uint256 sellerProceeds
    );
    event ListingCancelled(address indexed collection, uint256 indexed tokenId, address indexed seller);
    event FeeUpdated(uint256 feeBps);
    event FeeRecipientUpdated(address indexed recipient);

    error NotSeller();
    error NotListed();
    error InvalidPrice();
    error InvalidFee();
    error PaymentMismatch();
    error TransferFailed();

    constructor(address feeRecipient_, uint256 feeBps_) Ownable(msg.sender) {
        if (feeBps_ > 10_000) revert InvalidFee();
        feeRecipient = feeRecipient_;
        feeBps = feeBps_;
    }

    function setFeeBps(uint256 newFeeBps) external onlyOwner {
        if (newFeeBps > 10_000) revert InvalidFee();
        feeBps = newFeeBps;
        emit FeeUpdated(newFeeBps);
    }

    function setFeeRecipient(address newRecipient) external onlyOwner {
        feeRecipient = newRecipient;
        emit FeeRecipientUpdated(newRecipient);
    }

    function getListing(address collection, uint256 tokenId) external view returns (address seller, uint256 price) {
        Listing storage l = _listings[collection][tokenId];
        return (l.seller, l.price);
    }

    function list(address collection, uint256 tokenId, uint256 price) external {
        if (price == 0) revert InvalidPrice();
        IERC721 nft = IERC721(collection);
        if (nft.ownerOf(tokenId) != msg.sender) revert NotSeller();
        nft.safeTransferFrom(msg.sender, address(this), tokenId);
        _listings[collection][tokenId] = Listing({seller: msg.sender, price: price});
        emit Listed(collection, tokenId, msg.sender, price);
    }

    function cancelListing(address collection, uint256 tokenId) external {
        Listing storage l = _listings[collection][tokenId];
        if (l.price == 0) revert NotListed();
        if (l.seller != msg.sender) revert NotSeller();
        address seller = l.seller;
        delete _listings[collection][tokenId];
        IERC721(collection).safeTransferFrom(address(this), seller, tokenId);
        emit ListingCancelled(collection, tokenId, seller);
    }

    function buy(address collection, uint256 tokenId) external payable nonReentrant {
        Listing storage l = _listings[collection][tokenId];
        if (l.price == 0) revert NotListed();
        uint256 price = l.price;
        if (msg.value != price) revert PaymentMismatch();
        address seller = l.seller;
        delete _listings[collection][tokenId];

        uint256 feeAmount = (price * feeBps) / 10_000;
        uint256 sellerProceeds = price - feeAmount;

        if (feeAmount > 0) {
            _sendValue(payable(feeRecipient), feeAmount);
        }
        if (sellerProceeds > 0) {
            _sendValue(payable(seller), sellerProceeds);
        }

        IERC721(collection).safeTransferFrom(address(this), msg.sender, tokenId);
        emit Sale(collection, tokenId, msg.sender, seller, price, feeAmount, sellerProceeds);
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure override returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    function _sendValue(address payable to, uint256 amount) private {
        (bool ok, ) = to.call{value: amount}("");
        if (!ok) revert TransferFailed();
    }

    receive() external payable {}
}
