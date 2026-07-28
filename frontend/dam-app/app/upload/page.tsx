"use client";

import FileUpload from "@/components/ui/upload/upload-file";

const steps = [
    { number: 1, label: "Upload" },
    { number: 2, label: "Hashing" },
    { number: 3, label: "Blockchain registration" },
    { number: 4, label: "Verification" },
];

export default function UploadPage() {
    const currentStep = 1;

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

                {/* <!-- Line --> */}
                <div className="relative flex justify-between">

                    <div className="absolute top-6 left-4 right-10 h-px bg-stone-300 dark:bg-stone-700"></div>

                    {steps.map((step) => {
                        const isActive = step.number <= currentStep;

                        return (
                            <div
                                key={step.number}
                                className="relative z-10 flex flex-col items-center"
                            >
                                <div
                                    className={`w-12 h-12 rounded-full flex items-center justify-center text-lg ${isActive
                                        ? "bg-teal-800 text-white"
                                        : "bg-white dark:bg-zinc-950 border border-stone-300 dark:border-stone-700 text-stone-600 dark:text-stone-400"
                                        }`}
                                >
                                    {step.number}
                                </div>
                                <p
                                    className={`mt-4 text-xl ${isActive ? "font-medium" : "text-stone-600 dark:text-stone-400"
                                        }`}
                                >
                                    {step.label}
                                </p>
                            </div>
                        );
                    })}

                </div>

            </div>
            <FileUpload
                onSubmit={async (files) => {
                    const formData = new FormData();
                    files.forEach((f) => formData.append("files", f));
                    await fetch("http://localhost:8001/hash", { method: "POST", body: formData });
                }}
            />
        </main>
    );
}