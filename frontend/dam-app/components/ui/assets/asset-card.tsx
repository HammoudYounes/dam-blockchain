import Image from "next/image";

export type AssetStatus = "minted" | "flagged";

export type AssetCardProps = {
    category: string;
    title: string;
    hash: string;
    id: string | number;
    date: string;
    status: AssetStatus;
    imageSrc?: string;
};

const STATUS_STYLES: Record<AssetStatus, string> = {
    minted: "border-emerald-400/50 text-emerald-300 bg-emerald-400/10",
    flagged: "border-amber-400/50 text-amber-300 bg-amber-400/10",
};

const STATUS_LABEL: Record<AssetStatus, string> = {
    minted: "MINTED",
    flagged: "FLAGGED",
};

function StatusBadge({ status }: { status: AssetStatus }) {
    return (
        <span
            className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-medium tracking-wide font-mono ${STATUS_STYLES[status]}`}
        >
            {STATUS_LABEL[status]}
        </span>
    );
}

export function AssetCard({
    category,
    title,
    hash,
    id,
    date,
    status,
    imageSrc = "https://placehold.co/600x400",
}: AssetCardProps) {
    return (
        <div className="group relative aspect-square overflow-hidden rounded-xl bg-neutral-200">
            <Image
                src={imageSrc}
                alt={category}
                fill
                sizes="(min-width: 1024px) 25vw, (min-width: 640px) 50vw, 100vw"
                className="object-cover"
                unoptimized
            />

            <div className="absolute inset-x-0 bottom-0 bg-neutral-500/50 p-3 backdrop-blur-md transition-colors duration-300">
                <div className="flex items-start justify-between gap-2">
                    <h3 className="line-clamp-1 text-base font-medium leading-snug text-white">
                        {title}
                    </h3>
                    <StatusBadge status={status} />
                </div>

                <div className="grid grid-rows-[0fr] transition-[grid-template-rows] duration-300 ease-out group-hover:grid-rows-[1fr]">
                    <div className="overflow-hidden">
                        <div className="translate-y-1 space-y-2 pt-3 opacity-0 transition-all duration-300 ease-out group-hover:translate-y-0 group-hover:opacity-100">
                            <p className="truncate font-mono text-xs text-neutral-200/80">
                                {hash}
                            </p>

                            <div className="flex items-center justify-between text-xs text-neutral-200/80">
                                <span className="font-mono">#{id}</span>
                                <span>{date}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}