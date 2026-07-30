import { useState, useEffect } from "react";
import { connectWallet, getConnectedWallet, disconnectWallet, getNonce, login } from "@/lib/auth";

export const useWallet = () => {
    const [walletAddress, setWalletAddress] = useState<string | null>(null);
    const [token, setToken] = useState<string | null>(null);

    useEffect(() => {
        const checkConnection = async () => {
            if (typeof window !== "undefined" && window.ethereum) {
                const address = await getConnectedWallet();
                setWalletAddress(address || null);
            }
        };
        checkConnection();
        const savedToken = localStorage.getItem("jwt");
        if (savedToken) setToken(savedToken);
    }, []);

    useEffect(() => {
        if (typeof window === "undefined" || !window.ethereum) return;

        const ethereum = window.ethereum;

        const handleAccountsChanged = (accounts: string[]) => {
            if (accounts && accounts.length > 0) {
                setWalletAddress(accounts[0]);
            } else {
                setWalletAddress(null);
                setToken(null);
                localStorage.removeItem("jwt");
            }
        };

        ethereum.on?.("accountsChanged", handleAccountsChanged);

        return () => {
            ethereum.removeListener?.("accountsChanged", handleAccountsChanged);
        };
    }, []);

    const handleConnect = async () => {
        const address = await connectWallet();
        if (address) {
            setWalletAddress(address);
            // Auto login after connecting
            handleLogin(address);
        }
    };

    const handleLogin = async (address: string) => {
        const nonce = await getNonce(address);
        const token = await login(address, nonce);
        setToken(token);
        localStorage.setItem("jwt", token);
    };

    const handleDisconnect = async () => {
        await disconnectWallet();
        setWalletAddress(null);
        setToken(null);
        localStorage.removeItem("jwt");
    };

    const formatAddress = (address: string) => {
        if (!address) return "";
        return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
    };

    return { walletAddress, token, handleConnect, handleDisconnect, formatAddress };
};
