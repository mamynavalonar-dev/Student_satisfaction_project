/* V16.11_STATIC_MOBILE_CANVAS_START */
(() => {
    "use strict";

    const root = document.documentElement;
    const body = document.body;

    if (!body) return;

    const DRAWER_KEY =
        "student-satisfaction-mobile-drawer-open";

    const MOBILE_QUERY =
        "(max-width: 820px)";

    const isMobile = () => (
        window.matchMedia
        && window.matchMedia(MOBILE_QUERY).matches
    );

    const shouldRestore = () => {
        if (!isMobile()) return false;

        try {
            return (
                sessionStorage.getItem(DRAWER_KEY)
                === "1"
            );
        } catch (_) {
            return false;
        }
    };

    const syncCardTop = () => {
        const firstItem = document.querySelector(
            "[data-mobile-drawer] "
            + ".mobile-drawer-nav "
            + ".mobile-drawer-link"
        );

        if (!firstItem) return;

        const top = Math.max(
            0,
            Math.round(
                firstItem.getBoundingClientRect().top
            )
        );

        root.style.setProperty(
            "--mobile-card-top",
            `${top}px`
        );
    };

    const forceOpenSemantics = () => {
        body.classList.add(
            "mobile-nav-open"
        );

        document
            .querySelector("[data-mobile-menu-toggle]")
            ?.setAttribute(
                "aria-expanded",
                "true"
            );

        document
            .querySelector("[data-mobile-drawer]")
            ?.setAttribute(
                "aria-hidden",
                "false"
            );
    };

    const finishServerCanvasRestore = () => {
        if (!shouldRestore()) {
            root.classList.remove(
                "v1611-drawer-preopen",
                "v1611-drawer-settling",
                "v1611-navigation-lock"
            );
            return;
        }

        /*
         * No canvas creation is needed anymore: it is already present in
         * base.html. We only synchronize semantic/body state.
         */
        syncCardTop();
        forceOpenSemantics();

        root.classList.add(
            "v1611-drawer-settling"
        );

        requestAnimationFrame(() => {
            syncCardTop();

            requestAnimationFrame(() => {
                /*
                 * body.mobile-nav-open now describes the same geometry as
                 * v1611-drawer-preopen; removing the early class is invisible.
                 */
                root.classList.remove(
                    "v1611-drawer-preopen",
                    "v1611-navigation-lock"
                );

                window.setTimeout(() => {
                    root.classList.remove(
                        "v1611-drawer-settling"
                    );
                }, 80);
            });
        });
    };

    /* Lock the already-reduced old document before following a drawer link. */
    document.addEventListener(
        "pointerdown",
        (event) => {
            const link = event.target.closest(
                "[data-mobile-drawer] a[href]"
            );

            if (!link || !isMobile()) {
                return;
            }

            try {
                sessionStorage.setItem(
                    DRAWER_KEY,
                    "1"
                );
            } catch (_) {
                /* Visual persistence is optional. */
            }

            root.classList.add(
                "v1611-navigation-lock"
            );
        },
        {
            capture: true,
            passive: true,
        }
    );

    /*
     * Existing V16 may set body.mobile-nav-open later as well. That is safe
     * because the server canvas is already at the same transform.
     */
    finishServerCanvasRestore();

    window.addEventListener(
        "pageshow",
        finishServerCanvasRestore
    );

    window.addEventListener(
        "resize",
        () => {
            if (
                body.classList.contains(
                    "mobile-nav-open"
                )
                || root.classList.contains(
                    "v1611-drawer-preopen"
                )
            ) {
                syncCardTop();
            }
        },
        { passive: true }
    );
})();
/* V16.11_STATIC_MOBILE_CANVAS_END */
