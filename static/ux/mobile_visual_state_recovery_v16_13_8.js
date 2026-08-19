/* V16.13.8.1_MOBILE_VISUAL_STATE_RECOVERY_START */
(() => {
    "use strict";

    const root = document.documentElement;
    const body = document.body;

    if (!body) return;

    const DRAWER_KEY =
        "student-satisfaction-mobile-drawer-open";

    /*
     * Current mobile stack:
     * - V16.9  : v169-*
     * - V16.10 : v1610-drawer-settling may still live inside V16.9 assets
     * - V16.11 : v1611-* is the current static-canvas persistence layer
     *
     * V16.10.1 external assets were deliberately retired by V16.11.
     */
    const CLOSED_STATE_CLASSES = [
        "v169-drawer-preopen",
        "v169-navigation-lock",
        "v1610-drawer-settling",
        "v1611-drawer-preopen",
        "v1611-drawer-settling",
        "v1611-navigation-lock",
    ];

    const MOBILE_QUERY =
        "(max-width: 820px)";

    const isMobile = () => (
        window.matchMedia
        && window.matchMedia(
            MOBILE_QUERY
        ).matches
    );

    const drawerIsOpen = () => (
        body.classList.contains(
            "mobile-nav-open"
        )
    );

    const clearClosedStateClasses = () => {
        root.classList.remove(
            ...CLOSED_STATE_CLASSES
        );
    };

    const clearPersistedDrawer = () => {
        try {
            sessionStorage.removeItem(
                DRAWER_KEY
            );
        } catch (_) {
            /* UI persistence only. */
        }
    };

    const clearCanvasInlineResidue = () => {
        const canvas =
            document.querySelector(
                ".mobile-app-canvas"
            );

        if (!canvas) return;

        /*
         * The current CSS stack owns geometry.
         * Remove only inline state that could keep an old reduced card alive.
         */
        [
            "position",
            "top",
            "right",
            "bottom",
            "left",
            "width",
            "height",
            "min-height",
            "overflow",
            "overflow-x",
            "overflow-y",
            "transform",
            "transform-origin",
            "border-radius",
            "box-shadow",
            "pointer-events",
            "user-select",
            "visibility",
            "opacity",
        ].forEach((property) => {
            canvas.style.removeProperty(
                property
            );
        });

        canvas.scrollTop = 0;
    };

    const synchronizeClosedSemantics = () => {
        document
            .querySelector(
                "[data-mobile-drawer]"
            )
            ?.setAttribute(
                "aria-hidden",
                "true"
            );

        document
            .querySelector(
                "[data-mobile-menu-toggle]"
            )
            ?.setAttribute(
                "aria-expanded",
                "false"
            );
    };

    const clearUnexpectedSkipFocus = () => {
        const active =
            document.activeElement;

        if (
            active instanceof HTMLElement
            && active.classList.contains(
                "skip-link"
            )
        ) {
            active.blur();
        }
    };

    const notifyGeometry = () => {
        window.dispatchEvent(
            new Event("resize")
        );

        window.dispatchEvent(
            new CustomEvent(
                "v161381:closed-state-normalized"
            )
        );
    };

    const normalizeClosedState = () => {
        /*
         * Never own drawer open/close.
         * Only normalize AFTER the real V16 controller has closed it.
         */
        if (
            !isMobile()
            || drawerIsOpen()
        ) {
            return;
        }

        clearPersistedDrawer();
        clearClosedStateClasses();
        synchronizeClosedSemantics();
        clearCanvasInlineResidue();
        clearUnexpectedSkipFocus();

        requestAnimationFrame(() => {
            if (drawerIsOpen()) return;

            clearClosedStateClasses();
            clearCanvasInlineResidue();
            clearUnexpectedSkipFocus();

            requestAnimationFrame(() => {
                if (drawerIsOpen()) return;

                clearClosedStateClasses();
                clearCanvasInlineResidue();
                notifyGeometry();
            });
        });
    };

    const scheduleClosedNormalization = () => {
        queueMicrotask(
            normalizeClosedState
        );

        requestAnimationFrame(
            normalizeClosedState
        );

        window.setTimeout(
            normalizeClosedState,
            120
        );

        /*
         * V16.9/V16.11 contain small settling timers.
         * One final assertion after them prevents a stale reduced card.
         */
        window.setTimeout(
            normalizeClosedState,
            520
        );
    };

    document.addEventListener(
        "click",
        (event) => {
            if (
                event.target.closest(
                    "[data-mobile-menu-close]"
                )
            ) {
                scheduleClosedNormalization();
                return;
            }

            const toggle =
                event.target.closest(
                    "[data-mobile-menu-toggle]"
                );

            if (
                toggle
                && !drawerIsOpen()
            ) {
                scheduleClosedNormalization();
            }
        },
        false
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape"
            ) {
                scheduleClosedNormalization();
            }
        },
        false
    );

    /*
     * Body.mobile-nav-open is the source of truth.
     * When the existing controller removes it, normalize immediately.
     */
    const bodyObserver =
        new MutationObserver(
            (mutations) => {
                const changed =
                    mutations.some(
                        (mutation) => (
                            mutation.type
                                === "attributes"
                            && mutation.attributeName
                                === "class"
                        )
                    );

                if (
                    changed
                    && !drawerIsOpen()
                ) {
                    scheduleClosedNormalization();
                }
            }
        );

    bodyObserver.observe(
        body,
        {
            attributes: true,
            attributeFilter: [
                "class",
            ],
        }
    );

    /*
     * Same-document page/language work can finish after the close event.
     * Reassert only when the drawer is already closed.
     */
    [
        "v1613:navigated",
        "v16137:language-changed",
        "v16138:closed-state-normalized",
        "pageshow",
    ].forEach((eventName) => {
        window.addEventListener(
            eventName,
            () => {
                if (
                    !drawerIsOpen()
                ) {
                    scheduleClosedNormalization();
                }
            }
        );
    });

    normalizeClosedState();

    root.dataset.mobileVisualRecovery =
        "v16.13.8.1";
})();
/* V16.13.8.1_MOBILE_VISUAL_STATE_RECOVERY_END */
