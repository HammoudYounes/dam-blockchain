import { useState, useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

export const useActiveLink = () => {
    const pathname = usePathname();
    const [activeStyle, setActiveStyle] = useState<{
        left: number;
        width: number;
        opacity: number;
    }>({ left: 0, width: 0, opacity: 0 });
    const navRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const activeEl = navRef.current?.querySelector(`a[href="${pathname}"]`) as HTMLElement;
        if (activeEl) {
            setActiveStyle({ left: activeEl.offsetLeft, width: activeEl.offsetWidth, opacity: 1 });
        } else {
            setActiveStyle({ left: 0, width: 0, opacity: 0 });
        }
    }, [pathname]);

    return { navRef, activeStyle };
};
