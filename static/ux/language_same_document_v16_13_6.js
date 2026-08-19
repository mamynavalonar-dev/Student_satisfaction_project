/* V16.13.7_LANGUAGE_VISUAL_INTEGRITY_START */
(() => {
    "use strict";

    const root = document.documentElement;
    const DRAWER_KEY =
        "student-satisfaction-mobile-drawer-open";

    let busy = false;

    const normalizeUrl = (value) => {
        try {
            return new URL(
                value,
                window.location.href
            );
        } catch (_) {
            return null;
        }
    };

    const routeKey = (value) => {
        const url =
            normalizeUrl(value);

        if (!url) return "";

        let path =
            url.pathname || "/";

        if (
            path.length > 1
            && path.endsWith("/")
        ) {
            path =
                path.slice(0, -1);
        }

        return (
            path
            + (url.search || "")
        );
    };

    const copyTranslatedAttributes = (
        current,
        next
    ) => {
        if (!current || !next) {
            return;
        }

        [
            "aria-label",
            "aria-description",
            "title",
            "placeholder",
            "alt",
        ].forEach((name) => {
            if (
                next.hasAttribute(name)
            ) {
                current.setAttribute(
                    name,
                    next.getAttribute(name)
                );
            } else {
                current.removeAttribute(
                    name
                );
            }
        });
    };

    const nonEmptyDirectTextNodes = (
        element
    ) => (
        Array.from(
            element?.childNodes || []
        ).filter(
            (node) => (
                node.nodeType
                    === Node.TEXT_NODE
                && node.nodeValue
                    ?.trim()
            )
        )
    );

    const copyVisibleLabel = (
        current,
        next
    ) => {
        if (!current || !next) {
            return;
        }

        copyTranslatedAttributes(
            current,
            next
        );

        /*
         * Prefer an explicit final span when both sides use one.
         * This preserves icons, sliders and runtime-owned elements.
         */
        const currentSpan =
            current.querySelector(
                ":scope > span:last-child"
            );

        const nextSpan =
            next.querySelector(
                ":scope > span:last-child"
            );

        if (
            currentSpan
            && nextSpan
            && !currentSpan.classList.contains(
                "mobile-drawer-owner-name"
            )
        ) {
            currentSpan.textContent =
                nextSpan.textContent;

            return;
        }

        /*
         * Bootstrap-style desktop buttons often use:
         * <i ...></i> Profile
         * Update only their direct text nodes.
         */
        const currentTextNodes =
            nonEmptyDirectTextNodes(
                current
            );

        const nextTextNodes =
            nonEmptyDirectTextNodes(
                next
            );

        if (
            currentTextNodes.length
            && currentTextNodes.length
                === nextTextNodes.length
        ) {
            currentTextNodes.forEach(
                (node, index) => {
                    node.nodeValue =
                        nextTextNodes[
                            index
                        ].nodeValue;
                }
            );
        }
    };

    const findRoutePeer = (
        nextGroup,
        selector,
        currentLink
    ) => {
        if (
            !nextGroup
            || !currentLink
        ) {
            return null;
        }

        const key =
            routeKey(
                currentLink.href
            );

        return Array.from(
            nextGroup.querySelectorAll(
                selector
            )
        ).find(
            (link) => (
                routeKey(link.href)
                === key
            )
        ) || null;
    };

    const syncRouteGroup = (
        nextDoc,
        groupSelector,
        linkSelector
    ) => {
        const currentGroup =
            document.querySelector(
                groupSelector
            );

        const nextGroup =
            nextDoc.querySelector(
                groupSelector
            );

        if (
            !currentGroup
            || !nextGroup
        ) {
            return;
        }

        currentGroup
            .querySelectorAll(
                linkSelector
            )
            .forEach(
                (currentLink) => {
                    const nextLink =
                        findRoutePeer(
                            nextGroup,
                            linkSelector,
                            currentLink
                        );

                    if (!nextLink) {
                        return;
                    }

                    copyVisibleLabel(
                        currentLink,
                        nextLink
                    );
                }
            );
    };

    const copyText = (
        nextDoc,
        selector,
        {
            html = false,
        } = {}
    ) => {
        const current =
            document.querySelector(
                selector
            );

        const next =
            nextDoc.querySelector(
                selector
            );

        if (!current || !next) {
            return;
        }

        copyTranslatedAttributes(
            current,
            next
        );

        if (html) {
            current.innerHTML =
                next.innerHTML;
        } else {
            current.textContent =
                next.textContent;
        }
    };

    const syncLanguageFormContract = (
        nextDoc,
        selector,
        language
    ) => {
        const current =
            document.querySelector(
                selector
            );

        const next =
            nextDoc.querySelector(
                selector
            );

        if (
            !current
            || !next
        ) {
            return;
        }

        copyTranslatedAttributes(
            current,
            next
        );

        const currentNext =
            current.querySelector(
                'input[name="next"]'
            );

        const nextNext =
            next.querySelector(
                'input[name="next"]'
            );

        if (
            currentNext
            && nextNext
        ) {
            currentNext.value =
                nextNext.value;
        }

        ["fr", "en"].forEach(
            (code) => {
                const currentButton =
                    current.querySelector(
                        `button[name="language"][value="${code}"]`
                    );

                const nextButton =
                    next.querySelector(
                        `button[name="language"][value="${code}"]`
                    );

                if (
                    !currentButton
                    || !nextButton
                ) {
                    return;
                }

                copyTranslatedAttributes(
                    currentButton,
                    nextButton
                );

                currentButton.setAttribute(
                    "aria-pressed",
                    code === language
                        ? "true"
                        : "false"
                );
            }
        );
    };

    const extractAppI18n = (
        nextDoc
    ) => {
        const result = {};

        for (
            const script
            of nextDoc.scripts
        ) {
            const text =
                script.textContent || "";

            if (
                !text.includes(
                    "window.APP_I18N"
                )
            ) {
                continue;
            }

            const objectMatch =
                text.match(
                    /window\.APP_I18N\s*=\s*\{([\s\S]*?)\}\s*;/
                );

            if (!objectMatch) {
                continue;
            }

            const pattern =
                /([A-Za-z_$][\w$]*)\s*:\s*"((?:\\.|[^"\\])*)"/g;

            let match;

            while (
                (
                    match =
                        pattern.exec(
                            objectMatch[1]
                        )
                )
            ) {
                try {
                    result[
                        match[1]
                    ] = JSON.parse(
                        `"${match[2]}"`
                    );
                } catch (_) {
                    /* Optional translation entry. */
                }
            }

            break;
        }

        return result;
    };

    const syncNotifications = (
        nextDoc
    ) => {
        copyTranslatedAttributes(
            document.querySelector(
                "[data-notification-toggle]"
            ),
            nextDoc.querySelector(
                "[data-notification-toggle]"
            )
        );

        copyTranslatedAttributes(
            document.querySelector(
                "[data-notification-panel]"
            ),
            nextDoc.querySelector(
                "[data-notification-panel]"
            )
        );

        copyText(
            nextDoc,
            ".notification-panel-header strong"
        );

        copyText(
            nextDoc,
            "[data-notification-status]"
        );

        copyText(
            nextDoc,
            "[data-notification-read-all]"
        );

        copyText(
            nextDoc,
            ".notification-empty span"
        );
    };

    const captureUiState = () => {
        const body =
            document.body;

        const active =
            document.activeElement;

        const canvas =
            document.querySelector(
                ".mobile-app-canvas"
            );

        let focusTarget =
            "none";

        if (
            active instanceof HTMLElement
        ) {
            if (
                active.closest(
                    ".mobile-drawer-locale"
                )
            ) {
                focusTarget =
                    "drawer-language";
            } else if (
                active.closest(
                    ".app-locale-switch"
                )
            ) {
                focusTarget =
                    "topbar-language";
            }
        }

        return {
            drawerOpen:
                body?.classList.contains(
                    "mobile-nav-open"
                ) || false,

            canvasScrollTop:
                canvas?.scrollTop
                || 0,

            windowScrollX:
                window.scrollX,

            windowScrollY:
                window.scrollY,

            focusTarget,
        };
    };

    const restoreUiState = (
        state
    ) => {
        const body =
            document.body;

        const drawer =
            document.querySelector(
                "[data-mobile-drawer]"
            );

        const toggle =
            document.querySelector(
                "[data-mobile-menu-toggle]"
            );

        const canvas =
            document.querySelector(
                ".mobile-app-canvas"
            );

        if (
            state.drawerOpen
        ) {
            body?.classList.add(
                "mobile-nav-open"
            );

            drawer?.setAttribute(
                "aria-hidden",
                "false"
            );

            toggle?.setAttribute(
                "aria-expanded",
                "true"
            );

            try {
                sessionStorage.setItem(
                    DRAWER_KEY,
                    "1"
                );
            } catch (_) {
                /* Optional persistence. */
            }

            if (canvas) {
                canvas.scrollTop =
                    state.canvasScrollTop;
            }
        } else {
            body?.classList.remove(
                "mobile-nav-open"
            );

            drawer?.setAttribute(
                "aria-hidden",
                "true"
            );

            toggle?.setAttribute(
                "aria-expanded",
                "false"
            );

            try {
                sessionStorage.removeItem(
                    DRAWER_KEY
                );
            } catch (_) {
                /* Optional persistence. */
            }

            window.scrollTo(
                {
                    left:
                        state.windowScrollX,
                    top:
                        state.windowScrollY,
                    behavior:
                        "auto",
                }
            );
        }

        /*
         * A lost checkbox focus was the reason the skip-link could
         * become visibly focused after a language update.
         */
        const targetSelector =
            state.focusTarget
                === "drawer-language"
                ? (
                    ".mobile-drawer-locale "
                    + ".v168-language-switch "
                    + ".checkbox"
                )
                : state.focusTarget
                    === "topbar-language"
                    ? (
                        ".app-locale-switch "
                        + ".v168-language-switch "
                        + ".checkbox"
                    )
                    : null;

        if (targetSelector) {
            requestAnimationFrame(
                () => {
                    const target =
                        document.querySelector(
                            targetSelector
                        );

                    if (
                        target
                        instanceof HTMLElement
                    ) {
                        target.focus(
                            {
                                preventScroll:
                                    true,
                            }
                        );
                    }
                }
            );
        } else if (
            document.activeElement
                ?.classList
                ?.contains(
                    "skip-link"
                )
        ) {
            document.activeElement.blur();
        }
    };

    const syncStableShellPrecisely = (
        nextDoc,
        language
    ) => {
        /*
         * BRAND / GREETING
         * Safe because these elements contain no V16 runtime controls.
         */
        copyText(
            nextDoc,
            ".page-header .brand",
            {
                html: true,
            }
        );

        copyText(
            nextDoc,
            ".page-header .navbar-text",
            {
                html: true,
            }
        );

        copyText(
            nextDoc,
            ".skip-link"
        );

        /*
         * DESKTOP NAV
         * Links are unique inside the nav group.
         */
        syncRouteGroup(
            nextDoc,
            "[data-animated-nav]",
            "a[href]"
        );

        /*
         * TOPBAR ACCOUNT LINKS
         * Scoped to user-info, not the whole page-header.
         */
        syncRouteGroup(
            nextDoc,
            ".page-header .user-info",
            ":scope > a[href]"
        );

        copyText(
            nextDoc,
            ".page-header .account-role-badge"
        );

        const currentLogout =
            document.querySelector(
                ".page-header .logout-form button"
            );

        const nextLogout =
            nextDoc.querySelector(
                ".page-header .logout-form button"
            );

        copyVisibleLabel(
            currentLogout,
            nextLogout
        );

        /*
         * DRAWER OWNER
         * IMPORTANT: owner and Profile share the same href.
         * Owner is intentionally NOT matched by href.
         */
        copyTranslatedAttributes(
            document.querySelector(
                ".mobile-drawer-owner"
            ),
            nextDoc.querySelector(
                ".mobile-drawer-owner"
            )
        );

        copyTranslatedAttributes(
            document.querySelector(
                "[data-mobile-drawer]"
            ),
            nextDoc.querySelector(
                "[data-mobile-drawer]"
            )
        );

        copyTranslatedAttributes(
            document.querySelector(
                "[data-mobile-menu-close]"
            ),
            nextDoc.querySelector(
                "[data-mobile-menu-close]"
            )
        );

        /*
         * Primary drawer and tools are separate route groups.
         * This prevents /profile/ from ever matching the owner row.
         */
        syncRouteGroup(
            nextDoc,
            ".mobile-drawer-nav",
            ".mobile-drawer-link[href]"
        );

        syncRouteGroup(
            nextDoc,
            ".mobile-drawer-tools",
            ".mobile-drawer-link[href]"
        );

        /*
         * Theme row: update LABEL ONLY.
         * Never replace the runtime switch or its slider/circle.
         */
        copyText(
            nextDoc,
            "[data-mobile-theme-cycle] > span"
        );

        const nextThemeLabel =
            nextDoc.querySelector(
                "[data-mobile-theme-cycle] > span"
            )?.textContent?.trim();

        if (nextThemeLabel) {
            document
                .querySelectorAll(
                    ".mobile-drawer-theme-switch-label "
                    + "> span:last-child"
                )
                .forEach(
                    (label) => {
                        label.textContent =
                            nextThemeLabel;
                    }
                );

            document
                .querySelectorAll(
                    ".v168-theme-switch"
                )
                .forEach(
                    (switchElement) => {
                        switchElement.title =
                            nextThemeLabel;

                        switchElement
                            .querySelector(
                                'input[role="switch"]'
                            )
                            ?.setAttribute(
                                "aria-label",
                                nextThemeLabel
                            );
                    }
                );
        }

        /*
         * Language row: label and hidden server controls only.
         * The V16.8 runtime switch DOM is kept intact.
         */
        copyText(
            nextDoc,
            ".mobile-drawer-locale-label "
            + "> span:last-child"
        );

        syncLanguageFormContract(
            nextDoc,
            ".app-locale-switch",
            language
        );

        syncLanguageFormContract(
            nextDoc,
            ".mobile-drawer-locale",
            language
        );

        /*
         * Logout label only; preserve the icon/button.
         */
        copyText(
            nextDoc,
            ".mobile-drawer-logout "
            + ".mobile-drawer-action "
            + "> span:last-child"
        );

        /*
         * BOTTOM NAV
         * Only aria-label and .mobile-bottom-label change.
         * Icons and slider geometry are never replaced.
         */
        const currentBottom =
            document.querySelector(
                ".mobile-bottom-nav"
            );

        const nextBottom =
            nextDoc.querySelector(
                ".mobile-bottom-nav"
            );

        copyTranslatedAttributes(
            currentBottom,
            nextBottom
        );

        if (
            currentBottom
            && nextBottom
        ) {
            currentBottom
                .querySelectorAll(
                    ".mobile-bottom-link[href]"
                )
                .forEach(
                    (currentLink) => {
                        const nextLink =
                            findRoutePeer(
                                nextBottom,
                                ".mobile-bottom-link[href]",
                                currentLink
                            );

                        if (!nextLink) {
                            return;
                        }

                        copyTranslatedAttributes(
                            currentLink,
                            nextLink
                        );

                        const currentLabel =
                            currentLink.querySelector(
                                ".mobile-bottom-label"
                            );

                        const nextLabel =
                            nextLink.querySelector(
                                ".mobile-bottom-label"
                            );

                        if (
                            currentLabel
                            && nextLabel
                        ) {
                            currentLabel.textContent =
                                nextLabel.textContent;
                        }
                    }
                );
        }

        /*
         * Runtime notification chrome.
         */
        syncNotifications(
            nextDoc
        );

        /*
         * Footer has no persistent interaction controller.
         * Replacing only its internal content is safe.
         */
        const currentFooter =
            document.querySelector(
                "footer"
            );

        const nextFooter =
            nextDoc.querySelector(
                "footer"
            );

        if (
            currentFooter
            && nextFooter
        ) {
            currentFooter.innerHTML =
                nextFooter.innerHTML;
        }

        const appI18n =
            extractAppI18n(
                nextDoc
            );

        if (
            Object.keys(
                appI18n
            ).length
        ) {
            window.APP_I18N = {
                ...(
                    window.APP_I18N
                    || {}
                ),
                ...appI18n,
            };
        }
    };

    const syncSwitches = (
        language
    ) => {
        document
            .querySelectorAll(
                ".v168-language-switch "
                + ".checkbox"
            )
            .forEach(
                (checkbox) => {
                    if (
                        !(
                            checkbox
                            instanceof
                            HTMLInputElement
                        )
                    ) {
                        return;
                    }

                    checkbox.checked =
                        language === "en";

                    checkbox.disabled =
                        false;

                    checkbox.setAttribute(
                        "aria-checked",
                        language === "en"
                            ? "true"
                            : "false"
                    );

                    checkbox
                        .closest(
                            ".v168-language-switch"
                        )
                        ?.removeAttribute(
                            "aria-busy"
                        );
                }
            );
    };

    const refreshIndicatorGeometry = (
        finalUrl
    ) => {
        requestAnimationFrame(
            () => {
                requestAnimationFrame(
                    () => {
                        window.dispatchEvent(
                            new CustomEvent(
                                "v1613:navigated",
                                {
                                    detail: {
                                        url:
                                            finalUrl,
                                    },
                                }
                            )
                        );

                        window.dispatchEvent(
                            new Event(
                                "resize"
                            )
                        );
                    }
                );
            }
        );
    };

    const nativeFallback = (
        form,
        submitter
    ) => {
        root.classList.add(
            "v16137-language-fallback"
        );

        if (
            submitter
            instanceof HTMLButtonElement
            && typeof form.requestSubmit
                === "function"
        ) {
            form.requestSubmit(
                submitter
            );
        } else {
            HTMLFormElement
                .prototype
                .submit
                .call(
                    form
                );
        }
    };

    const change = async (
        form,
        language,
        submitter = null
    ) => {
        if (busy) {
            return false;
        }

        if (
            !["fr", "en"].includes(
                language
            )
        ) {
            return false;
        }

        const partial =
            window
                .StudentSatisfactionPartialNavigationV1613;

        if (
            !partial
            || typeof partial.applyHtml
                !== "function"
        ) {
            nativeFallback(
                form,
                submitter
            );

            return false;
        }

        const uiState =
            captureUiState();

        busy = true;

        root.classList.add(
            "v16137-language-busy"
        );

        const data =
            new FormData(
                form
            );

        data.set(
            "language",
            language
        );

        try {
            /*
             * Django remains the source of truth:
             * POST + CSRF + language cookie are all real.
             * Only the browser document replacement is removed.
             */
            const response =
                await fetch(
                    form.action,
                    {
                        method: "POST",
                        credentials:
                            "same-origin",
                        headers: {
                            "Accept":
                                "text/html,application/xhtml+xml",
                            "X-Requested-With":
                                "XMLHttpRequest",
                            "X-Student-Satisfaction-Language":
                                "v16.13.7",
                        },
                        body:
                            data,
                        redirect:
                            "follow",
                        cache:
                            "no-store",
                    }
                );

            const contentType =
                response.headers.get(
                    "content-type"
                ) || "";

            if (
                !response.ok
                || !contentType.includes(
                    "text/html"
                )
            ) {
                throw new Error(
                    `set_language HTTP ${response.status}`
                );
            }

            const html =
                await response.text();

            const finalUrl =
                response.url
                || window.location.href;

            const nextDoc =
                new DOMParser()
                    .parseFromString(
                        html,
                        "text/html"
                    );

            const resolvedLanguage = (
                nextDoc
                    .documentElement
                    .getAttribute(
                        "lang"
                    )
                || language
            )
                .toLowerCase()
                .startsWith("en")
                    ? "en"
                    : "fr";

            const applyLanguageDom =
                async () => {
                    /*
                     * Main + page-specific CSS/scripts:
                     * existing proven V16.13 engine.
                     */
                    await partial.applyHtml(
                        html,
                        finalUrl,
                        {
                            historyMode:
                                "none",
                        }
                    );

                    /*
                     * Persistent shell:
                     * precise label-only synchronization.
                     */
                    syncStableShellPrecisely(
                        nextDoc,
                        resolvedLanguage
                    );

                    document
                        .documentElement
                        .setAttribute(
                            "lang",
                            resolvedLanguage
                        );

                    syncSwitches(
                        resolvedLanguage
                    );

                    restoreUiState(
                        uiState
                    );

                    refreshIndicatorGeometry(
                        finalUrl
                    );
                };

            const reducedMotion = (
                window.matchMedia
                && window.matchMedia(
                    "(prefers-reduced-motion: reduce)"
                ).matches
            );

            /*
             * ViewTransition keeps the LAST CORRECT FRAME visible
             * while all DOM work above completes. It does not replace
             * the document and therefore cannot create a white navigation flash.
             */
            if (
                !reducedMotion
                && typeof document.startViewTransition
                    === "function"
            ) {
                const transition =
                    document.startViewTransition(
                            applyLanguageDom
                        );

                await transition.finished;
            } else {
                await applyLanguageDom();
            }

            partial.clearCache?.();

            window.dispatchEvent(
                new CustomEvent(
                    "v16137:language-changed",
                    {
                        detail: {
                            language:
                                resolvedLanguage,
                            url:
                                finalUrl,
                        },
                    }
                )
            );

            return true;
        } catch (error) {
            console.error(
                "V16.13.7 language switch fallback:",
                error
            );

            restoreUiState(
                uiState
            );

            syncSwitches(
                (
                    document
                        .documentElement
                        .lang
                    || "fr"
                )
                    .toLowerCase()
                    .startsWith("en")
                        ? "en"
                        : "fr"
            );

            nativeFallback(
                form,
                submitter
            );

            return false;
        } finally {
            busy = false;

            root.classList.remove(
                "v16137-language-busy"
            );
        }
    };

    window.StudentSatisfactionLanguageV16136 =
        Object.freeze({
            change,
        });

    root.dataset.languageNavigation =
        "v16.13.7";
})();
/* V16.13.7_LANGUAGE_VISUAL_INTEGRITY_END */
