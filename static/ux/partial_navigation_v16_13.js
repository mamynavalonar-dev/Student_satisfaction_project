/* V16.13_PARTIAL_NAVIGATION_START */
(() => {
    "use strict";

    const root = document.documentElement;
    const parser = new DOMParser();

    const CACHE_TTL_MS = 12000;
    const CACHE = new Map();

    const NAV_SELECTOR = [
        "[data-animated-nav] a[href]",
        "[data-mobile-drawer] a.mobile-drawer-link[href]",
        ".mobile-bottom-nav a[href]",
        ".brand[href]"
    ].join(",");

    let navigationSequence = 0;

    const closestFromTarget = (
        target,
        selector
    ) => {
        const element =
            target instanceof Element
                ? target
                : target?.parentElement;

        return element instanceof Element
            ? element.closest(selector)
            : null;
    };

    const normalizeUrl = (value) => {
        try {
            return new URL(value, window.location.href);
        } catch (_) {
            return null;
        }
    };

    const sameRoute = (left, right) => (
        left.origin === right.origin
        && left.pathname === right.pathname
        && left.search === right.search
    );

    const eligibleAnchor = (anchor, event = null) => {
        if (!(anchor instanceof HTMLAnchorElement)) {
            return null;
        }

        if (
            anchor.target === "_blank"
            || anchor.hasAttribute("download")
            || anchor.dataset.v1613FullNavigation === "true"
        ) {
            return null;
        }

        if (
            event
            && (
                event.defaultPrevented
                || event.button !== 0
                || event.metaKey
                || event.ctrlKey
                || event.shiftKey
                || event.altKey
            )
        ) {
            return null;
        }

        const url = normalizeUrl(anchor.href);

        if (
            !url
            || url.origin !== window.location.origin
            || !/^https?:$/.test(url.protocol)
        ) {
            return null;
        }

        const current = new URL(window.location.href);

        if (
            sameRoute(url, current)
            && (
                !url.hash
                || url.hash === current.hash
            )
        ) {
            return null;
        }

        if (
            sameRoute(url, current)
            && url.hash
            && url.hash !== current.hash
        ) {
            return null;
        }

        return url;
    };

    const hardNavigate = (url) => {
        window.location.assign(
            typeof url === "string"
                ? url
                : url.href
        );
    };

    const fetchDocument = (url) => {
        const key = url.href;
        const now = Date.now();
        const cached = CACHE.get(key);

        if (
            cached
            && now - cached.createdAt < CACHE_TTL_MS
        ) {
            return cached.promise;
        }

        const promise = fetch(
            key,
            {
                method: "GET",
                credentials: "same-origin",
                headers: {
                    "Accept": "text/html,application/xhtml+xml",
                    "X-Requested-With": "XMLHttpRequest",
                    "X-Student-Satisfaction-Partial": "v16.13",
                },
                redirect: "follow",
                cache: "default",
            }
        ).then(async (response) => {
            const contentType =
                response.headers.get("content-type") || "";

            if (
                !response.ok
                || !contentType.includes("text/html")
            ) {
                throw new Error(
                    `Réponse non compatible avec la navigation partielle (${response.status}).`
                );
            }

            const html = await response.text();
            const finalUrl = new URL(
                response.url || key,
                window.location.href
            );

            return {
                html,
                finalUrl,
                redirected: response.redirected,
            };
        });

        CACHE.set(
            key,
            {
                createdAt: now,
                promise,
            }
        );

        promise.catch(() => {
            const entry = CACHE.get(key);

            if (entry?.promise === promise) {
                CACHE.delete(key);
            }
        });

        return promise;
    };

    const parseFetchedDocument = (payload) => {
        const doc = parser.parseFromString(
            payload.html,
            "text/html"
        );

        const base = doc.createElement("base");
        base.href = payload.finalUrl.href;
        doc.head.prepend(base);

        return doc;
    };

    const nodesBetween = (start, end) => {
        const nodes = [];
        let node = start?.nextSibling || null;

        while (node && node !== end) {
            nodes.push(node);
            node = node.nextSibling;
        }

        return nodes;
    };

    const waitForStylesheet = (node) => {
        if (
            !(node instanceof HTMLLinkElement)
            || (
                node.rel !== "stylesheet"
                && !node.relList?.contains("stylesheet")
            )
        ) {
            return Promise.resolve();
        }

        if (node.sheet) {
            return Promise.resolve();
        }

        return new Promise((resolve) => {
            const done = () => resolve();

            node.addEventListener(
                "load",
                done,
                { once: true }
            );

            node.addEventListener(
                "error",
                done,
                { once: true }
            );

            window.setTimeout(
                done,
                1600
            );
        });
    };

    const syncPageHead = async (nextDoc) => {
        const currentStart = document.querySelector(
            'meta[name="v1613-page-head-start"]'
        );

        const currentEnd = document.querySelector(
            'meta[name="v1613-page-head-end"]'
        );

        const nextStart = nextDoc.querySelector(
            'meta[name="v1613-page-head-start"]'
        );

        const nextEnd = nextDoc.querySelector(
            'meta[name="v1613-page-head-end"]'
        );

        if (
            !currentStart
            || !currentEnd
            || !nextStart
            || !nextEnd
        ) {
            throw new Error(
                "Marqueurs CSS V16.13 absents."
            );
        }

        const oldNodes =
            nodesBetween(
                currentStart,
                currentEnd
            );

        const newNodes =
            nodesBetween(
                nextStart,
                nextEnd
            );

        const inserted = [];

        for (const node of newNodes) {
            const clone =
                document.importNode(
                    node,
                    true
                );

            currentEnd.parentNode.insertBefore(
                clone,
                currentEnd
            );

            inserted.push(clone);
        }

        await Promise.all(
            inserted.map(
                waitForStylesheet
            )
        );

        /*
         * New page CSS is ready before old page CSS is removed,
         * so there is no unstyled frame between them.
         */
        oldNodes.forEach(
            (node) => node.remove()
        );
    };

    const destroyPageResources = (main) => {
        if (
            window.Chart
            && typeof window.Chart.getChart === "function"
        ) {
            main
                .querySelectorAll("canvas")
                .forEach((canvas) => {
                    try {
                        window.Chart
                            .getChart(canvas)
                            ?.destroy();
                    } catch (_) {
                        /* Old chart cleanup is best-effort. */
                    }
                });
        }
    };

    const copyMainAttributes = (
        currentMain,
        nextMain
    ) => {
        const temporaryMinHeight =
            currentMain.style.minHeight;

        Array.from(
            currentMain.attributes
        ).forEach((attribute) => {
            currentMain.removeAttribute(
                attribute.name
            );
        });

        Array.from(
            nextMain.attributes
        ).forEach((attribute) => {
            currentMain.setAttribute(
                attribute.name,
                attribute.value
            );
        });

        if (temporaryMinHeight) {
            currentMain.style.minHeight =
                temporaryMinHeight;
        }
    };

    const replaceMain = (nextDoc) => {
        const currentMain =
            document.querySelector(
                "main.main-content"
            );

        const nextMain =
            nextDoc.querySelector(
                "main.main-content"
            );

        if (!currentMain || !nextMain) {
            throw new Error(
                "main.main-content absent de la réponse."
            );
        }

        const oldHeight =
            Math.ceil(
                currentMain.getBoundingClientRect().height
            );

        if (oldHeight > 0) {
            currentMain.style.minHeight =
                `${oldHeight}px`;
        }

        destroyPageResources(
            currentMain
        );

        copyMainAttributes(
            currentMain,
            nextMain
        );

        currentMain.innerHTML =
            nextMain.innerHTML;

        currentMain.setAttribute(
            "data-v1613-busy",
            "false"
        );

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                currentMain.style.minHeight = "";
            });
        });

        return currentMain;
    };


    const invokeListener = (
        target,
        listener,
        event
    ) => {
        try {
            if (
                typeof listener === "function"
            ) {
                listener.call(
                    target,
                    event
                );
            } else if (
                listener
                && typeof listener.handleEvent
                    === "function"
            ) {
                listener.handleEvent(
                    event
                );
            }
        } catch (error) {
            console.error(
                "V16.13 page listener error:",
                error
            );
        }
    };

    const executePageScripts = async (
        nextDoc,
        finalUrl
    ) => {
        const source = nextDoc.querySelector(
            "#v1613-page-scripts"
        );

        const live = document.querySelector(
            "#v1613-page-scripts"
        );

        if (!source || !live) {
            throw new Error(
                "Conteneur scripts V16.13 absent."
            );
        }

        const scripts =
            Array.from(
                source.querySelectorAll(
                    "script"
                )
            );

        live.replaceChildren();

        const readyListeners = [];
        const loadListeners = [];

        const originalDocumentAdd =
            document.addEventListener;

        const originalWindowAdd =
            window.addEventListener;

        document.addEventListener =
            function (
                type,
                listener,
                options
            ) {
                if (
                    type === "DOMContentLoaded"
                ) {
                    readyListeners.push(
                        listener
                    );
                    return;
                }

                return originalDocumentAdd.call(
                    document,
                    type,
                    listener,
                    options
                );
            };

        window.addEventListener =
            function (
                type,
                listener,
                options
            ) {
                if (type === "load") {
                    loadListeners.push(
                        listener
                    );
                    return;
                }

                return originalWindowAdd.call(
                    window,
                    type,
                    listener,
                    options
                );
            };

        try {
            for (
                let index = 0;
                index < scripts.length;
                index += 1
            ) {
                const sourceScript =
                    scripts[index];

                const type = (
                    sourceScript.getAttribute(
                        "type"
                    )
                    || ""
                ).trim();

                const src =
                    sourceScript.getAttribute(
                        "src"
                    );

                if (
                    type
                    && ![
                        "text/javascript",
                        "application/javascript",
                        "module",
                    ].includes(type)
                ) {
                    const inert =
                        document.importNode(
                            sourceScript,
                            true
                        );

                    live.appendChild(
                        inert
                    );
                    continue;
                }

                if (src) {
                    const absoluteSrc =
                        new URL(
                            src,
                            finalUrl
                        ).href;

                    const globalAlreadyLoaded =
                        Array.from(
                            document.querySelectorAll(
                                "script[src]"
                            )
                        ).some((existing) => {
                            if (
                                live.contains(existing)
                            ) {
                                return false;
                            }

                            try {
                                return (
                                    new URL(
                                        existing.src,
                                        window.location.href
                                    ).href
                                    === absoluteSrc
                                );
                            } catch (_) {
                                return false;
                            }
                        });

                    if (globalAlreadyLoaded) {
                        continue;
                    }

                    await new Promise(
                        (resolve, reject) => {
                            const script =
                                document.createElement(
                                    "script"
                                );

                            for (
                                const attribute
                                of sourceScript.attributes
                            ) {
                                if (
                                    attribute.name
                                    === "src"
                                ) {
                                    continue;
                                }

                                script.setAttribute(
                                    attribute.name,
                                    attribute.value
                                );
                            }

                            script.src =
                                absoluteSrc;

                            script.onload =
                                () => resolve();

                            script.onerror =
                                () => reject(
                                    new Error(
                                        `Script page impossible à charger: ${absoluteSrc}`
                                    )
                                );

                            live.appendChild(
                                script
                            );
                        }
                    );

                    continue;
                }

                const code =
                    sourceScript.textContent || "";

                if (!code.trim()) {
                    continue;
                }

                const executable =
                    document.createElement(
                        "script"
                    );

                executable.textContent =
                    "(function(){\n"
                    + code
                    + "\n}).call(window);\n"
                    + `//# sourceURL=v1613-inline-${index}.js`;

                live.appendChild(
                    executable
                );
            }
        } finally {
            document.addEventListener =
                originalDocumentAdd;

            window.addEventListener =
                originalWindowAdd;
        }

        const readyEvent =
            new Event(
                "DOMContentLoaded"
            );

        readyListeners.forEach(
            (listener) => {
                invokeListener(
                    document,
                    listener,
                    readyEvent
                );
            }
        );

        const loadEvent =
            new Event("load");

        loadListeners.forEach(
            (listener) => {
                invokeListener(
                    window,
                    listener,
                    loadEvent
                );
            }
        );
    };

    const routeKey = (value) => {
        const url =
            normalizeUrl(value);

        if (!url) return "";

        let path = url.pathname;

        if (
            path.length > 1
            && path.endsWith("/")
        ) {
            path = path.slice(0, -1);
        }

        return path + url.search;
    };

    const syncNavigation = (url) => {
        const target =
            routeKey(url.href);

        const groups = [
            {
                selector:
                    "[data-animated-nav] a[href]",
                activeClasses:
                    ["active"],
            },
            {
                selector:
                    ".mobile-drawer-link[href]",
                activeClasses:
                    ["active", "is-active"],
            },
            {
                selector:
                    ".mobile-bottom-link[href]",
                activeClasses:
                    ["active", "is-active"],
            },
        ];

        groups.forEach((group) => {
            document
                .querySelectorAll(
                    group.selector
                )
                .forEach((link) => {
                    const active = (
                        routeKey(link.href)
                        === target
                    );

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
        });
    };

    const syncIndicators = () => {
        requestAnimationFrame(() => {
            const desktop =
                document.querySelector(
                    "[data-animated-nav]"
                );

            const desktopActive =
                desktop?.querySelector(
                    "a.active"
                );

            const desktopIndicator =
                desktop?.querySelector(
                    ".nav-indicator"
                );

            if (
                desktop
                && desktopActive
                && desktopIndicator
            ) {
                desktopIndicator.style.width =
                    `${desktopActive.offsetWidth}px`;

                desktopIndicator.style.height =
                    `${desktopActive.offsetHeight}px`;

                desktopIndicator.style.transform =
                    `translate3d(${desktopActive.offsetLeft}px, ${desktopActive.offsetTop}px, 0)`;
            }

            const bottom =
                document.querySelector(
                    ".mobile-bottom-nav"
                );

            const bottomActive =
                bottom?.querySelector(
                    ".mobile-bottom-link.is-active"
                );

            const bottomSlider =
                bottom?.querySelector(
                    ".mobile-bottom-slider"
                );

            if (
                bottom
                && bottomSlider
            ) {
                if (bottomActive) {
                    const navRect =
                        bottom.getBoundingClientRect();

                    const activeRect =
                        bottomActive.getBoundingClientRect();

                    bottomSlider.classList.remove(
                        "is-hidden"
                    );

                    bottomSlider.style.width =
                        `${activeRect.width}px`;

                    bottomSlider.style.transform =
                        `translate3d(${Math.round(activeRect.left - navRect.left)}px, 0, 0)`;
                } else {
                    bottomSlider.classList.add(
                        "is-hidden"
                    );
                }
            }

            const drawer =
                document.querySelector(
                    "[data-mobile-drawer]"
                );

            const drawerActive =
                drawer?.querySelector(
                    ".mobile-drawer-link.is-active"
                );

            const drawerSlider =
                drawer?.querySelector(
                    ".mobile-drawer-slider"
                );

            if (
                drawer
                && drawerActive
                && drawerSlider
            ) {
                const drawerRect =
                    drawer.getBoundingClientRect();

                const activeRect =
                    drawerActive.getBoundingClientRect();

                drawerSlider.style.width =
                    `${activeRect.width}px`;

                drawerSlider.style.height =
                    `${activeRect.height}px`;

                drawerSlider.style.transform =
                    `translate3d(${Math.round(activeRect.left - drawerRect.left)}px, ${Math.round(activeRect.top - drawerRect.top)}px, 0)`;
            }
        });
    };

    const resetScroll = () => {
        const canvas =
            document.querySelector(
                ".mobile-app-canvas"
            );

        if (
            document.body.classList.contains(
                "mobile-nav-open"
            )
            && canvas
        ) {
            canvas.scrollTop = 0;
        } else {
            window.scrollTo(
                {
                    top: 0,
                    left: 0,
                    behavior: "auto",
                }
            );
        }
    };

    const applyDocument = async (
        payload,
        {
            historyMode = "push",
            sequence,
        } = {}
    ) => {
        if (
            sequence !== navigationSequence
        ) {
            return;
        }

        const nextDoc =
            parseFetchedDocument(
                payload
            );

        const nextMain =
            nextDoc.querySelector(
                "main.main-content"
            );

        const nextScripts =
            nextDoc.querySelector(
                "#v1613-page-scripts"
            );

        if (
            !nextMain
            || !nextScripts
        ) {
            throw new Error(
                "La réponse ne possède pas le shell V16.13."
            );
        }

        await syncPageHead(
            nextDoc
        );

        if (
            sequence !== navigationSequence
        ) {
            return;
        }

        replaceMain(
            nextDoc
        );


        document.title =
            nextDoc.title
            || document.title;

        const nextLang =
            nextDoc.documentElement
                .getAttribute("lang");

        if (nextLang) {
            document.documentElement
                .setAttribute(
                    "lang",
                    nextLang
                );
        }

        syncNavigation(
            payload.finalUrl
        );

        if (
            historyMode === "push"
        ) {
            history.pushState(
                {
                    v1613: true,
                },
                "",
                payload.finalUrl.href
            );
        } else if (
            historyMode === "replace"
        ) {
            history.replaceState(
                {
                    v1613: true,
                },
                "",
                payload.finalUrl.href
            );
        }

        await executePageScripts(
            nextDoc,
            payload.finalUrl
        );

        syncIndicators();
        resetScroll();

        window.dispatchEvent(
            new CustomEvent(
                "v1613:navigated",
                {
                    detail: {
                        url:
                            payload.finalUrl.href,
                    },
                }
            )
        );
    };

    const navigate = async (
        url,
        {
            historyMode = "push",
        } = {}
    ) => {
        const sequence =
            ++navigationSequence;

        const currentMain =
            document.querySelector(
                "main.main-content"
            );

        root.classList.remove(
            "app-navigating"
        );

        root.classList.add(
            "v1613-partial-loading"
        );

        currentMain?.setAttribute(
            "data-v1613-busy",
            "true"
        );

        try {
            const payload =
                await fetchDocument(
                    url
                );

            if (
                sequence
                !== navigationSequence
            ) {
                return;
            }

            /*
             * Authentication/permission redirects must use the
             * normal Django navigation so the whole shell is rebuilt.
             */
            if (
                payload.redirected
                && !sameRoute(
                    payload.finalUrl,
                    url
                )
            ) {
                hardNavigate(
                    payload.finalUrl
                );
                return;
            }

            await applyDocument(
                payload,
                {
                    historyMode,
                    sequence,
                }
            );
        } catch (error) {
            console.error(
                "V16.13 partial navigation fallback:",
                error
            );

            if (
                sequence
                === navigationSequence
            ) {
                hardNavigate(
                    url
                );
            }
        } finally {
            if (
                sequence
                === navigationSequence
            ) {
                root.classList.remove(
                    "v1613-partial-loading",
                    "app-navigating"
                );

                document
                    .querySelector(
                        "main.main-content"
                    )
                    ?.setAttribute(
                        "data-v1613-busy",
                        "false"
                    );
            }
        }
    };

    const prefetchAnchor = (anchor) => {
        const url =
            eligibleAnchor(
                anchor
            );

        if (!url) return;

        fetchDocument(
            url
        ).catch(() => {
            /* Prefetch failure is intentionally silent. */
        });
    };

    document.addEventListener(
        "pointerenter",
        (event) => {
            const anchor =
                closestFromTarget(
                    event.target,
                    NAV_SELECTOR
                );

            if (anchor) {
                prefetchAnchor(
                    anchor
                );
            }
        },
        true
    );

    document.addEventListener(
        "focusin",
        (event) => {
            const anchor =
                closestFromTarget(
                    event.target,
                    NAV_SELECTOR
                );

            if (anchor) {
                prefetchAnchor(
                    anchor
                );
            }
        },
        true
    );

    document.addEventListener(
        "touchstart",
        (event) => {
            const anchor =
                closestFromTarget(
                    event.target,
                    NAV_SELECTOR
                );

            if (anchor) {
                prefetchAnchor(
                    anchor
                );
            }
        },
        {
            capture: true,
            passive: true,
        }
    );

    document.addEventListener(
        "click",
        (event) => {
            const anchor =
                closestFromTarget(
                    event.target,
                    NAV_SELECTOR
                );

            const url =
                eligibleAnchor(
                    anchor,
                    event
                );

            if (!url) return;

            event.preventDefault();
            event.stopImmediatePropagation();

            navigate(
                url,
                {
                    historyMode: "push",
                }
            );
        },
        true
    );

    window.addEventListener(
        "popstate",
        () => {
            const url =
                new URL(
                    window.location.href
                );

            navigate(
                url,
                {
                    historyMode: "none",
                }
            );
        }
    );

    /*
     * Mark the current entry so back/forward navigation remains
     * inside the same-document navigator after the first click.
     */
    if (
        !history.state
        || !history.state.v1613
    ) {
        history.replaceState(
            {
                ...(history.state || {}),
                v1613: true,
            },
            "",
            window.location.href
        );
    }



    /* V16.13.6_PUBLIC_PARTIAL_API */
    window.StudentSatisfactionPartialNavigationV1613 =
        Object.freeze({
            applyHtml: async (
                html,
                finalUrlValue,
                {
                    historyMode = "none",
                } = {}
            ) => {
                const finalUrl =
                    normalizeUrl(
                        finalUrlValue
                        || window.location.href
                    );

                if (!finalUrl) {
                    throw new Error(
                        "URL V16.13.6 invalide."
                    );
                }

                const sequence =
                    ++navigationSequence;

                CACHE.clear();

                const currentMain =
                    document.querySelector(
                        "main.main-content"
                    );

                root.classList.add(
                    "v1613-partial-loading"
                );

                currentMain?.setAttribute(
                    "data-v1613-busy",
                    "true"
                );

                try {
                    await applyDocument(
                        {
                            html,
                            finalUrl,
                            redirected: false,
                        },
                        {
                            historyMode,
                            sequence,
                        }
                    );
                } finally {
                    if (
                        sequence
                        === navigationSequence
                    ) {
                        root.classList.remove(
                            "v1613-partial-loading",
                            "app-navigating"
                        );

                        document
                            .querySelector(
                                "main.main-content"
                            )
                            ?.setAttribute(
                                "data-v1613-busy",
                                "false"
                            );
                    }
                }
            },

            clearCache: () => {
                CACHE.clear();
            },
        });

    root.dataset.partialNavigation =
        "v16.13";
})();
/* V16.13_PARTIAL_NAVIGATION_END */
