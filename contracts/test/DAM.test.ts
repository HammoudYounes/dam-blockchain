import { expect } from "chai";
import { ethers } from "hardhat";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";
import { DAMAsset, DAMSignature, DAMVerifier } from "../typechain-types";

describe("DAM System", function () {
  let damAsset: DAMAsset;
  let damSignature: DAMSignature;
  let damVerifier: DAMVerifier;
  let owner: SignerWithAddress;
  let creator: SignerWithAddress;
  let attacker: SignerWithAddress;

  const SAMPLE_URI = "ipfs://QmSampleHash123";
  const SAMPLE_URI_2 = "ipfs://QmSampleHash456";
  const PERCEPTUAL_HASH = ethers.keccak256(ethers.toUtf8Bytes("sample_image_hash"));

  // Split a signature into r, s, v components
  async function signAndSplit(
    signer: SignerWithAddress,
    hash: string
  ): Promise<{ r: string; s: string; v: number }> {
    const messageBytes = ethers.getBytes(hash);
    const flatSig = await signer.signMessage(messageBytes);
    const sig = ethers.Signature.from(flatSig);
    return { r: sig.r, s: sig.s, v: sig.v };
  }

  beforeEach(async function () {
    [owner, creator, attacker] = await ethers.getSigners();

    const DAMAssetFactory = await ethers.getContractFactory("DAMAsset");
    damAsset = await DAMAssetFactory.deploy();

    const DAMSignatureFactory = await ethers.getContractFactory("DAMSignature");
    damSignature = await DAMSignatureFactory.deploy();

    const DAMVerifierFactory = await ethers.getContractFactory("DAMVerifier");
    damVerifier = await DAMVerifierFactory.deploy(await damSignature.getAddress());
  });

  // ─────────────────────────────────────────────
  // DAMAsset
  // ─────────────────────────────────────────────
  describe("DAMAsset", function () {
    describe("mintAsset", function () {
      it("should mint a token and assign it to the creator", async function () {
        await damAsset.mintAsset(creator.address, SAMPLE_URI);
        expect(await damAsset.ownerOf(1)).to.equal(creator.address);
      });

      it("should record the correct creator", async function () {
        await damAsset.mintAsset(creator.address, SAMPLE_URI);
        expect(await damAsset.creatorOf(1)).to.equal(creator.address);
      });

      it("should set the correct token URI", async function () {
        await damAsset.mintAsset(creator.address, SAMPLE_URI);
        expect(await damAsset.tokenURI(1)).to.equal(SAMPLE_URI);
      });

      it("should increment token IDs sequentially", async function () {
        await damAsset.mintAsset(creator.address, SAMPLE_URI);
        await damAsset.mintAsset(creator.address, SAMPLE_URI_2);
        expect(await damAsset.ownerOf(1)).to.equal(creator.address);
        expect(await damAsset.ownerOf(2)).to.equal(creator.address);
      });

      it("should emit AssetMinted event", async function () {
        await expect(damAsset.mintAsset(creator.address, SAMPLE_URI))
          .to.emit(damAsset, "AssetMinted")
          .withArgs(1, creator.address, SAMPLE_URI);
      });

      it("should revert on duplicate URI", async function () {
        await damAsset.mintAsset(creator.address, SAMPLE_URI);
        await expect(
          damAsset.mintAsset(creator.address, SAMPLE_URI)
        ).to.be.revertedWith("DAMAsset: URI already registered");
      });

      it("should revert on zero address creator", async function () {
        await expect(
          damAsset.mintAsset(ethers.ZeroAddress, SAMPLE_URI)
        ).to.be.revertedWith("DAMAsset: creator is zero address");
      });

      it("should revert on empty URI", async function () {
        await expect(
          damAsset.mintAsset(creator.address, "")
        ).to.be.revertedWith("DAMAsset: URI is empty");
      });

      it("should mark URI as registered after mint", async function () {
        await damAsset.mintAsset(creator.address, SAMPLE_URI);
        expect(await damAsset.isURIRegistered(SAMPLE_URI)).to.equal(true);
      });

      it("should return false for unregistered URI", async function () {
        expect(await damAsset.isURIRegistered(SAMPLE_URI)).to.equal(false);
      });
    });

    describe("transferAsset", function () {
      beforeEach(async function () {
        await damAsset.mintAsset(creator.address, SAMPLE_URI);
      });

      it("should transfer token to new owner", async function () {
        await damAsset.connect(creator).transferAsset(1, attacker.address);
        expect(await damAsset.ownerOf(1)).to.equal(attacker.address);
      });

      it("should emit AssetTransferred event", async function () {
        await expect(damAsset.connect(creator).transferAsset(1, attacker.address))
          .to.emit(damAsset, "AssetTransferred")
          .withArgs(1, creator.address, attacker.address);
      });

      it("should preserve original creator after transfer", async function () {
        await damAsset.connect(creator).transferAsset(1, attacker.address);
        expect(await damAsset.creatorOf(1)).to.equal(creator.address);
      });

      it("should revert if non-owner attempts transfer", async function () {
        await expect(
          damAsset.connect(attacker).transferAsset(1, attacker.address)
        ).to.be.revertedWith("DAMAsset: caller is not the token owner");
      });

      it("should revert on transfer to zero address", async function () {
        await expect(
          damAsset.connect(creator).transferAsset(1, ethers.ZeroAddress)
        ).to.be.revertedWith("DAMAsset: recipient is zero address");
      });
    });
  });

  // ─────────────────────────────────────────────
  // DAMSignature
  // ─────────────────────────────────────────────
  describe("DAMSignature", function () {
    let r: string;
    let s: string;
    let v: number;

    beforeEach(async function () {
      ({ r, s, v } = await signAndSplit(creator, PERCEPTUAL_HASH));
    });

    describe("registerSignature", function () {
      it("should register a signature successfully", async function () {
        await damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address);
        expect(await damSignature.isRegistered(1)).to.equal(true);
      });

      it("should store the correct creator address", async function () {
        await damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address);
        const asset = await damSignature.getAssetSignature(1);
        expect(asset.creator).to.equal(creator.address);
      });

      it("should store the correct perceptual hash", async function () {
        await damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address);
        const asset = await damSignature.getAssetSignature(1);
        expect(asset.perceptualHash).to.equal(PERCEPTUAL_HASH);
      });

      it("should store correct r, s, v components", async function () {
        await damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address);
        const asset = await damSignature.getAssetSignature(1);
        expect(asset.r).to.equal(r);
        expect(asset.s).to.equal(s);
        expect(asset.v).to.equal(v);
      });

      it("should emit AssetRegistered event", async function () {
        await expect(
          damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address)
        ).to.emit(damSignature, "AssetRegistered");
      });

      it("should revert on duplicate tokenId", async function () {
        await damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address);
        await expect(
          damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address)
        ).to.be.revertedWith("DAMSignature: token already registered");
      });

      it("should revert on duplicate perceptual hash", async function () {
        await damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address);
        const hash2 = ethers.keccak256(ethers.toUtf8Bytes("other_image"));
        const { r: r2, s: s2, v: v2 } = await signAndSplit(creator, hash2);
        await expect(
          damSignature.registerSignature(2, PERCEPTUAL_HASH, r2, s2, v2, creator.address)
        ).to.be.revertedWith("DAMSignature: hash already registered");
      });

      it("should revert on zero address creator", async function () {
        await expect(
          damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, ethers.ZeroAddress)
        ).to.be.revertedWith("DAMSignature: creator is zero address");
      });

      it("should revert on invalid token ID", async function () {
        await expect(
          damSignature.registerSignature(0, PERCEPTUAL_HASH, r, s, v, creator.address)
        ).to.be.revertedWith("DAMSignature: invalid token ID");
      });
    });

    describe("getAssetSignature", function () {
      it("should revert for unregistered token", async function () {
        await expect(
          damSignature.getAssetSignature(99)
        ).to.be.revertedWith("DAMSignature: token not registered");
      });

      it("should return registeredAt timestamp", async function () {
        await damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address);
        const asset = await damSignature.getAssetSignature(1);
        expect(asset.registeredAt).to.be.greaterThan(0);
      });
    });

    describe("isHashRegistered", function () {
      it("should return false for unregistered hash", async function () {
        expect(await damSignature.isHashRegistered(PERCEPTUAL_HASH)).to.equal(false);
      });

      it("should return true after registration", async function () {
        await damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address);
        expect(await damSignature.isHashRegistered(PERCEPTUAL_HASH)).to.equal(true);
      });
    });
  });

  // ─────────────────────────────────────────────
  // DAMVerifier
  // ─────────────────────────────────────────────
  describe("DAMVerifier", function () {
    let r: string;
    let s: string;
    let v: number;

    beforeEach(async function () {
      ({ r, s, v } = await signAndSplit(creator, PERCEPTUAL_HASH));
      await damSignature.registerSignature(1, PERCEPTUAL_HASH, r, s, v, creator.address);
    });

    describe("verifySignatureView", function () {
      it("should return true for correct hash and valid signature", async function () {
        expect(
          await damVerifier.verifySignatureView(1, PERCEPTUAL_HASH)
        ).to.equal(true);
      });

      it("should return false if submitted hash differs", async function () {
        const alteredHash = ethers.keccak256(ethers.toUtf8Bytes("different_image"));
        expect(
          await damVerifier.verifySignatureView(1, alteredHash)
        ).to.equal(false);
      });

      it("should return false for a hash signed by a different wallet", async function () {
        const attackerHash = ethers.keccak256(ethers.toUtf8Bytes("attacker_image"));
        const { r: ar, s: as_, v: av } = await signAndSplit(attacker, attackerHash);
        await damSignature.registerSignature(2, attackerHash, ar, as_, av, creator.address);
        expect(
          await damVerifier.verifySignatureView(2, attackerHash)
        ).to.equal(false);
      });

      it("should revert for unregistered token", async function () {
        await expect(
          damVerifier.verifySignatureView(99, PERCEPTUAL_HASH)
        ).to.be.revertedWith("DAMSignature: token not registered");
      });
    });

    describe("verifySignature (with event)", function () {
      it("should emit VerificationPerformed on success", async function () {
        await expect(damVerifier.verifySignature(1, PERCEPTUAL_HASH))
          .to.emit(damVerifier, "VerificationPerformed")
          .withArgs(1, owner.address, true);
      });

      it("should emit VerificationPerformed with false on hash mismatch", async function () {
        const wrongHash = ethers.keccak256(ethers.toUtf8Bytes("wrong"));
        await expect(damVerifier.verifySignature(1, wrongHash))
          .to.emit(damVerifier, "VerificationPerformed")
          .withArgs(1, owner.address, false);
      });
    });

    describe("constructor", function () {
      it("should revert if deployed with zero address", async function () {
        const DAMVerifierFactory = await ethers.getContractFactory("DAMVerifier");
        await expect(
          DAMVerifierFactory.deploy(ethers.ZeroAddress)
        ).to.be.revertedWith("DAMVerifier: invalid DAMSignature address");
      });
    });
  });
});