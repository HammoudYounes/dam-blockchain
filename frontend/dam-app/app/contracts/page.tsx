import ContractsReference from "@/components/ui/contracts/contracts-reference";
import ExplanationFlow from "@/components/ui/contracts/explanation-flow";

export default function ContractsPage() {
    return (
        <main className="p-10 min-h-screen dark:text-white">
            <h1 className="text-4xl font-fraunces text-center mb-10">
                Three contracts, one chain of custody.
            </h1>
            <div className="w-full h-[1px] bg-gray-300 dark:bg-zinc-800" />
            <div className="flex flex-row gap-10 py-6">
                <div className="flex-1 flex flex-col gap-3">
                    <div className="text-gray-400 dark:text-stone-400 text-sm font-plex">Network</div>
                    <div className="flex flex-row items-center gap-2 font-fraunces text-lg">
                        <div className="w-3 h-3 bg-teal-800 rounded-full"></div>
                        <div>Polygon - Amoy</div>
                    </div>
                </div>
                <div className="flex-1 flex flex-col gap-3">
                    <div className="text-gray-400 dark:text-stone-400 text-sm font-plex">Contract deployed</div>
                    <div className="text-lg">3 / 3</div>
                </div>
                <div className="flex-1 flex flex-col gap-3">
                    <div className="text-gray-400 dark:text-stone-400 text-sm font-plex">Assets registered</div>
                    <div className="text-lg">55555</div>
                </div>
                <div className="flex-1 flex flex-col gap-3">
                    <div className="text-gray-400 dark:text-stone-400 text-sm font-plex">Verifications runs</div>
                    <div className="text-lg">77777</div>
                </div>
            </div>
            <div className="w-full h-[1px] bg-gray-300 dark:bg-zinc-800" />
            <ExplanationFlow />
            <ContractsReference />
        </main>
    );
}