export function truncateHash(
    hash: string | undefined,
    start = 14,
    end = 4
): string {
    if (!hash) return "";

    return `${hash.slice(0, start)}...${hash.slice(-end)}`;
}