// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

contract NFTCollection is ERC721, ERC721URIStorage, Ownable {
    using Strings for uint256;

    string private baseURI;
    uint256 private nextTokenId;

    event BaseURIUpdated(string indexed newBaseURI);
    event TokenMinted(address indexed to, uint256 indexed tokenId);

    constructor(
        string memory name,
        string memory symbol,
        string memory initialBaseURI
    ) ERC721(name, symbol) {
        baseURI = initialBaseURI;
        nextTokenId = 1;
    }

    function mint(address to) public onlyOwner returns (uint256) {
        uint256 tokenId = nextTokenId;
        nextTokenId++;
        
        _safeMint(to, tokenId);
        emit TokenMinted(to, tokenId);
        
        return tokenId;
    }

    function mintBatch(address to, uint256 quantity) public onlyOwner returns (uint256[] memory) {
        uint256[] memory tokenIds = new uint256[](quantity);
        
        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = nextTokenId;
            nextTokenId++;
            _safeMint(to, tokenId);
            tokenIds[i] = tokenId;
            emit TokenMinted(to, tokenId);
        }
        
        return tokenIds;
    }

    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        require(ownerOf(tokenId) != address(0), "Token does not exist");
        
        string memory base = baseURI;
        return string(abi.encodePacked(base, tokenId.toString(), ".json"));
    }

    function getBaseURI() public view returns (string memory) {
        return baseURI;
    }

    function setBaseURI(string memory newBaseURI) public onlyOwner {
        baseURI = newBaseURI;
        emit BaseURIUpdated(newBaseURI);
    }

    function getNextTokenId() public view returns (uint256) {
        return nextTokenId;
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    function _update(address to, uint256 tokenId, address auth)
        internal
        override(ERC721)
        returns (address)
    {
        return super._update(to, tokenId, auth);
    }

    function _increaseBalance(address account, uint128 value)
        internal
        override(ERC721)
    {
        super._increaseBalance(account, value);
    }
}