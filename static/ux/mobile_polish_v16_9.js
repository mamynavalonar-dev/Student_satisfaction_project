
/* V16.9_MOBILE_POLISH_START */
(() => {
    "use strict";

    const root = document.documentElement;
    const body = document.body;
    const DRAWER_KEY =
        "student-satisfaction-mobile-drawer-open";
    const MOBILE_QUERY = "(max-width: 820px)";

    if (!body) return;

    const isMobile = () => (
        window.matchMedia
        && window.matchMedia(MOBILE_QUERY).matches
    );

    const drawerShouldPersist = () => {
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

    const alignFloatingCardNow = () => {
        const drawer = document.querySelector(
            "[data-mobile-drawer]"
        );
        const firstItem = drawer?.querySelector(
            ".mobile-drawer-nav .mobile-drawer-link"
        );

        if (!drawer || !firstItem) return;

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

    const finishPreopenRestore = () => {
        if (
            !root.classList.contains(
                "v169-drawer-preopen"
            )
        ) {
            return;
        }

        alignFloatingCardNow();
        body.classList.add("mobile-nav-open");

        const toggle = document.querySelector(
            "[data-mobile-menu-toggle]"
        );
        const drawer = document.querySelector(
            "[data-mobile-drawer]"
        );

        toggle?.setAttribute(
            "aria-expanded",
            "true"
        );
        drawer?.setAttribute(
            "aria-hidden",
            "false"
        );

        window.requestAnimationFrame(() => {
            alignFloatingCardNow();

            window.requestAnimationFrame(() => {
                root.classList.remove(
                    "v169-drawer-preopen"
                );
                root.classList.remove(
                    "v169-navigation-lock"
                );
            });
        });
    };

    document.addEventListener(
        "pointerdown",
        (event) => {
            const link = event.target.closest(
                "[data-mobile-drawer] a[href]"
            );

            if (!link || !isMobile()) return;

            root.classList.add(
                "v169-navigation-lock"
            );

            try {
                sessionStorage.setItem(
                    DRAWER_KEY,
                    "1"
                );
            } catch (_) {
                /* Visual enhancement only. */
            }
        },
        {
            capture: true,
            passive: true,
        }
    );

    window.addEventListener(
        "pageshow",
        () => {
            if (drawerShouldPersist()) {
                root.classList.add(
                    "v169-drawer-preopen"
                );
                finishPreopenRestore();
            } else {
                root.classList.remove(
                    "v169-drawer-preopen",
                    "v169-navigation-lock"
                );
            }
        }
    );

    if (
        root.classList.contains(
            "v169-drawer-preopen"
        )
        || drawerShouldPersist()
    ) {
        root.classList.add(
            "v169-drawer-preopen"
        );
        finishPreopenRestore();
    }

    window.setTimeout(
        () => {
            root.classList.remove(
                "v169-drawer-preopen",
                "v169-navigation-lock"
            );
        },
        1200
    );
})();
/* V16.9_MOBILE_POLISH_END */
