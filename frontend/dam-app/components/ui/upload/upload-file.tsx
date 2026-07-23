"use client";

import { useCallback, useRef, useState } from "react";
import { Plus, File as FileIcon, X } from "lucide-react";

type QueuedFile = {
    id: string;
    file: File;
};

const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];
const MAX_SIZE_MB = 5;

function formatSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function FileUpload({ onSubmit }: { onSubmit?: (files: File[]) => void }) {
    const [queue, setQueue] = useState<QueuedFile[]>([]);
    const [dragActive, setDragActive] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const totalSize = queue.reduce((sum, q) => sum + q.file.size, 0);

    const addFiles = (fileList: FileList | File[]) => {
        const incoming = Array.from(fileList).filter((f) => {
            const validType = ACCEPTED_TYPES.includes(f.type);
            const validSize = f.size <= MAX_SIZE_MB * 1024 * 1024;
            return validType && validSize;
        });

        setQueue((prev) => [
            ...prev,
            ...incoming.map((file) => ({
                id: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
                file,
            })),
        ]);
    };

    const removeFile = (id: string) => {
        setQueue((prev) => prev.filter((q) => q.id !== id));
    };

    const handleDrag = useCallback((e: React.DragEvent, active: boolean) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(active);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
    }, []);

    const handleSubmit = async () => {
        if (queue.length === 0) return;
        setSubmitting(true);
        try {
            await onSubmit?.(queue.map((q) => q.file));
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="w-full mx-auto mt-10">
            <div className="grid grid-cols-2 gap-6">

                {/* Left panel - queued files */}
                <div className="border border-stone-300 dark:border-zinc-700 rounded-2xl bg-white dark:bg-zinc-950 flex flex-col overflow-hidden">
                    <div className="px-6 py-5 border-b border-stone-200 dark:border-zinc-700">
                        <p className="text-2xl font-fraunces">Files ready to register</p>
                        <p className="mt-1 text-sm font-mono text-stone-500 dark:text-stone-400">
                            {queue.length} file{queue.length === 1 ? "" : "s"} · {formatSize(totalSize)}
                        </p>
                    </div>

                    <div className="flex-1 min-h-[380px] flex flex-col">
                        {queue.length === 0 ? (
                            <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-10">
                                <FileIcon className="w-8 h-8 text-stone-400 dark:text-stone-500" strokeWidth={1.5} />
                                <p className="text-stone-500 dark:text-stone-400">
                                    Nothing queued yet - drop files on the right
                                </p>
                            </div>
                        ) : (
                            <ul className="divide-y divide-stone-100 dark:divide-zinc-800">
                                {queue.map((q) => (
                                    <li
                                        key={q.id}
                                        className="flex items-center justify-between px-6 py-3"
                                    >
                                        <div className="flex items-center gap-3 min-w-0">
                                            <FileIcon className="w-4 h-4 text-stone-400 dark:text-stone-500 shrink-0" />
                                            <span className="truncate">{q.file.name}</span>
                                            <span className="text-sm font-mono text-stone-400 dark:text-stone-500 shrink-0">
                                                {formatSize(q.file.size)}
                                            </span>
                                        </div>
                                        <button
                                            onClick={() => removeFile(q.id)}
                                            className="text-stone-400 dark:text-stone-500 hover:text-stone-700 dark:hover:text-stone-300 shrink-0"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                </div>

                {/* Right panel - dropzone */}
                <div
                    onDragEnter={(e) => handleDrag(e, true)}
                    onDragOver={(e) => handleDrag(e, true)}
                    onDragLeave={(e) => handleDrag(e, false)}
                    onDrop={handleDrop}
                    onClick={() => inputRef.current?.click()}
                    className={`cursor-pointer border rounded-2xl min-h-[380px] flex flex-col items-center justify-center gap-4 text-center transition-colors ${dragActive
                        ? "border-teal-800 bg-teal-50 dark:bg-teal-950"
                        : "border-stone-300 dark:border-zinc-700 bg-white dark:bg-zinc-950"
                        }`}
                >
                    <input
                        ref={inputRef}
                        type="file"
                        multiple
                        accept={ACCEPTED_TYPES.join(",")}
                        className="hidden"
                        onChange={(e) => {
                            if (e.target.files?.length) addFiles(e.target.files);
                            e.target.value = "";
                        }}
                    />

                    <div className="w-14 h-14 rounded-full border border-dashed border-stone-400 dark:border-zinc-500 flex items-center justify-center">
                        <Plus className="w-5 h-5 text-stone-500 dark:text-stone-400" />
                    </div>

                    <p className="text-lg">
                        Drag &amp; drop{" "}
                        <span
                            className="underline"
                            onClick={(e) => {
                                e.stopPropagation();
                                inputRef.current?.click();
                            }}
                        >
                            or click to open folder
                        </span>
                    </p>

                    <p className="text-sm font-mono text-stone-500 dark:text-stone-400">
                        PNG, JPG, GIF, WEBP · up to {MAX_SIZE_MB}MB each
                    </p>
                </div>

            </div>

            {/* Submit */}
            <div className="mt-8 flex justify-center">
                <button
                    onClick={handleSubmit}
                    disabled={queue.length === 0 || submitting}
                    className={`px-8 py-3 rounded-full text-lg font-medium transition-colors ${queue.length === 0 || submitting
                        ? "bg-stone-300 dark:bg-zinc-700 text-white dark:text-stone-400 cursor-not-allowed"
                        : "bg-teal-800 text-white hover:bg-teal-900"
                        }`}
                >
                    {submitting ? "Submitting…" : "Submit for hashing"}
                </button>
            </div>
        </div>
    );
}