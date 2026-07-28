"use client";

import { ArrowLeft } from "lucide-react";

export function BackButton({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex items-center gap-2 text-black-200/80 hover:text-black-200 cursor-pointer" onClick={() => window.history.back()}>
            <ArrowLeft className="inline-block w-6 h-6 mr-2" />
            <span className="ml-2 text-lg font-mono cursor-pointer">
                {children}
            </span>
        </div>
    );
}
