"use client";

import { useState } from "react";
import { AssetCard } from "@/components/ui/assets/asset-card";
import { MOCK_ASSETS } from "@/components/ui/assets/mock-assets";
import { AssetFilters } from "@/components/ui/assets/asset-filters";
import { AssetSearch } from "@/components/ui/assets/asset-search";

const filters = [
    { label: "All", count: "4,812" },
    { label: "Verified", count: "4,761" },
    { label: "Flagged", count: "39" },
    { label: "Pending", count: "12" },
];

export default function AssetsPage() {
    const [activeFilter, setActiveFilter] = useState("All");
    const [searchQuery, setSearchQuery] = useState("");

    const filteredAssets = MOCK_ASSETS.filter((asset) => {
        const matchesStatus =
            activeFilter === "All" ||
            (activeFilter === "Flagged" && asset.status === "flagged") ||
            (activeFilter === "Verified" && asset.status === "minted");

        const matchesSearch =
            asset.hash.toLowerCase().includes(searchQuery.toLowerCase()) ||
            asset.id.toString().includes(searchQuery) ||
            asset.title.toLowerCase().includes(searchQuery.toLowerCase());

        return matchesStatus && matchesSearch;
    });

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
            <AssetFilters
                filters={filters}
                activeFilter={activeFilter}
                setActiveFilter={setActiveFilter}
            />

            <AssetSearch
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
            />
        </div>

        {/* Assets */}
        <div className="grid grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-4 mt-10">
            {filteredAssets.map((asset) => (
                <AssetCard key={asset.id} {...asset} />
            ))}
        </div>

    </main>);
}