// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title DAMAsset
 * @notice ERC-721 contract for minting and transferring digital asset NFTs.
 * Each token represents a unique digital asset registered in the DAM system.
 */
contract DAMAsset is ERC721URIStorage, Ownable {
    // Auto-incrementing token ID counter
    uint256 private _nextTokenId;

    // Maps tokenId to the original creator address (immutable after mint)
    mapping(uint256 => address) private _creators;

    // Prevents the same IPFS URI from being minted twice
    mapping(string => bool) private _registeredURIs;

    // Emitted when a new asset is minted
    event AssetMinted(
        uint256 indexed tokenId,
        address indexed creator,
        string tokenURI
    );

    // Emitted when an asset is transferred to a new owner
    event AssetTransferred(
        uint256 indexed tokenId,
        address indexed from,
        address indexed to
    );

    constructor() ERC721("DAMAsset", "DAM") Ownable(msg.sender) {
        _nextTokenId = 1;
    }

    /**
     * @notice Mint a new NFT representing a digital asset.
     * @param creator The address of the original creator (recorded permanently).
     * @param uri The IPFS metadata URI for this asset.
     * @return tokenId The ID of the newly minted token.
     */
    function mintAsset(
        address creator,
        string memory uri
    ) external returns (uint256) {
        require(creator != address(0), "DAMAsset: creator is zero address");
        require(bytes(uri).length > 0, "DAMAsset: URI is empty");
        require(!_registeredURIs[uri], "DAMAsset: URI already registered");

        uint256 tokenId = _nextTokenId;
        _nextTokenId++;

        _registeredURIs[uri] = true;
        _creators[tokenId] = creator;

        _safeMint(creator, tokenId);
        _setTokenURI(tokenId, uri);

        emit AssetMinted(tokenId, creator, uri);
        return tokenId;
    }

    /**
     * @notice Transfer an asset to a new owner.
     * Only the current token owner can call this.
     * @param tokenId The token to transfer.
     * @param to The recipient address.
     */
    function transferAsset(uint256 tokenId, address to) external {
        require(to != address(0), "DAMAsset: recipient is zero address");
        require(
            ownerOf(tokenId) == msg.sender,
            "DAMAsset: caller is not the token owner"
        );

        safeTransferFrom(msg.sender, to, tokenId);
        emit AssetTransferred(tokenId, msg.sender, to);
    }

    /**
     * @notice Returns the original creator of a token.
     * The creator is recorded at mint time and never changes.
     */
    function creatorOf(uint256 tokenId) external view returns (address) {
        return _creators[tokenId];
    }

    /**
     * @notice Returns whether a given URI has already been registered.
     */
    function isURIRegistered(string memory uri) external view returns (bool) {
        return _registeredURIs[uri];
    }
}