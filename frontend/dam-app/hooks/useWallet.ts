import { useState, useEffect } from "react";
import { connectWallet, getConnectedWallet, disconnectWallet } from "@/lib/auth";

export const useWallet = () => {
    const [walletAddress, setWalletAddress] = useState<string | null>(null);

    useEffect(() => {
        const checkConnection = async () => {
            if (typeof window !== "undefined" && window.ethereum) {
                const address = await getConnectedWallet();
                setWalletAddress(address || null);
            }
        };
        checkConnection();
    }, []);

    useEffect(() => {
        if (typeof window === "undefined" || !window.ethereum) return;

        const ethereum = window.ethereum;

        const handleAccountsChanged = (accounts: string[]) => {
            if (accounts && accounts.length > 0) {
                setWalletAddress(accounts[0]);
            } else {
                setWalletAddress(null);
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
        }
    };

    const handleDisconnect = async () => {
        await disconnectWallet();
        setWalletAddress(null);
    };

    const formatAddress = (address: string) => {
        if (!address) return "";
        return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
    };

    return { walletAddress, handleConnect, handleDisconnect, formatAddress };
};
