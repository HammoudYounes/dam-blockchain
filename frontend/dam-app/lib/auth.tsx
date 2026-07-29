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


export async function getConnectedWallet() {
    if (!window.ethereum) {
        return null;
    }
    try {
        const accounts = await window.ethereum.request({
            method: "eth_accounts",
        });
        if (accounts.length > 0) {
            console.log("Connected address:", accounts[0]);
            return accounts[0];
        } else {
            console.log("No connected wallet found");
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
        console.log("Wallet disconnected");
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