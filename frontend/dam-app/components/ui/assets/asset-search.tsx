import React from "react";
import { Search } from "lucide-react";

type AssetSearchProps = {
    searchQuery: string;
    setSearchQuery: (query: string) => void;
};

export function AssetSearch({ searchQuery, setSearchQuery }: AssetSearchProps) {
    return (
        <div className="relative w-72">
            <Search
                size={18}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400"
            />
            <input
                type="text"
                placeholder="search by hash or id"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-full border border-zinc-300 py-2.5 pl-11 pr-4 text-sm outline-none focus:border-zinc-500"
            />
        </div>
    );
}
