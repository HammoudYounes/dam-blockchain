// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * @title DAMSignature
 * @notice Stores the perceptual hash and ECDSA signature for each registered asset.
 * Signature is stored as (r, s, v) components to minimize storage slot usage.
 * Prevents duplicate registration of the same asset.
 */
contract DAMSignature {
    struct AssetSignature {
        bytes32 perceptualHash;
        bytes32 r;
        bytes32 s;
        uint8 v;
        address creator;       // non-zero iff registered
        uint256 registeredAt;
    }

    // Maps tokenId to its signature data
    mapping(uint256 => AssetSignature) private _signatures;

    // Prevents the same perceptual hash from being registered twice
    mapping(bytes32 => bool) private _registeredHashes;

    event AssetRegistered(
        uint256 indexed tokenId,
        address indexed creator,
        bytes32 perceptualHash,
        uint256 timestamp
    );

    /**
     * @notice Register the perceptual hash and ECDSA signature for a minted asset.
     * @param tokenId The token ID from DAMAsset.
     * @param perceptualHash The 32-byte perceptual hash of the image.
     * @param r ECDSA signature component r.
     * @param s ECDSA signature component s.
     * @param v ECDSA signature component v.
     * @param creator The original creator's wallet address.
     */
    function registerSignature(
        uint256 tokenId,
        bytes32 perceptualHash,
        bytes32 r,
        bytes32 s,
        uint8 v,
        address creator
    ) external {
        require(tokenId > 0, "DAMSignature: invalid token ID");
        require(_signatures[tokenId].creator == address(0), "DAMSignature: token already registered");
        require(!_registeredHashes[perceptualHash], "DAMSignature: hash already registered");
        require(creator != address(0), "DAMSignature: creator is zero address");

        _signatures[tokenId] = AssetSignature({
            perceptualHash: perceptualHash,
            r: r,
            s: s,
            v: v,
            creator: creator,
            registeredAt: block.timestamp
        });

        _registeredHashes[perceptualHash] = true;

        emit AssetRegistered(tokenId, creator, perceptualHash, block.timestamp);
    }

    /**
     * @notice Returns the full signature data for a given token.
     */
    function getAssetSignature(
        uint256 tokenId
    ) external view returns (AssetSignature memory) {
        require(_signatures[tokenId].creator != address(0), "DAMSignature: token not registered");
        return _signatures[tokenId];
    }

    /**
     * @notice Returns whether a token has been registered.
     */
    function isRegistered(uint256 tokenId) external view returns (bool) {
        return _signatures[tokenId].creator != address(0);
    }

    /**
     * @notice Returns whether a perceptual hash has already been registered.
     */
    function isHashRegistered(bytes32 perceptualHash) external view returns (bool) {
        return _registeredHashes[perceptualHash];
    }
}