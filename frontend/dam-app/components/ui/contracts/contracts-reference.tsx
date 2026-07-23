import { Square } from "lucide-react";

const contracts = [
    {
        id: 1,
        name: "DAMAsset.sol",
        subtitle: "ERC-721 mint & asset hash storage",
        description:
            "Every uploaded asset becomes a token here. The fusion hash computed by the hashing service is written at mint time, so the on-chain record and the off-chain perceptual signature are locked together from the first block.",
        verified: true,
        address: "0x8f2a...c14d",
        methods: [
            {
                signature: "mint(address to, bytes32 assetHash, string uri)",
                type: "write",
            },
            {
                signature: "assetHash(uint256 tokenId) returns (bytes32)",
                type: "read",
            },
            {
                signature: "ownerOf(uint256 tokenId) returns (address)",
                type: "read",
            },
        ],
    },
    {
        id: 2,
        name: "DAMSignature.sol",
        subtitle: "Fusion score attestation",
        description:
            "Holds the copy-probability score from the logistic regression fusion model against each token, signed by the registering address. This is the record a dispute gets resolved against.",
        verified: true,
        address: "0x3d91...7a02",
        methods: [
            {
                signature:
                    "registerSignature(uint256 tokenId, bytes32 fusionHash, uint16 copyProbabilityBps)",
                type: "write",
            },
            {
                signature: "getSignature(uint256 tokenId) returns (Signature)",
                type: "read",
            },
            {
                signature: "revoke(uint256 tokenId)",
                type: "write · owner only",
            },
        ],
    },
    {
        id: 3,
        name: "DAMVerifier.sol",
        subtitle: "Duplicate check, callable by anyone",
        description:
            "Takes any candidate hash and checks it against every registered signature, returning a confidence score. This is what a marketplace or collector queries before a purchase clears.",
        verified: true,
        address: "0xb607...f38e",
        methods: [
            {
                signature:
                    "verify(bytes32 candidateHash) returns (bool isDuplicate, uint16 confidenceBps, uint256 matchedTokenId)",
                type: "read",
            },
            {
                signature: "verifiedCount() returns (uint256)",
                type: "read",
            },
        ],
    },
];

export default function ContractsPage() {
    return (
        <div>
            <h2 className="font-fraunces mt-15 text-lg md:text-xl">
                CONTRACT REFERENCE
            </h2>

            <div className="space-y-5 mt-5">
                {contracts.map((contract) => (
                    <div
                        key={contract.id}
                        className="overflow-hidden rounded-2xl border border-stone-300 dark:border-zinc-700 bg-white dark:bg-zinc-950"
                    >
                        {/* Header */}
                        <div className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
                            <div className="flex items-center gap-4">
                                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-teal-50 dark:bg-teal-950">
                                    <Square className="h-5 w-5 text-teal-700 dark:text-teal-400" />
                                </div>

                                <div>
                                    <h2 className="font-fraunces text-lg md:text-2xl">
                                        {contract.name}
                                    </h2>

                                    <p className="text-sm text-stone-500 dark:text-stone-400">
                                        {contract.subtitle}
                                    </p>
                                </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                                {contract.verified && (
                                    <span className="rounded-full bg-teal-50 dark:bg-teal-950 px-3 py-1 text-xs font-mono text-teal-700 dark:text-teal-400">
                                        verified
                                    </span>
                                )}

                                <span className="rounded-md bg-stone-100 dark:bg-zinc-800 px-3 py-1 text-xs font-mono text-stone-600 dark:text-stone-400">
                                    {contract.address}
                                </span>
                            </div>
                        </div>

                        {/* Body */}
                        <div className="border-t border-stone-300 dark:border-zinc-700 p-5">
                            <p className="max-w-3xl text-sm leading-7 text-stone-600 dark:text-stone-300">
                                {contract.description}
                            </p>

                            <div className="mt-5 overflow-hidden rounded-lg border border-stone-300 dark:border-zinc-700">
                                {contract.methods.map((method, index) => (
                                    <div
                                        key={index}
                                        className={`flex flex-col gap-2 bg-stone-50 dark:bg-zinc-900 px-4 py-3 md:flex-row md:items-center md:justify-between ${index !== contract.methods.length - 1
                                            ? "border-b border-stone-300 dark:border-zinc-700"
                                            : ""
                                            }`}
                                    >
                                        <span className="break-all font-mono text-sm">
                                            {method.signature}
                                        </span>

                                        <span
                                            className={`text-xs font-mono uppercase tracking-wider ${method.type === "write"
                                                ? "text-amber-700 dark:text-amber-400"
                                                : "text-slate-500 dark:text-slate-400"
                                                }`}
                                        >
                                            {method.type}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}