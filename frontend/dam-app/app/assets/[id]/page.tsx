import Image from "next/image";
import { StatusBadge } from "@/components/ui/assets/asset-card";
import { MOCK_ASSETS } from "@/components/ui/assets/mock-assets";
import { truncateHash } from "@/utils/format";
import { ArrowLeft } from "lucide-react";
import { BackButton } from "@/components/ui/back-button";


export default async function AssetPage({ params }: { params: Promise<{ id: string }> }) {
    const { id: assetId } = await params;

    const asset = MOCK_ASSETS.find((asset) => asset.id.toString() === assetId);

    if (!asset) {
        return (
            <main className="p-10">
                <div className="text-7xl mt-2 font-fraunces font-medium">
                    Asset Not Found
                </div>
                <div className="text-lg mt-4 font-mono w-1/2">
                    No asset found with ID: {assetId}
                </div>
            </main>
        );
    }

    return (
        <main className="p-10">
            <div>
                <BackButton children={"Back to Assets"} />
            </div>
            <div className="text-7xl mt-2 font-fraunces font-medium">
                Asset Details
            </div>
            <div className="text-lg mt-4 font-mono w-1/2">
                Details for asset with ID: {assetId}
            </div>
            <div className="flex justify-start gap-4 mt-10">
                <Image
                    src={asset.imageSrc || "https://placehold.co/600x400"}
                    alt={asset.title || "Asset Image"}
                    width={600}
                    height={400}
                    unoptimized
                    loading="eager"
                />
            </div>
            <div className="mt-10 font-mono w-1/2 space-y-2">
                <div className="flex w-full items-center justify-between gap-4">
                    <div className="text-xl font-medium font-plex">Title: {asset.title}</div>
                    <StatusBadge status={asset.status} />
                </div>
                <div className="text-lg">Category: {asset.category}</div>
                <div className="text-lg truncate-hash">Hash: <a className="underline" href={`https://etherscan.io/tx/${asset.hash}`} target="_blank" rel="noopener noreferrer">{truncateHash(asset.hash)}</a></div>
                <div className="text-lg">Date: {asset.date}</div>
            </div>
        </main>
    );
}