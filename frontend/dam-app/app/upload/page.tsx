"use client";

import { useState } from "react";
import FileUpload from "@/components/ui/upload/upload-file";
import { signPHash } from "@/lib/signature";
import { useWallet } from "@/hooks/useWallet";

const steps = [
    { number: 1, label: "Upload" },
    { number: 2, label: "Hashing" },
    { number: 3, label: "Sign" },
    { number: 4, label: "Blockchain" },
];

export default function UploadPage() {
    const [currentStep, setCurrentStep] = useState(1);
    const [hashingResult, setHashingResult] = useState<any>(null);
    const { walletAddress } = useWallet();

    const handleUploadSubmit = async (files: File[]) => {
        setCurrentStep(2);
        // Placeholder for step 1-2: Hashing
        const formData = new FormData();
        files.forEach((f) => formData.append("files", f));

        const response = await fetch(`${process.env.NEXT_PUBLIC_HASHING_SERVICE_URL}/hash`, {
            method: "POST",
            body: formData
        });
        const result = await response.json();
        setHashingResult(result);

        // Proceed to signing
        setCurrentStep(3);

        // Step 3: Sign (assuming result has the pHash)
        // Note: In real flow, you'd iterate over files.
        const pHash = result[0].hash;
        const signature = await signPHash(pHash);

        // Proceed to blockchain registration
        setCurrentStep(4);

        // Step 4: Register (Placeholder)
        console.log("Registering:", { pHash, signature, creator: walletAddress });
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
                <FileUpload onSubmit={handleUploadSubmit} />
            )}
            {currentStep > 1 && (
                <div className="text-center p-10">
                    <p className="text-2xl">Processing step {currentStep}...</p>
                </div>
            )}
        </main>
    );
}