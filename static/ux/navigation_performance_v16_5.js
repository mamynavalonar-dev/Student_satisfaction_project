(() => {
    "use strict";

    const PREFETCHED = new Set();

    const sameOriginUrl = (href) => {
        try {
            const url = new URL(href, window.location.href);
            return url.origin === window.location.origin ? url : null;
        } catch (_) {
            return null;
        }
    };

    const closestAnchor = (target) => {
        const element =
            target instanceof Element
                ? target
                : target?.parentElement;

        return element instanceof Element
            ? element.closest("a[href]")
            : null;
    };

    const prefetch = (link) => {
        if (!(link instanceof HTMLAnchorElement)) return;

        const url = sameOriginUrl(link.href);
        if (!url) return;

        if (
            url.pathname === window.location.pathname
            && url.search === window.location.search
        ) {
            return;
        }

        if (PREFETCHED.has(url.href)) return;
        PREFETCHED.add(url.href);

        const hint = document.createElement("link");
        hint.rel = "prefetch";
        hint.as = "document";
        hint.href = url.href;
        document.head.appendChild(hint);
    };

    const moveDesktopIndicator = (link) => {
        const nav = link?.closest("[data-animated-nav]");
        const indicator = nav?.querySelector(".nav-indicator");

        if (!nav || !indicator || !(link instanceof HTMLElement)) {
            return;
        }

        indicator.style.width = `${link.offsetWidth}px`;
        indicator.style.height = `${link.offsetHeight}px`;
        indicator.style.transform =
            `translate3d(${link.offsetLeft}px, ${link.offsetTop}px, 0)`;
    };

    const markBottomPending = (link) => {
        const nav = link?.closest(".mobile-bottom-nav");
        if (!nav) return;

        nav.querySelectorAll(".mobile-bottom-link").forEach((item) => {
            const active = item === link;
            item.classList.toggle("is-active", active);
            if (active) {
                item.setAttribute("aria-current", "page");
                item.dataset.navPending = "true";
            } else {
                item.removeAttribute("aria-current");
                item.removeAttribute("data-nav-pending");
            }
        });
    };

    const clearPending = () => {
        document.documentElement.classList.remove("app-navigating");

        document
            .querySelectorAll('[data-nav-pending="true"]')
            .forEach((element) => {
                element.removeAttribute("data-nav-pending");
            });
    };

    const primeLink = (event) => {
        const link = closestAnchor(event.target);

        if (!(link instanceof HTMLAnchorElement)) return;

        const isPrimary =
            link.closest("[data-animated-nav]")
            || link.closest(".mobile-bottom-nav")
            || link.closest("[data-mobile-drawer]");

        if (!isPrimary) return;

        prefetch(link);
    };

    const immediateFeedback = (event) => {
        const link = closestAnchor(event.target);

        if (!(link instanceof HTMLAnchorElement)) return;

        if (link.closest("[data-animated-nav]")) {
            moveDesktopIndicator(link);
            link.dataset.navPending = "true";
        }

        if (link.classList.contains("mobile-bottom-link")) {
            markBottomPending(link);
        }

        if (link.classList.contains("mobile-drawer-link")) {
            link.dataset.navPending = "true";
        }
    };

    const navigationStarted = (event) => {
        const link = closestAnchor(event.target);

        if (!(link instanceof HTMLAnchorElement)) return;

        const url = sameOriginUrl(link.href);
        if (!url) return;

        if (
            event.defaultPrevented
            || event.button > 0
            || event.metaKey
            || event.ctrlKey
            || event.shiftKey
            || event.altKey
            || link.target === "_blank"
            || link.hasAttribute("download")
        ) {
            return;
        }

        document.documentElement.classList.add("app-navigating");
    };

    document.addEventListener(
        "pointerdown",
        immediateFeedback,
        { passive: true }
    );

    document.addEventListener(
        "touchstart",
        primeLink,
        { passive: true, capture: true }
    );

    document.addEventListener(
        "pointerenter",
        primeLink,
        { passive: true, capture: true }
    );

    document.addEventListener(
        "focusin",
        primeLink,
        true
    );

    document.addEventListener(
        "click",
        navigationStarted,
        true
    );

    window.addEventListener(
        "pageshow",
        clearPending
    );
})();
