import { useState, useEffect, useCallback } from "react";
import { connectWallet, getConnectedWallet, disconnectWallet, getNonce, login } from "@/lib/auth";
import {
    discoverProviders,
    selectProvider,
    rememberProviderChoice,
    EIP1193Provider,
    EIP6963ProviderDetail,
} from "@/lib/eip6963";

export const useWallet = () => {
    const [walletAddress, setWalletAddress] = useState<string | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [availableProviders, setAvailableProviders] = useState<EIP6963ProviderDetail[]>([]);
    const [activeProvider, setActiveProvider] = useState<EIP1193Provider | null>(null);

    // Discover installed wallet extensions once, then resolve which one to use.
    useEffect(() => {
        let cancelled = false;
        discoverProviders().then((providers) => {
            if (cancelled) return;
            setAvailableProviders(providers);
            setActiveProvider(selectProvider(providers));
        });
        return () => { cancelled = true; };
    }, []);

    useEffect(() => {
        if (!activeProvider) return;
        getConnectedWallet(activeProvider).then((address) => setWalletAddress(address || null));

        const savedToken = localStorage.getItem("jwt");
        if (savedToken) setToken(savedToken);
    }, [activeProvider]);

    useEffect(() => {
        if (!activeProvider?.on) return;

        const handleAccountsChanged = (accounts: string[]) => {
            if (accounts && accounts.length > 0) {
                setWalletAddress(accounts[0]);
            } else {
                setWalletAddress(null);
                setToken(null);
                localStorage.removeItem("jwt");
            }
        };

        activeProvider.on("accountsChanged", handleAccountsChanged);
        return () => activeProvider.removeListener?.("accountsChanged", handleAccountsChanged);
    }, [activeProvider]);

    // Exposed for a future wallet-picker UI -- not built yet, but the
    // plumbing to let a user explicitly choose among multiple wallets
    // is here rather than always silently auto-selecting.
    const selectWallet = useCallback((rdns: string) => {
        const match = availableProviders.find((p) => p.info.rdns === rdns);
        if (match) {
            rememberProviderChoice(rdns);
            setActiveProvider(match.provider);
        }
    }, [availableProviders]);

    const handleConnect = async () => {
        const address = await connectWallet(activeProvider);
        if (address) {
            setWalletAddress(address);
            handleLogin(address);
        }
    };

    const handleLogin = async (address: string) => {
        if (!activeProvider) return;
        const token = await login(activeProvider, address, await getNonce(address));
        setToken(token);
        localStorage.setItem("jwt", token);
    };

    const handleDisconnect = async () => {
        await disconnectWallet(activeProvider);
        setWalletAddress(null);
        setToken(null);
        localStorage.removeItem("jwt");
    };

    const formatAddress = (address: string) => {
        if (!address) return "";
        return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
    };

    return {
        walletAddress, token, handleConnect, handleDisconnect, formatAddress,
        availableProviders, selectWallet,
    };
};