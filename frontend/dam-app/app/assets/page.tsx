"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { AssetCard } from "@/components/ui/assets/asset-card";
import { MOCK_ASSETS } from "@/components/ui/assets/mock-assets";

const filters = [
    { label: "All", count: "4,812" },
    { label: "Verified", count: "4,761" },
    { label: "Flagged", count: "39" },
    { label: "Pending", count: "12" },
];

export default function AssetsPage() {
    const [activeFilter, setActiveFilter] = useState("All");

    return (<main className="p-10">
        <div className="text-7xl mt-2 font-fraunces font-medium">
            Find your next assets.
        </div>
        <div className="text-lg mt-4 font-mono w-1/2">
            Browse and search for assets that have been registered on the DAM.
        </div>
        <div className="flex justify-end gap-4 mt-10">
            <button className="px-4 py-2 rounded-lg bg-teal-800 text-white font-medium">
                Upload new asset
            </button>
        </div>
        {/* Filter */}
        <div className="flex items-center justify-between w-full mt-10">
            <div className="flex gap-3">
                {filters.map((item) => {
                    const isActive = item.label === activeFilter;
                    return (
                        <button
                            key={item.label}
                            className={`px-5 py-2 rounded-full border text-sm transition
              ${isActive
                                    ? "bg-zinc-900 text-white border-zinc-900"
                                    : "bg-white text-zinc-600 border-zinc-300 hover:border-zinc-400"
                                }`}
                            onClick={() => {
                                setActiveFilter(item.label);
                            }}
                        >
                            <span>{item.label}</span>
                            <span className="mx-2">·</span>
                            <span>{item.count}</span>
                        </button>
                    );
                })}
            </div>

            <div className="relative w-72">
                <Search
                    size={18}
                    className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400"
                />
                <input
                    type="text"
                    placeholder="search by hash or id"
                    className="w-full rounded-full border border-zinc-300 py-2.5 pl-11 pr-4 text-sm outline-none focus:border-zinc-500"
                />
            </div>
        </div>

        {/* Assets */}
        <div className="grid grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-4 mt-10">
            {MOCK_ASSETS.map((asset) => (
                <AssetCard key={asset.id} {...asset} />
            ))}
        </div>

    </main>);
}