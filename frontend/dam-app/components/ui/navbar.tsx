"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useRef } from "react";

export default function Navbar() {
    const pathname = usePathname();
    const links = [
        { name: "Assets", href: "/assets" },
        { name: "Upload", href: "/upload" },
        { name: "Contracts", href: "/contracts" },
        { name: "How it works", href: "/how-it-works" },
    ];

    const [activeStyle, setActiveStyle] = useState<{
        left: number;
        width: number;
        opacity: number;
    }>({ left: 0, width: 0, opacity: 0 });
    const navRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const activeEl = navRef.current?.querySelector(`a[href="${pathname}"]`) as HTMLElement;
        if (activeEl) {
            setActiveStyle({ left: activeEl.offsetLeft, width: activeEl.offsetWidth, opacity: 1 });
        } else {
            setActiveStyle({ left: 0, width: 0, opacity: 0 });
        }
    }, [pathname]);

    return (
        <header className="p-4 sticky top-0 z-50">
            <nav className="mx-auto max-w-7xl flex items-center justify-between bg-white px-6 py-3 rounded-[10px] border border-gray-200 shadow-sm relative">
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-gray-200 rounded-sm"></div>
                    <Link href="/" className="text-xl font-bold">
                        <span className={`text-xl font-bold ${pathname === "/" ? "border-b-2 border-black" : ""}`}>DAM</span>
                    </Link>
                </div>
                <div className="flex items-center gap-8 text-sm font-medium text-gray-700 relative" ref={navRef}>
                    {links.map((link) => (
                        <Link
                            key={link.name}
                            href={link.href}
                            className={`py-1 transition-colors duration-300 ${pathname === link.href ? "text-black" : "hover:text-black"
                                }`}
                        >
                            {link.name}
                        </Link>
                    ))}
                    <span
                        className="absolute top-9.5 h-1.5 bg-black transition-all duration-300 ease-in-out"
                        style={{
                            left: `${activeStyle.left}px`,
                            width: `${activeStyle.width}px`,
                            opacity: activeStyle.opacity
                        }}
                    />
                </div>
                <button className="bg-gray-200 px-4 py-2 rounded-[10px] text-sm font-medium">
                    Connect Wallet
                </button>
            </nav>
        </header>
    );
}
