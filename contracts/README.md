# DAM System — Smart Contracts

Blockchain layer for the Blockchain-backed Digital Asset Management system.  
Three Solidity contracts deployed on **Polygon Amoy testnet** via Hardhat.

---

## Deployed Contracts

| Contract | Address | Polygonscan |
|---|---|---|
| DAMAsset | `0xE7127207eB3E24B34021344aCB7D7Cff5D092A59` | [View](https://amoy.polygonscan.com/address/0xE7127207eB3E24B34021344aCB7D7Cff5D092A59#code) |
| DAMSignature | `0xA55Ba1468967ad3a11adD593eA702673cc66d660` | [View](https://amoy.polygonscan.com/address/0xA55Ba1468967ad3a11adD593eA702673cc66d660#code) |
| DAMVerifier | `0x1524c7e44fDad13f4288b36Fca468647002DbecF` | [View](https://amoy.polygonscan.com/address/0x1524c7e44fDad13f4288b36Fca468647002DbecF#code) |

All three contracts are verified — source code is publicly readable on Polygonscan.

---

## What Each Contract Does

**DAMAsset.sol** — ERC-721 NFT contract. Handles minting, ownership transfer, and creator registration. Each token represents one uploaded image. The original creator address is stored permanently at mint time and never changes, even after the token is transferred.

**DAMSignature.sol** — Stores the cryptographic fingerprint of each asset on-chain: the perceptual hash (bytes32) and the ECDSA signature components (r, s, v) produced by the creator's private key. This is the immutable proof of prior authorship.

**DAMVerifier.sol** — Answers the question: was this token's perceptual hash signed by its registered creator? Performs on-chain ECDSA recovery via OpenZeppelin and compares the recovered address against the stored creator. Exposes both a gas-costing version (with on-chain audit trail) and a free view version for frontend read-only checks.

---

## Prerequisites

- Node.js v20+ (use NVM: `nvm use 20`)
- npm 10+
- A funded Polygon Amoy wallet (get test POL from [https://faucet.polygon.technology](https://faucet.polygon.technology))

---

## Setup

**1. Install dependencies**
```bash
cd contracts
npm install
```

**2. Configure environment**

Copy `.env.example` to `.env` and fill in the values:
```bash
cp .env.example .env
```

```dotenv
ALCHEMY_AMOY_URL=https://polygon-amoy.g.alchemy.com/v2/YOUR_KEY
DEPLOYER_PRIVATE_KEY=YOUR_WALLET_PRIVATE_KEY
POLYGONSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY

# Already deployed — do not change unless redeploying
DAM_ASSET_ADDRESS=0xE7127207eB3E24B34021344aCB7D7Cff5D092A59
DAM_SIGNATURE_ADDRESS=0xA55Ba1468967ad3a11adD593eA702673cc66d660
DAM_VERIFIER_ADDRESS=0x1524c7e44fDad13f4288b36Fca468647002DbecF
```

To get your keys:
- **ALCHEMY_AMOY_URL** → [https://dashboard.alchemy.com](https://dashboard.alchemy.com) → create app on Polygon Amoy → copy HTTPS URL
- **DEPLOYER_PRIVATE_KEY** → MetaMask → Account Details → Export Private Key (use a dedicated dev wallet, never your main wallet)
- **POLYGONSCAN_API_KEY** → [https://etherscan.io/myapikey](https://etherscan.io/myapikey) → create account → generate key (the Etherscan V2 key works for Polygon)

**3. Compile**
```bash
npx hardhat compile
```

**4. Run tests**
```bash
npx hardhat test
```

All 35 tests should pass.

---

## For the NestJS Backend Team

The contracts are already deployed — you do not need to redeploy. You only need the three contract addresses from `.env.example` and the ABIs.

**Getting the ABIs**

After running `npx hardhat compile`, the ABIs are generated at:
```
contracts/artifacts/contracts/DAMAsset.sol/DAMAsset.json
contracts/artifacts/contracts/DAMSignature.sol/DAMSignature.json
contracts/artifacts/contracts/DAMVerifier.sol/DAMVerifier.json
```

Copy the `abi` field from each JSON file into your NestJS service.

**Calling the contracts with ethers.js v6**

```typescript
import { ethers } from 'ethers';
import DAMAssetABI from './abis/DAMAsset.json';
import DAMSignatureABI from './abis/DAMSignature.json';
import DAMVerifierABI from './abis/DAMVerifier.json';

const provider = new ethers.JsonRpcProvider(process.env.ALCHEMY_AMOY_URL);
const signer = new ethers.Wallet(process.env.DEPLOYER_PRIVATE_KEY, provider);

const damAsset = new ethers.Contract(process.env.DAM_ASSET_ADDRESS, DAMAssetABI, signer);
const damSignature = new ethers.Contract(process.env.DAM_SIGNATURE_ADDRESS, DAMSignatureABI, signer);
const damVerifier = new ethers.Contract(process.env.DAM_VERIFIER_ADDRESS, DAMVerifierABI, signer);
```

**Mint flow (NftModule)**

```typescript
// 1. Mint the NFT
const tx = await damAsset.mintAsset(creatorAddress, ipfsURI);
const receipt = await tx.wait();
const tokenId = receipt.logs[0].args.tokenId; // from AssetMinted event

// 2. Register the signature
// pHashBytes32: the 64-bit boolean array from Python, packed into bytes32
// r, s, v: the three components of the ECDSA signature
const tx2 = await damSignature.registerSignature(tokenId, pHashBytes32, r, s, v, creatorAddress);
await tx2.wait();
```

**Verification flow (SignatureModule)**

```typescript
// Free read-only check — costs zero gas
const isValid = await damVerifier.verifySignatureView(tokenId, submittedHashBytes32);
// Returns true if the submitted hash was signed by the registered creator
```

**Converting the Python hash to bytes32**

The Python hashing layer returns a 64-element boolean array. Convert it to bytes32 before calling the contract:

```typescript
function boolArrayToBytes32(boolArray: boolean[]): string {
  let bits = 0n;
  for (let i = 0; i < 64; i++) {
    if (boolArray[i]) bits |= (1n << BigInt(63 - i));
  }
  return '0x' + bits.toString(16).padStart(64, '0');
}
```

**Splitting a signature into r, s, v**

```typescript
const sig = ethers.Signature.from(rawSignature); // rawSignature is the 65-byte hex string from Python
const { r, s, v } = sig;
```

---

## Gas Reference

| Function | Avg Gas | Notes |
|---|---|---|
| `mintAsset()` | ~147,557 | Dominant cost: ERC-721 URI string storage |
| `transferAsset()` | ~59,772 | Standard ERC-721 transfer |
| `registerSignature()` | ~159,775 | 5 cold SSTORE writes |
| `verifySignature()` | ~42,784 | Writes one event log |
| `verifySignatureView()` | 0 | Free off-chain read |

---

## Network

- **Chain:** Polygon Amoy testnet
- **Chain ID:** 80002
- **RPC:** via Alchemy (see `.env`)
- **Explorer:** [https://amoy.polygonscan.com](https://amoy.polygonscan.com)

---

## Redeployment (only if needed)

If contracts ever need to be redeployed from scratch:

```bash
npx hardhat ignition deploy ignition/modules/DAMDeploy.ts --network amoy
```

Then verify each contract:
```bash
npx hardhat verify --network amoy <DAMAsset_address>
npx hardhat verify --network amoy <DAMSignature_address>
npx hardhat verify --network amoy <DAMVerifier_address> <DAMSignature_address>
```

Update the three `DAM_*_ADDRESS` values in `.env.example` with the new addresses.

---

*DNIIT — University of Da Nang | Blockchain-backed Digital Asset Management System | Phase 2*