"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useWallet } from "@/hooks/useWallet";
import { useActiveLink } from "@/hooks/useActiveLink";

export default function Navbar() {
    const pathname = usePathname();
    const links = [
        { name: "Assets", href: "/assets" },
        { name: "Upload", href: "/upload" },
        { name: "Contracts", href: "/contracts" },
        { name: "How it works", href: "/how-it-works" },
    ];

    const { walletAddress, handleConnect, handleDisconnect, formatAddress } = useWallet();
    const { navRef, activeStyle } = useActiveLink();

    return (
        <header className="p-4 sticky top-0 z-50">
            <nav className="mx-auto max-w-7xl flex items-center justify-between bg-white dark:bg-zinc-950 px-6 py-3 rounded-[10px] border border-gray-200 dark:border-zinc-800 shadow-sm relative">
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-gray-200 dark:bg-zinc-800 rounded-sm"></div>
                    <Link href="/" className="text-xl font-bold">
                        <span className={`text-xl font-bold ${pathname === "/" ? "border-b-2 border-black dark:border-white" : ""}`}>DAM</span>
                    </Link>
                </div>
                <div className="flex items-center gap-8 text-sm font-medium text-gray-700 dark:text-zinc-300 relative" ref={navRef}>
                    {links.map((link) => (
                        <Link
                            key={link.name}
                            href={link.href}
                            className={`py-1 transition-colors duration-300 ${pathname === link.href ? "text-black dark:text-white" : "hover:text-black dark:hover:text-white"
                                }`}
                        >
                            {link.name}
                        </Link>
                    ))}
                    <span
                        className="absolute top-9.5 h-1.5 bg-black dark:bg-white transition-all duration-300 ease-in-out"
                        style={{
                            left: `${activeStyle.left}px`,
                            width: `${activeStyle.width}px`,
                            opacity: activeStyle.opacity
                        }}
                    />
                </div>
                {walletAddress ? (
                    <div className="flex items-center gap-3">
                        <span className="text-sm font-medium bg-gray-100 dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 px-3 py-1.5 rounded-[10px] font-mono">
                            {formatAddress(walletAddress)}
                        </span>
                        <div className="flex flex-col items-end gap-1">
                            <button
                                className="bg-red-500 hover:bg-red-600 text-white dark:bg-red-600 dark:hover:bg-red-700 px-4 py-2 rounded-[10px] text-sm font-medium transition-colors"
                                onClick={() => {
                                    if (confirm("Disconnect session? (Note: Wallet access remains authorized in your wallet until you manually disconnect it there.)")) {
                                        handleDisconnect();
                                    }
                                }}
                            >
                                Disconnect
                            </button>
                        </div>
                    </div>
                ) : (
                    <button
                        className="bg-gray-200 dark:bg-zinc-800 hover:bg-gray-300 dark:hover:bg-zinc-700 px-4 py-2 rounded-[10px] text-sm font-medium transition-colors"
                        onClick={handleConnect}
                    >
                        Connect Wallet
                    </button>
                )}
            </nav>
        </header>
    );
}
