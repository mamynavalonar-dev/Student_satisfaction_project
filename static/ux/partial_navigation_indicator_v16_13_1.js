/* V16.13.1_NAV_INDICATOR_SYNC_START */
(() => {
    "use strict";

    const STORAGE_KEY =
        "student-satisfaction-v16131-last-route";

    const GROUPS = [
        {
            rootSelector: "[data-animated-nav]",
            linkSelector: "a[href]",
            activeClasses: ["active"],
            indicatorSelector: ".nav-indicator",
            hideWithoutMatch: false,
        },
        {
            rootSelector: "[data-mobile-drawer]",
            linkSelector: ".mobile-drawer-link[href]",
            activeClasses: ["active", "is-active"],
            indicatorSelector: ".mobile-drawer-slider",
            hideWithoutMatch: false,
        },
        {
            rootSelector: ".mobile-bottom-nav",
            linkSelector: ".mobile-bottom-link[href]",
            activeClasses: ["active", "is-active"],
            indicatorSelector: ".mobile-bottom-slider",
            hideWithoutMatch: true,
        },
    ];

    const toUrl = (value) => {
        try {
            return new URL(
                value,
                window.location.href
            );
        } catch (_) {
            return null;
        }
    };

    const normalizePath = (pathname) => {
        let path = pathname || "/";

        try {
            path = decodeURIComponent(path);
        } catch (_) {
            /* Keep browser pathname if decoding fails. */
        }

        path = path.replace(/\/{2,}/g, "/");

        if (
            path.length > 1
            && path.endsWith("/")
        ) {
            path = path.slice(0, -1);
        }

        return path || "/";
    };

    const routeIdentity = (value) => {
        const url = toUrl(value);

        if (!url) return null;

        return {
            origin: url.origin,
            path: normalizePath(
                url.pathname
            ),
            search: url.search || "",
        };
    };

    const sameRoute = (
        leftValue,
        rightValue
    ) => {
        const left =
            routeIdentity(leftValue);

        const right =
            routeIdentity(rightValue);

        if (!left || !right) {
            return false;
        }

        return (
            left.origin === right.origin
            && left.path === right.path
            && left.search === right.search
        );
    };

    const routePathMatches = (
        leftValue,
        rightValue
    ) => {
        const left =
            routeIdentity(leftValue);

        const right =
            routeIdentity(rightValue);

        if (!left || !right) {
            return false;
        }

        return (
            left.origin === right.origin
            && left.path === right.path
        );
    };

    const groupLinks = (
        groupRoot,
        group
    ) => (
        Array.from(
            groupRoot.querySelectorAll(
                group.linkSelector
            )
        )
    );

    const findMatch = (
        groupRoot,
        group,
        url
    ) => {
        const links =
            groupLinks(
                groupRoot,
                group
            );

        const exact = links.find(
            (link) => (
                sameRoute(
                    link.href,
                    url
                )
            )
        );

        if (exact) {
            return exact;
        }

        /*
         * Query strings can differ after filtering pages.
         * For the primary five application routes, pathname
         * is the stable navigation identity.
         */
        return links.find(
            (link) => (
                routePathMatches(
                    link.href,
                    url
                )
            )
        ) || null;
    };

    const setLinkState = (
        groupRoot,
        group,
        activeLink
    ) => {
        groupLinks(
            groupRoot,
            group
        ).forEach((link) => {
            const active =
                link === activeLink;

            group.activeClasses.forEach(
                (className) => {
                    link.classList.toggle(
                        className,
                        active
                    );
                }
            );

            link.removeAttribute(
                "data-nav-pending"
            );

            if (active) {
                link.setAttribute(
                    "aria-current",
                    "page"
                );
            } else {
                link.removeAttribute(
                    "aria-current"
                );
            }
        });
    };

    const indicatorPosition = (
        indicator,
        activeLink
    ) => {
        const parent =
            indicator.offsetParent
            || indicator.parentElement;

        if (!parent) {
            return null;
        }

        const parentRect =
            parent.getBoundingClientRect();

        const linkRect =
            activeLink.getBoundingClientRect();

        return {
            x: Math.round(
                linkRect.left
                - parentRect.left
                + parent.scrollLeft
            ),
            y: Math.round(
                linkRect.top
                - parentRect.top
                + parent.scrollTop
            ),
            width: Math.round(
                linkRect.width
            ),
            height: Math.round(
                linkRect.height
            ),
        };
    };

    const moveIndicator = (
        groupRoot,
        group,
        activeLink
    ) => {
        const indicator =
            groupRoot.querySelector(
                group.indicatorSelector
            );

        if (!indicator) {
            return;
        }

        if (!activeLink) {
            if (group.hideWithoutMatch) {
                indicator.classList.add(
                    "is-hidden"
                );
            }

            return;
        }

        indicator.classList.remove(
            "is-hidden"
        );

        const position =
            indicatorPosition(
                indicator,
                activeLink
            );

        if (!position) {
            return;
        }

        /*
         * Inline geometry wins over stale server-rendered
         * "Accueil" geometry while preserving CSS transitions.
         */
        indicator.style.setProperty(
            "width",
            `${position.width}px`
        );

        if (
            group.indicatorSelector === ".mobile-bottom-slider"
        ) {
            /* V16.13.8.1: V16.6 owns vertical geometry. */
            indicator.style.removeProperty("height");
            indicator.style.setProperty(
                "transform",
                `translate3d(${position.x}px, 0, 0)`
            );
        } else {
            indicator.style.setProperty(
                "height",
                `${position.height}px`
            );

            indicator.style.setProperty(
                "transform",
                `translate3d(${position.x}px, ${position.y}px, 0)`
            );
        }
    };

    const synchronizeGroup = (
        group,
        url
    ) => {
        const groupRoot =
            document.querySelector(
                group.rootSelector
            );

        if (!groupRoot) {
            return;
        }

        const activeLink =
            findMatch(
                groupRoot,
                group,
                url
            );

        setLinkState(
            groupRoot,
            group,
            activeLink
        );

        /*
         * First update classes, then measure. Two passes also
         * win over older V16 observers that may run in the same frame.
         */
        requestAnimationFrame(() => {
            moveIndicator(
                groupRoot,
                group,
                activeLink
            );

            requestAnimationFrame(() => {
                moveIndicator(
                    groupRoot,
                    group,
                    activeLink
                );
            });
        });
    };

    const synchronize = (
        url,
        {
            remember = true,
        } = {}
    ) => {
        const resolved =
            toUrl(url);

        if (!resolved) {
            return;
        }

        GROUPS.forEach(
            (group) => {
                synchronizeGroup(
                    group,
                    resolved
                );
            }
        );

        if (remember) {
            try {
                sessionStorage.setItem(
                    STORAGE_KEY,
                    resolved.href
                );
            } catch (_) {
                /* Visual state can work without storage. */
            }
        }
    };

    const primaryAnchor = (
        event
    ) => {
        if (
            event.defaultPrevented
            || event.button !== 0
            || event.metaKey
            || event.ctrlKey
            || event.shiftKey
            || event.altKey
        ) {
            return null;
        }

        const selector =
            GROUPS.map(
                (group) => (
                    `${group.rootSelector} ${group.linkSelector}`
                )
            ).join(",");

        const anchor =
            event.target.closest(
                selector
            );

        if (
            !(anchor instanceof HTMLAnchorElement)
            || anchor.target === "_blank"
            || anchor.hasAttribute("download")
        ) {
            return null;
        }

        const url =
            toUrl(anchor.href);

        if (
            !url
            || url.origin
                !== window.location.origin
        ) {
            return null;
        }

        return anchor;
    };

    /*
     * IMPORTANT: this script is loaded BEFORE V16.13.
     * Its capture handler therefore runs before V16.13 calls
     * stopImmediatePropagation(). The indicator starts sliding
     * as soon as the user clicks, while the shell remains mounted.
     */
    document.addEventListener(
        "click",
        (event) => {
            const anchor =
                primaryAnchor(
                    event
                );

            if (!anchor) {
                return;
            }

            synchronize(
                anchor.href
            );
        },
        true
    );

    /*
     * V16.13 emits this only after the fetched Django page
     * has replaced main.main-content. Re-sync using the final URL.
     */
    window.addEventListener(
        "v1613:navigated",
        (event) => {
            synchronize(
                event.detail?.url
                || window.location.href
            );
        }
    );

    /*
     * V16.13 handles popstate asynchronously. A direct sync here
     * gives immediate visual feedback; v1613:navigated confirms
     * it again after the fetched page is ready.
     */
    window.addEventListener(
        "popstate",
        () => {
            synchronize(
                window.location.href
            );
        }
    );

    window.addEventListener(
        "pageshow",
        () => {
            synchronize(
                window.location.href
            );
        }
    );

    window.addEventListener(
        "resize",
        () => {
            synchronize(
                window.location.href,
                {
                    remember: false,
                }
            );
        },
        {
            passive: true,
        }
    );

    /*
     * Initial server render: make the indicator agree with the
     * actual URL even if another V16 script initialized it first.
     */
    if (
        document.readyState
        === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            () => {
                synchronize(
                    window.location.href
                );
            },
            {
                once: true,
            }
        );
    } else {
        synchronize(
            window.location.href
        );
    }

    root.dataset.navIndicatorSync =
        "v16.13.1";
})();
/* V16.13.1_NAV_INDICATOR_SYNC_END */
