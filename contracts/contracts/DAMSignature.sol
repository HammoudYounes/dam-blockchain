// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

// DAMSignature.sol
import "./DAMAsset.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

contract DAMSignature {
    struct AssetSignature {
        bytes32 perceptualHash;
        bytes32 r;
        bytes32 s;
        uint8   v;
        address creator;        // the REAL owner/creator — untouched by who signed
        uint256 registeredAt;
    }

    DAMAsset public immutable assetContract;   //  dependency
    address  public immutable trustedSigner;   // address of your backend's key

    mapping(uint256 => AssetSignature) private _signatures;
    mapping(bytes32  => bool)          private _registeredHashes;

    event AssetRegistered(uint256 indexed tokenId, address indexed creator, bytes32 perceptualHash, uint256 timestamp);

    constructor(address assetContractAddress, address trustedSignerAddress) {
        assetContract  = DAMAsset(assetContractAddress);
        trustedSigner  = trustedSignerAddress;
    }

    function registerSignature(
        uint256 tokenId,
        bytes32 perceptualHash,
        bytes32 r,
        bytes32 s,
        uint8   v,
        address creator
    ) external {
        require(_signatures[tokenId].creator == address(0), "Token already registered");
        require(!_registeredHashes[perceptualHash], "Hash already registered");
        require(creator != address(0), "Invalid creator");

        //creator can no longer be an arbitrary caller-supplied value —
        // it must match what DAMAsset actually recorded at mint time.
        require(creator == assetContract.creatorOf(tokenId), "Creator mismatch with DAMAsset");

        //validate the signature AT WRITE TIME, not just later at verify time.
        bytes32 ethSignedHash = MessageHashUtils.toEthSignedMessageHash(perceptualHash);
        address recovered = ECDSA.recover(ethSignedHash, v, r, s);
        require(recovered == trustedSigner, "Signature not from trusted signer");

        _signatures[tokenId] = AssetSignature({
            perceptualHash: perceptualHash, r: r, s: s, v: v,
            creator: creator, registeredAt: block.timestamp
        });
        _registeredHashes[perceptualHash] = true;

        emit AssetRegistered(tokenId, creator, perceptualHash, block.timestamp);
    }

    function getAssetSignature(uint256 tokenId) external view returns (AssetSignature memory) {
    require(_signatures[tokenId].creator != address(0), "Token not registered");
    return _signatures[tokenId];
    }

    function isRegistered(uint256 tokenId) external view returns (bool) {
        return _signatures[tokenId].creator != address(0);
    }

    function isHashRegistered(bytes32 hash) external view returns (bool) {
        return _registeredHashes[hash];
    }
}