/* V16.6_SLIDING_INDICATORS_START */
(() => {
    "use strict";

    const BOTTOM_SELECTOR = ".mobile-bottom-nav";
    const DRAWER_SELECTOR = "[data-mobile-drawer]";

    const nextFrames = (callback) => {
        window.requestAnimationFrame(() => {
            window.requestAnimationFrame(callback);
        });
    };

    const createSlider = (parent, className) => {
        let slider = parent.querySelector(`.${className}`);

        if (slider) return slider;

        slider = document.createElement("span");
        slider.className = className;
        slider.setAttribute("aria-hidden", "true");

        parent.prepend(slider);
        return slider;
    };

    const setReadyAfterInitialPlacement = (slider) => {
        window.requestAnimationFrame(() => {
            slider.classList.add("is-ready");
        });
    };

    /* ---------------- Bottom navigation ---------------- */

    const bottomNav = document.querySelector(BOTTOM_SELECTOR);
    let bottomSlider = null;

    const positionBottomSlider = (target, animate = true) => {
        if (
            !bottomNav
            || !bottomSlider
            || !(target instanceof HTMLElement)
        ) {
            return;
        }

        if (!animate) {
            bottomSlider.classList.remove("is-ready");
        }

        const navRect = bottomNav.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();

        const x = targetRect.left - navRect.left;

        bottomSlider.style.width = `${targetRect.width}px`;
        bottomSlider.style.transform =
            `translate3d(${Math.round(x)}px, 0, 0)`;

        if (!animate) {
            setReadyAfterInitialPlacement(bottomSlider);
        }
    };

    const activateBottomLink = (target) => {
        if (!bottomNav || !(target instanceof HTMLElement)) return;

        const links = Array.from(
            bottomNav.querySelectorAll(".mobile-bottom-link")
        );

        links.forEach((link) => {
            const active = link === target;

            link.classList.toggle("is-active", active);

            if (active) {
                link.setAttribute("aria-current", "page");
            } else {
                link.removeAttribute("aria-current");
            }
        });

        /*
         * The links reflow immediately because the active slot is wider.
         * The white slider alone performs the visible glide.
         */
        nextFrames(() => {
            positionBottomSlider(target, true);
        });
    };

    if (bottomNav) {
        bottomSlider = createSlider(
            bottomNav,
            "mobile-bottom-slider"
        );

        const initial = bottomNav.querySelector(
            ".mobile-bottom-link.is-active"
        );

        if (initial) {
            nextFrames(() => {
                positionBottomSlider(initial, false);
            });
        }

        bottomNav.addEventListener(
            "pointerdown",
            (event) => {
                const target = event.target.closest(
                    ".mobile-bottom-link"
                );

                if (target) {
                    activateBottomLink(target);
                }
            },
            {
                capture: true,
                passive: true,
            }
        );
    }

    /* ---------------- Drawer indicator ---------------- */

    const drawer = document.querySelector(DRAWER_SELECTOR);
    let drawerSlider = null;

    const positionDrawerSlider = (target, animate = true) => {
        if (
            !drawer
            || !drawerSlider
            || !(target instanceof HTMLElement)
        ) {
            return;
        }

        if (!animate) {
            drawerSlider.classList.remove("is-ready");
        }

        const drawerRect = drawer.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();

        const x = targetRect.left - drawerRect.left;
        const y = targetRect.top - drawerRect.top;

        drawerSlider.style.width = `${targetRect.width}px`;
        drawerSlider.style.height = `${targetRect.height}px`;
        drawerSlider.style.transform =
            `translate3d(${Math.round(x)}px, ${Math.round(y)}px, 0)`;

        if (!animate) {
            setReadyAfterInitialPlacement(drawerSlider);
        }
    };

    const activateDrawerLink = (target) => {
        if (!drawer || !(target instanceof HTMLElement)) return;

        drawer
            .querySelectorAll(".mobile-drawer-link")
            .forEach((link) => {
                const active = link === target;

                link.classList.toggle("is-active", active);

                if (active) {
                    link.setAttribute("aria-current", "page");
                } else {
                    link.removeAttribute("aria-current");
                }
            });

        positionDrawerSlider(target, true);
    };

    if (drawer) {
        drawerSlider = createSlider(
            drawer,
            "mobile-drawer-slider"
        );

        const initial =
            drawer.querySelector(".mobile-drawer-link.is-active")
            || drawer.querySelector(".mobile-drawer-link");

        if (initial) {
            nextFrames(() => {
                positionDrawerSlider(initial, false);
            });
        }

        drawer.addEventListener(
            "pointerdown",
            (event) => {
                const target = event.target.closest(
                    ".mobile-drawer-link"
                );

                if (target) {
                    activateDrawerLink(target);
                }
            },
            {
                capture: true,
                passive: true,
            }
        );
    }

    /* ---------------- Keep geometry correct ---------------- */

    const syncIndicators = () => {
        if (bottomNav && bottomSlider) {
            const active = bottomNav.querySelector(
                ".mobile-bottom-link.is-active"
            );

            if (active) {
                positionBottomSlider(active, false);
            }
        }

        if (drawer && drawerSlider) {
            const active = drawer.querySelector(
                ".mobile-drawer-link.is-active"
            );

            if (active) {
                positionDrawerSlider(active, false);
            }
        }
    };

    window.addEventListener(
        "resize",
        () => nextFrames(syncIndicators),
        { passive: true }
    );

    window.addEventListener(
        "orientationchange",
        () => nextFrames(syncIndicators),
        { passive: true }
    );

    window.addEventListener(
        "pageshow",
        () => nextFrames(syncIndicators)
    );

    if ("ResizeObserver" in window) {
        const observer = new ResizeObserver(() => {
            nextFrames(syncIndicators);
        });

        if (bottomNav) observer.observe(bottomNav);
        if (drawer) observer.observe(drawer);
    }
})();
/* V16.6_SLIDING_INDICATORS_END */

/* V16.7_GHOST_SLIDER_FIX_START */
(() => {
    "use strict";

    const nav = document.querySelector(".mobile-bottom-nav");
    if (!nav) return;

    const slider = nav.querySelector(".mobile-bottom-slider");
    if (!slider) return;

    const syncVisibility = () => {
        const active = nav.querySelector(
            ".mobile-bottom-link.is-active"
        );

        slider.classList.toggle(
            "is-hidden",
            !active
        );
    };

    syncVisibility();

    const observer = new MutationObserver(
        (mutations) => {
            const relevant = mutations.some(
                (mutation) => (
                    mutation.type === "attributes"
                    && mutation.attributeName === "class"
                )
            );

            if (relevant) {
                syncVisibility();
            }
        }
    );

    nav.querySelectorAll(".mobile-bottom-link").forEach(
        (link) => {
            observer.observe(
                link,
                {
                    attributes: true,
                    attributeFilter: ["class"],
                }
            );
        }
    );

    window.addEventListener(
        "pageshow",
        syncVisibility
    );
})();
/* V16.7_GHOST_SLIDER_FIX_END */
