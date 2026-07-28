import React from "react";

type Filter = { label: string; count: string };

type AssetFiltersProps = {
    filters: Filter[];
    activeFilter: string;
    setActiveFilter: (filter: string) => void;
};

export function AssetFilters({ filters, activeFilter, setActiveFilter }: AssetFiltersProps) {
    return (
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
    );
}
