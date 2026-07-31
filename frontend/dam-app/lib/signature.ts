import { ethers } from "ethers";

/**
 * Signs a perceptual hash (pHash) using the connected wallet.
 * @param pHash The 32-byte perceptual hash (as a hex string).
 * @returns The r, s, and v components of the signature.
 */
export async function signPHash(pHash: string) {
    if (typeof window === "undefined" || !window.ethereum) {
        throw new Error("MetaMask not installed or window undefined");
    }

    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();

    // Ensure pHash is treated as bytes
    const pHashBytes = ethers.getBytes(pHash);

    // Sign the hash
    // Note: signMessage prepends the standard Ethereum message prefix.
    // Ensure the smart contract verification (ECDSA.recover) handles this prefix.
    const rawSignature = await signer.signMessage(pHashBytes);

    // Decompose into components
    const sig = ethers.Signature.from(rawSignature);

    return {
        r: sig.r,
        s: sig.s,
        v: sig.v,
    };
}
