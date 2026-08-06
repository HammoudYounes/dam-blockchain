import { ethers } from "ethers";
import axios from "axios";
import { EIP1193Provider } from "./eip6963";

export async function connectWallet(provider: EIP1193Provider | null) {
    if (!provider) {
        alert("No wallet extension detected.");
        return;
    }
    try {
        const accounts: string[] = await provider.request({ method: "eth_requestAccounts" });
        console.log("Connected address:", accounts[0]);
        return accounts[0];
    } catch (error) {
        console.error("Error connecting to wallet:", error);
        alert("Error connecting to wallet");
        return;
    }
}

export async function getNonce(address: string) {
    const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/auth/nonce?address=${address}`);
    return response.data.nonce;
}

export async function login(provider: EIP1193Provider, address: string, nonce: string) {
    const browserProvider = new ethers.BrowserProvider(provider as any);
    const signer = await browserProvider.getSigner();
    const message = `Sign this message to login: ${nonce}`;
    const signature = await signer.signMessage(message);

    const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
        address, signature, nonce,
    });
    return response.data.token;
}

export async function getConnectedWallet(provider: EIP1193Provider | null) {
    if (!provider) return null;
    try {
        const accounts: string[] = await provider.request({ method: "eth_accounts" });
        return accounts.length > 0 ? accounts[0] : null;
    } catch (error) {
        console.error("Error getting connected wallet:", error);
        return null;
    }
}

export async function disconnectWallet(provider: EIP1193Provider | null) {
    if (!provider) {
        alert("No wallet extension detected.");
        return;
    }
    try {
        await provider.request({
            method: "eth_requestAccounts",
            params: [{ eth_accounts: [] }],
        });
    } catch (error) {
        console.error("Error disconnecting wallet:", error);
        alert("Error disconnecting wallet");
    }
}

export async function isWalletConnected(provider: EIP1193Provider | null) {
    if (!provider) return false;
    try {
        const accounts: string[] = await provider.request({ method: "eth_accounts" });
        return accounts.length > 0;
    } catch (error) {
        console.error("Error checking wallet connection:", error);
        return false;
    }
}