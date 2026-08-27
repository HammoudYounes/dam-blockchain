"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import FileUpload from "@/components/ui/upload/upload-file";
import { useWallet } from "@/hooks/useWallet";
import { MintNftDto } from "@/types/MintNftDto";

const steps = [
    { number: 1, label: "Upload" },
    { number: 2, label: "Hashing" },
    { number: 3, label: "Blockchain" },
];

function ProcessingIndicator({ step }: { step: number }) {
    const [dots, setDots] = useState(".");

    useEffect(() => {
        const interval = setInterval(() => {
            setDots((prev) => (prev.length >= 3 ? "." : prev + "."));
        }, 500);
        return () => clearInterval(interval);
    }, []);

    return <p className="text-2xl">Processing step {step}{dots}</p>;
}

export default function UploadPage() {
    const [currentStep, setCurrentStep] = useState(1);
    const [hashingResult, setHashingResult] = useState<any>(null);
    const [mintingResult, setMintingResult] = useState<any>(null);
    const { walletAddress, handleConnect } = useWallet();

    const handleUploadSubmit = async (files: File[]) => {
        if (!walletAddress) {
            alert("Please connect your wallet to upload.");
            return;
        }

        setCurrentStep(2);
        // Step 1: Upload files to the backend for hashing
        const formData = new FormData();
        files.forEach((f) => formData.append("files", f));

        let result;
        try {
            const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/image/upload`, formData, {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('jwt')}`
                }
            });

            result = response.data;
            console.log("Hashing result:", result);
            setHashingResult(result);

            if (result[0]?.isDuplicate) {
                alert("This image is a duplicate of an existing asset and cannot be minted.");
                setCurrentStep(1);
                return;
            }
        } catch (error: any) {
            if (error.response && error.response.status === 401) {
                alert("Session expired. Please reconnect your wallet.");
                setCurrentStep(1);
                return;
            }
            console.error(error);
            alert("An error occurred during upload. Please try again.");
            setCurrentStep(1);
            return;
        }

        // Proceed to minting
        setCurrentStep(3);

        // Mint
        try {

            // Build MintNftDto
            const mintDto: MintNftDto = {
                imageUri: result[0].imageUri,
                creator: walletAddress,
            };

            const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/nft/mint`, mintDto, {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('jwt')}`
                }
            });

            setMintingResult(response.data);
        } catch (error) {
            console.error("Minting failed:", error);
            alert("Minting failed.");
            setCurrentStep(2);
        }
    };

    return (
        <main className="p-10 dark:text-white">
            <div className="flex items-center gap-4">
                <div className="w-3 h-3 bg-teal-800 rounded-full"></div>
                <div className="text-xl font-plex">NEW ASSET</div>
            </div>
            <div className="text-7xl mt-2 font-fraunces font-medium">
                Register a new asset.
            </div>
            <div className="text-lg mt-4 font-mono w-1/2 text-stone-600 dark:text-stone-400">
                Files are hashed with all six perceptual algorithms, checked against the index,
                then anchored on-chain.
            </div>
            <div className="w-full max-w-5xl mx-auto py-10">
                <div className="relative flex justify-between">
                    <div className="absolute top-6 left-4 right-10 h-px bg-stone-300 dark:bg-stone-700"></div>
                    {steps.map((step) => {
                        const isActive = step.number <= currentStep;
                        return (
                            <div key={step.number} className="relative z-10 flex flex-col items-center">
                                <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg ${isActive ? "bg-teal-800 text-white" : "bg-white dark:bg-zinc-950 border border-stone-300 dark:border-stone-700 text-stone-600 dark:text-stone-400"}`}>
                                    {step.number}
                                </div>
                                <p className={`mt-4 text-xl ${isActive ? "font-medium" : "text-stone-600 dark:text-stone-400"}`}>
                                    {step.label}
                                </p>
                            </div>
                        );
                    })}
                </div>
            </div>
            {currentStep === 1 && (
                walletAddress ? (
                    <div className="flex flex-col gap-4">
                        <FileUpload onSubmit={handleUploadSubmit} />
                    </div>
                ) : (
                    <div className="text-center p-10 border border-dashed rounded-lg">
                        <p className="text-xl mb-4">Please connect your wallet to start uploading.</p>
                        <button
                            className="bg-gray-200 dark:bg-zinc-800 hover:bg-gray-300 dark:hover:bg-zinc-700 px-6 py-3 rounded-[10px] text-sm font-medium transition-colors"
                            onClick={handleConnect}
                        >
                            Connect Wallet
                        </button>
                    </div>
                )
            )}
            {currentStep > 1 && !mintingResult && (
                <div className="text-center p-10">
                    <ProcessingIndicator step={currentStep} />
                </div>
            )}
            {mintingResult && (
                <div className="text-center p-10 border border-teal-800 dark:border-teal-500 rounded-lg bg-teal-50/50 dark:bg-teal-900/10">
                    <p className="text-2xl text-teal-800 dark:text-teal-300 font-medium">NFT minted successfully!</p>
                    <div className="mt-4 text-left font-mono text-stone-700 dark:text-stone-300">
                        <p>
                            <strong>Token URI:</strong>{" "}
                            <a 
                                href={mintingResult.uri} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-teal-800 dark:text-teal-400 hover:underline"
                            >
                                {mintingResult.uri}
                            </a>
                        </p>
                        <p className="mt-2">
                            <strong>Transaction Hash:</strong>{" "}
                            <a 
                                href={`https://amoy.polygonscan.com/tx/${mintingResult.txHash}`} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-teal-800 dark:text-teal-400 hover:underline"
                            >
                                {mintingResult.txHash}
                            </a>
                        </p>
                    </div>
                </div>
            )}
        </main>
    );
}

