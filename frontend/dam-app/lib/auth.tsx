import { ethers } from "ethers";

export async function connectWallet() {
    if (!window.ethereum) {
        alert("MetaMask not installed");
        return;
    }
    try {
        const [address] = await window.ethereum.request({
            method: "eth_requestAccounts",
        });
        console.log("Connected address:", address);
        return address;
    } catch (error) {
        console.error("Error connecting to MetaMask:", error);
        alert("Error connecting to MetaMask");
        return;
    }
}

export async function getNonce(address: string) {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/nonce?address=${address}`);
    const data = await response.json();
    return data.nonce;
}

export async function login(address: string, nonce: string) {
    if (!window.ethereum) throw new Error("No ethereum provider");
    const provider = new ethers.BrowserProvider(window.ethereum as any);
    const signer = await provider.getSigner();
    const message = `Sign this message to login: ${nonce}`;
    const signature = await signer.signMessage(message);

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address, signature, nonce }),
    });
    const data = await response.json();
    return data.token;
}

export async function getConnectedWallet() {
    if (!window.ethereum) {
        return null;
    }
    try {
        const accounts = await window.ethereum.request({
            method: "eth_accounts",
        });
        if (accounts.length > 0) {
            return accounts[0];
        } else {
            return null;
        }
    } catch (error) {
        console.error("Error getting connected wallet:", error);
        alert("Error getting connected wallet");
        return null;
    }
}

export async function disconnectWallet() {
    if (!window.ethereum) {
        alert("MetaMask not installed");
        return;
    }
    try {
        await window.ethereum.request({
            method: "eth_requestAccounts",
            params: [{ eth_accounts: [] }],
        });
    } catch (error) {
        console.error("Error disconnecting wallet:", error);
        alert("Error disconnecting wallet");
    }
}

export async function isWalletConnected() {
    if (!window.ethereum) {
        return false;
    }
    try {
        const accounts = await window.ethereum.request({
            method: "eth_accounts",
        });
        return accounts.length > 0;
    } catch (error) {
        console.error("Error checking wallet connection:", error);
        alert("Error checking wallet connection");
        return false;
    }
}