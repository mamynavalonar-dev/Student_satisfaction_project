(() => {
    "use strict";

    const MOBILE_QUERY = "(max-width: 820px)";
    // V16.7_DRAWER_PERSISTENCE
    const MOBILE_DRAWER_OPEN_KEY = "student-satisfaction-mobile-drawer-open";

    function initMobileNavigation() {
        const body = document.body;
        const drawer = document.querySelector("[data-mobile-drawer]");
        const toggle = document.querySelector("[data-mobile-menu-toggle]");
        const close = document.querySelector("[data-mobile-menu-close]");
        const scrim = document.querySelector("[data-mobile-nav-scrim]");

        if (!body || !drawer || !toggle || !close || !scrim) {
            return;
        }

        const media = window.matchMedia(MOBILE_QUERY);
        let previouslyFocused = null;

        const focusableSelector = [
            "a[href]",
            "button:not([disabled])",
            "input:not([disabled])",
            "select:not([disabled])",
            "textarea:not([disabled])",
            "[tabindex]:not([tabindex='-1'])",
        ].join(",");

        const setState = (open, { restoreFocus = true } = {}) => {
            if (open && !media.matches) return;

            body.classList.toggle("mobile-nav-open", open);
            try {
                if (open) {
                    sessionStorage.setItem(
                        MOBILE_DRAWER_OPEN_KEY,
                        "1"
                    );
                } else {
                    sessionStorage.removeItem(
                        MOBILE_DRAWER_OPEN_KEY
                    );
                }
            } catch (_) {
                /* Storage can be unavailable in private contexts. */
            }

            toggle.setAttribute("aria-expanded", String(open));
            drawer.setAttribute("aria-hidden", String(!open));

            if (open) {
                previouslyFocused = document.activeElement;
                window.requestAnimationFrame(() => close.focus());
                return;
            }

            if (
                restoreFocus &&
                previouslyFocused instanceof HTMLElement &&
                document.contains(previouslyFocused)
            ) {
                previouslyFocused.focus({ preventScroll: true });
            }
        };

        const isOpen = () => body.classList.contains("mobile-nav-open");

        toggle.addEventListener("click", () => {
            setState(!isOpen());
        });

        close.addEventListener("click", () => {
            setState(false);
        });

        scrim.addEventListener("click", () => {
            setState(false);
        });
        const keepDrawerOpenAcrossNavigation = (event) => {
            const link = event.target.closest("a[href]");
            if (!link) return;

            try {
                sessionStorage.setItem(
                    MOBILE_DRAWER_OPEN_KEY,
                    "1"
                );
            } catch (_) {
                /* Ignore unavailable session storage. */
            }
        };

        drawer.addEventListener(
            "click",
            keepDrawerOpenAcrossNavigation
        );

        drawer.addEventListener("keydown", (event) => {
            if (event.key !== "Tab" || !isOpen()) return;

            const focusable = Array.from(
                drawer.querySelectorAll(focusableSelector)
            ).filter((element) => {
                return (
                    element instanceof HTMLElement &&
                    !element.hasAttribute("hidden") &&
                    element.offsetParent !== null
                );
            });

            if (!focusable.length) return;

            const first = focusable[0];
            const last = focusable[focusable.length - 1];

            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (
                !event.shiftKey &&
                document.activeElement === last
            ) {
                event.preventDefault();
                first.focus();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && isOpen()) {
                event.preventDefault();
                setState(false);
            }
        });

        const mediaChanged = (event) => {
            if (!event.matches && isOpen()) {
                setState(false, { restoreFocus: false });
            }
        };

        if (typeof media.addEventListener === "function") {
            media.addEventListener("change", mediaChanged);
        } else if (typeof media.addListener === "function") {
            media.addListener(mediaChanged);
        }

        document
            .querySelectorAll("[data-mobile-theme-cycle]")
            .forEach((button) => {
                button.addEventListener("click", () => {
                    const desktopToggle = document.querySelector(
                        "[data-theme-toggle]"
                    );

                    if (desktopToggle instanceof HTMLElement) {
                        desktopToggle.click();
                    }
                });
            });

        document
            .querySelectorAll("[data-mobile-bottom-link]")
            .forEach((link) => {
                if (link.classList.contains("is-active")) {
                    link.setAttribute("aria-current", "page");
                }
            });

        document
            .querySelectorAll("[data-mobile-drawer-link]")
            .forEach((link) => {
                if (link.classList.contains("is-active")) {
                    link.setAttribute("aria-current", "page");
                }
            });

        drawer.setAttribute("aria-hidden", "true");
        toggle.setAttribute("aria-expanded", "false");

        const restorePersistedDrawerState = () => {
            let shouldRestore = false;

            try {
                shouldRestore = (
                    sessionStorage.getItem(
                        MOBILE_DRAWER_OPEN_KEY
                    ) === "1"
                );
            } catch (_) {
                shouldRestore = false;
            }

            if (shouldRestore && media.matches) {
                window.requestAnimationFrame(() => {
                    setState(
                        true,
                        { restoreFocus: false }
                    );
                });
            }
        };

        restorePersistedDrawerState();
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initMobileNavigation,
            { once: true }
        );
    } else {
        initMobileNavigation();
    }
})();

/* V16.2_REFERENCE_CANVAS
   Build one application canvas so the whole page shrinks/slides as one object. */
(() => {
    "use strict";

    const buildMobileAppCanvas = () => {
        if (document.querySelector(".mobile-app-canvas")) return;

        const header = document.querySelector(".page-header");
        const nav = document.querySelector(".nav-container");
        const toast = document.querySelector(".app-toast-region");
        const main = document.querySelector("main.main-content");
        const footer = document.querySelector("footer");
        const skip = document.querySelector(".skip-link");

        if (!header || !main || !footer) return;

        const canvas = document.createElement("div");
        canvas.className = "mobile-app-canvas";
        canvas.setAttribute("data-mobile-app-canvas", "");

        const first = skip || header;
        first.parentNode.insertBefore(canvas, first);

        [skip, header, nav, toast, main, footer]
            .filter(Boolean)
            .forEach((node) => canvas.appendChild(node));
    };

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            buildMobileAppCanvas,
            { once: true }
        );
    } else {
        buildMobileAppCanvas();
    }
})();

/* V16.3_REFERENCE_ALIGNMENT_START
   Keep the floating application canvas aligned with the first drawer item.
*/
(() => {
    "use strict";

    const ROOT = document.documentElement;
    const BODY = document.body;

    if (!BODY) return;

    const syncReferenceAlignment = () => {
        const drawer = document.querySelector("[data-mobile-drawer]");
        const firstItem = drawer?.querySelector(
            ".mobile-drawer-nav .mobile-drawer-link"
        );

        if (!drawer || !firstItem) return;

        const itemRect = firstItem.getBoundingClientRect();

        /*
         * The floating app is position:fixed relative to the viewport,
         * therefore the exact viewport Y of the first menu item is the
         * correct top translation.
         */
        const top = Math.max(0, Math.round(itemRect.top));

        ROOT.style.setProperty(
            "--mobile-card-top",
            `${top}px`
        );
    };

    const syncAfterLayout = () => {
        window.requestAnimationFrame(() => {
            window.requestAnimationFrame(
                syncReferenceAlignment
            );
        });
    };

    const menuToggle = document.querySelector(
        "[data-mobile-menu-toggle]"
    );
    const menuClose = document.querySelector(
        "[data-mobile-menu-close]"
    );

    menuToggle?.addEventListener(
        "click",
        syncAfterLayout
    );

    menuClose?.addEventListener(
        "click",
        syncAfterLayout
    );

    window.addEventListener(
        "resize",
        syncAfterLayout,
        { passive: true }
    );

    window.addEventListener(
        "orientationchange",
        syncAfterLayout,
        { passive: true }
    );

    /*
     * Observe the body class because the existing V16 controller owns
     * mobile-nav-open. This keeps V16.3 independent from its internals.
     */
    const observer = new MutationObserver(
        (mutations) => {
            const classChanged = mutations.some(
                (mutation) => (
                    mutation.type === "attributes"
                    && mutation.attributeName === "class"
                )
            );

            if (
                classChanged
                && BODY.classList.contains("mobile-nav-open")
            ) {
                syncAfterLayout();
            }
        }
    );

    observer.observe(
        BODY,
        {
            attributes: true,
            attributeFilter: ["class"],
        }
    );

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            syncAfterLayout,
            { once: true }
        );
    } else {
        syncAfterLayout();
    }
})();
/* V16.3_REFERENCE_ALIGNMENT_END */

/* V16.4_SCROLLABLE_FLOATING_CANVAS_START
   Preserve the floating card scroll position only while the drawer is open.
   Reset to the top each time a new drawer session starts, matching the visual
   reference and preventing a previously scrolled page from opening halfway down.
*/
(() => {
    "use strict";

    const body = document.body;

    if (!body) return;

    let wasOpen = body.classList.contains("mobile-nav-open");

    const syncDrawerScrollSession = () => {
        const isOpen = body.classList.contains("mobile-nav-open");

        if (isOpen && !wasOpen) {
            const canvas = document.querySelector(
                ".mobile-app-canvas"
            );

            if (canvas) {
                canvas.scrollTop = 0;
            }
        }

        wasOpen = isOpen;
    };

    const observer = new MutationObserver(
        (mutations) => {
            const classChanged = mutations.some(
                (mutation) => (
                    mutation.type === "attributes"
                    && mutation.attributeName === "class"
                )
            );

            if (classChanged) {
                syncDrawerScrollSession();
            }
        }
    );

    observer.observe(
        body,
        {
            attributes: true,
            attributeFilter: ["class"],
        }
    );
})();
/* V16.4_SCROLLABLE_FLOATING_CANVAS_END */
