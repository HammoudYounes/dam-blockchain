// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import "./DAMSignature.sol";

/**
 * @title DAMVerifier
 * @notice Verifies that a submitted perceptual hash matches the registered hash
 * for a token, and that the stored signature was produced by the registered creator.
 */
contract DAMVerifier {
    using ECDSA for bytes32;

    DAMSignature private immutable _damSignature;

    event VerificationPerformed(
        uint256 indexed tokenId,
        address indexed submittedBy,
        bool result
    );

    constructor(address damSignatureAddress) {
        require(damSignatureAddress != address(0), "DAMVerifier: invalid DAMSignature address");
        _damSignature = DAMSignature(damSignatureAddress);
    }

    /**
     * @notice Verifies that the submitted hash matches the registered hash for a token
     * and that the stored signature was produced by the registered creator.
     * @param tokenId The token ID to verify against.
     * @param submittedHash The perceptual hash of the submitted image.
     * @return true if the hash matches and the signature is valid.
     */
    function verifySignature(
        uint256 tokenId,
        bytes32 submittedHash
    ) external returns (bool) {
        DAMSignature.AssetSignature memory asset = _damSignature.getAssetSignature(tokenId);

        if (submittedHash != asset.perceptualHash) {
            emit VerificationPerformed(tokenId, msg.sender, false);
            return false;
        }

        bytes32 ethSignedHash = MessageHashUtils.toEthSignedMessageHash(asset.perceptualHash);
        bytes memory signature = abi.encodePacked(asset.r, asset.s, asset.v);
        address recovered = ECDSA.recover(ethSignedHash, signature);

        bool result = (recovered == asset.creator);
        emit VerificationPerformed(tokenId, msg.sender, result);
        return result;
    }

    /**
     * @notice Read-only version of verifySignature for off-chain calls.
     * Does not emit an event.
     */
    function verifySignatureView(
        uint256 tokenId,
        bytes32 submittedHash
    ) external view returns (bool) {
        DAMSignature.AssetSignature memory asset = _damSignature.getAssetSignature(tokenId);

        if (submittedHash != asset.perceptualHash) {
            return false;
        }

        bytes32 ethSignedHash = MessageHashUtils.toEthSignedMessageHash(asset.perceptualHash);
        bytes memory signature = abi.encodePacked(asset.r, asset.s, asset.v);
        address recovered = ECDSA.recover(ethSignedHash, signature);

        return (recovered == asset.creator);
    }
}