"use client";

export interface EIP1193Provider {
    request: (args: { method: string; params?: any[] }) => Promise<any>;
    on?: (event: string, callback: (...args: any[]) => void) => void;
    removeListener?: (event: string, callback: (...args: any[]) => void) => void;
    isMetaMask?: boolean;
}

export interface EIP6963ProviderInfo {
    uuid: string;
    name: string;
    icon: string;
    rdns: string;
}

export interface EIP6963ProviderDetail {
    info: EIP6963ProviderInfo;
    provider: EIP1193Provider;
}

const STORAGE_KEY = "dam-selected-wallet-rdns";

/**
 * Collects every wallet extension that announces itself via EIP-6963
 * (MetaMask, Coinbase Wallet, Rabby, Brave Wallet, etc. all support this).
 * Replaces reading `window.ethereum` directly, which is ambiguous the
 * moment more than one wallet extension is installed -- whichever one
 * "wins" that global is effectively arbitrary, and some wallets throw
 * when they detect a competing provider trying to claim it too.
 */
export function discoverProviders(timeoutMs = 300): Promise<EIP6963ProviderDetail[]> {
    return new Promise((resolve) => {
        if (typeof window === "undefined") {
            resolve([]);
            return;
        }

        const providers = new Map<string, EIP6963ProviderDetail>();

        const onAnnouncement = (event: Event) => {
            const detail = (event as CustomEvent<EIP6963ProviderDetail>).detail;
            if (detail?.info?.uuid) {
                providers.set(detail.info.uuid, detail);
            }
        };

        window.addEventListener("eip6963:announceProvider", onAnnouncement);
        // Ask every installed wallet to (re-)announce itself.
        window.dispatchEvent(new Event("eip6963:requestProvider"));

        setTimeout(() => {
            window.removeEventListener("eip6963:announceProvider", onAnnouncement);
            resolve(Array.from(providers.values()));
        }, timeoutMs);
    });
}

/**
 * Picks which provider to use when more than one wallet is installed.
 * Preference order: a previously-remembered choice (by rdns) > MetaMask
 * specifically (the rest of the app is built/tested against it) > whatever
 * was discovered first > window.ethereum as a last resort for wallets
 * that don't support EIP-6963 yet.
 */
export function selectProvider(providers: EIP6963ProviderDetail[]): EIP1193Provider | null {
    if (typeof window === "undefined") return null;

    if (providers.length > 0) {
        const remembered = localStorage.getItem(STORAGE_KEY);
        const rememberedMatch = remembered && providers.find((p) => p.info.rdns === remembered);
        if (rememberedMatch) return rememberedMatch.provider;

        const metamask = providers.find((p) => p.info.rdns === "io.metamask");
        if (metamask) return metamask.provider;

        return providers[0].provider;
    }

    return window.ethereum ?? null;
}

export function rememberProviderChoice(rdns: string) {
    if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, rdns);
    }
}