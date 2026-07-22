import { ArrowDown, ArrowRight } from "lucide-react";

const data = [
    {
        title: "DAMAsset",
        description: "Mints the token and stores the fusion hash at time of upload.",
        number: "01",
    },
    {
        title: "DAMSignature",
        description: "Records the signed fusion score and the signer's address.",
        number: "02",
    },
    {
        title: "DAMVerifier",
        description: "Compares any candidate hash against the registry, on demand.",
        number: "03",
    },
];

export default function ContractsPage() {
    return (
        <div>
            <h2 className="font-fraunces mt-15 text-lg md:text-xl">
                HOW THE THREE CONTRACTS CONNECT
            </h2>

            <div className="w-full bg-white my-5 rounded-2xl border border-stone-300 p-8">
                <div className="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-8">
                    {data.map((item, index) => (
                        <div
                            key={item.number}
                            className="flex flex-col md:flex-row items-center gap-6"
                        >
                            <div className="flex flex-col items-center text-center gap-2 max-w-[220px]">
                                <div className="w-12 h-12 bg-stone-100 rounded-sm flex items-center justify-center">
                                    <span className="font-plex">{item.number}</span>
                                </div>

                                <h3 className="text-sm font-mono">{item.title}</h3>

                                <p className="text-sm text-gray-500">
                                    {item.description}
                                </p>
                            </div>

                            {index < data.length - 1 && (
                                <>
                                    {/* Mobile */}
                                    <ArrowDown className="w-5 h-5 text-stone-500 md:hidden" />

                                    {/* Desktop */}
                                    <ArrowRight className="hidden md:block w-6 h-6 text-stone-500" />
                                </>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}