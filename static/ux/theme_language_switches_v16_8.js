/* V16.8_SWITCH_CONTROLS_START */
(() => {
    "use strict";

    const root = document.documentElement;
    const THEME_KEY = "student-satisfaction-theme";
    const DRAWER_KEY = "student-satisfaction-mobile-drawer-open";

    const escapeText = (value, fallback) => {
        const text = String(value || "").trim();
        return text || fallback;
    };

    /* =====================================================
       Theme
       ===================================================== */

    const currentEffectiveTheme = () => {
        const datasetTheme = root.dataset.appTheme;

        if (datasetTheme === "dark" || datasetTheme === "light") {
            return datasetTheme;
        }

        return (
            window.matchMedia
            && window.matchMedia("(prefers-color-scheme: dark)").matches
        )
            ? "dark"
            : "light";
    };

    const updateThemeMeta = (theme) => {
        const meta = document.querySelector(
            'meta[name="theme-color"]'
        );

        if (meta) {
            meta.setAttribute(
                "content",
                theme === "dark" ? "#0f1926" : "#ffffff"
            );
        }
    };

    const setThemeExplicit = (theme) => {
        if (theme !== "dark" && theme !== "light") return;

        try {
            localStorage.setItem(THEME_KEY, theme);
        } catch (_) {
            /* Storage may be unavailable; the current document still updates. */
        }

        root.dataset.themePreference = theme;
        root.dataset.appTheme = theme;
        root.style.colorScheme = theme;

        updateThemeMeta(theme);

        window.dispatchEvent(
            new CustomEvent(
                "app-theme-change",
                {
                    detail: {
                        preference: theme,
                        effective: theme,
                    },
                }
            )
        );
    };

    const themeCheckboxes = new Set();

    const syncThemeSwitches = () => {
        const dark = currentEffectiveTheme() === "dark";

        themeCheckboxes.forEach((checkbox) => {
            checkbox.checked = dark;
            checkbox.setAttribute(
                "aria-checked",
                String(dark)
            );
        });
    };

    const buildThemeSwitch = ({
        extraClass = "",
        label = "",
    } = {}) => {
        const wrapper = document.createElement("label");
        wrapper.className =
            `ui-switch v168-theme-switch ${extraClass}`.trim();

        if (label) {
            wrapper.title = label;
        }

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.setAttribute("role", "switch");
        checkbox.setAttribute(
            "aria-label",
            label || "Change theme"
        );

        const slider = document.createElement("span");
        slider.className = "slider";
        slider.setAttribute("aria-hidden", "true");

        const circle = document.createElement("span");
        circle.className = "circle";

        slider.appendChild(circle);
        wrapper.append(checkbox, slider);

        themeCheckboxes.add(checkbox);

        checkbox.addEventListener(
            "change",
            () => {
                /* V16.13.3_SMOOTH_THEME_CHANGE
                   Same-document transition only: no navigation/reload. */
                const applyTheme = () => {
                    setThemeExplicit(
                        checkbox.checked ? "dark" : "light"
                    );
                    syncThemeSwitches();
                };

                const reducedMotion = (
                    window.matchMedia
                    && window.matchMedia(
                        "(prefers-reduced-motion: reduce)"
                    ).matches
                );

                if (
                    !reducedMotion
                    && typeof document.startViewTransition === "function"
                ) {
                    document.startViewTransition(
                        applyTheme
                    );
                } else {
                    applyTheme();
                }
            }
        );

        return {
            wrapper,
            checkbox,
        };
    };

    const enhanceTopbarTheme = () => {
        const legacy = document.querySelector(
            "[data-theme-toggle]"
        );

        if (!legacy) return;

        if (
            document.querySelector(
                ".v168-topbar-theme-switch"
            )
        ) {
            return;
        }

        const i18n = window.APP_I18N || {};
        const label = escapeText(
            i18n.changeTheme,
            "Change theme"
        );

        const { wrapper } = buildThemeSwitch({
            extraClass: "v168-topbar-theme-switch",
            label,
        });

        legacy.insertAdjacentElement(
            "afterend",
            wrapper
        );

        legacy.classList.add("v168-legacy-control");
        legacy.setAttribute("aria-hidden", "true");
        legacy.tabIndex = -1;
    };

    const enhanceDrawerTheme = () => {
        const legacy = document.querySelector(
            "[data-mobile-theme-cycle]"
        );

        if (!legacy) return;

        if (
            document.querySelector(
                ".mobile-drawer-theme-switch-row"
            )
        ) {
            return;
        }

        const labelText = escapeText(
            legacy.textContent,
            (
                window.APP_I18N
                && window.APP_I18N.changeTheme
            )
                || "Change theme"
        );

        const row = document.createElement("div");
        row.className = "mobile-drawer-theme-switch-row";

        const label = document.createElement("span");
        label.className =
            "mobile-drawer-theme-switch-label";

        const icon = document.createElement("i");
        icon.className = "bi bi-circle-half";
        icon.setAttribute("aria-hidden", "true");

        const text = document.createElement("span");
        text.textContent = labelText;

        label.append(icon, text);

        const { wrapper } = buildThemeSwitch({
            label: labelText,
        });

        row.append(label, wrapper);

        legacy.insertAdjacentElement(
            "beforebegin",
            row
        );

        legacy.classList.add("v168-legacy-control");
        legacy.setAttribute("aria-hidden", "true");
        legacy.tabIndex = -1;
    };

    /* =====================================================
       Language
       ===================================================== */

    const languageCheckboxes = new Set();

    const currentLanguage = () => {
        const lang = (
            root.getAttribute("lang")
            || "fr"
        ).toLowerCase();

        return lang.startsWith("en") ? "en" : "fr";
    };

    const persistDrawerOpenIfNeeded = () => {
        if (
            !document.body.classList.contains(
                "mobile-nav-open"
            )
        ) {
            return;
        }

        try {
            sessionStorage.setItem(
                DRAWER_KEY,
                "1"
            );
        } catch (_) {
            /* Optional enhancement only. */
        }
    };

    /* V16.13.6_LANGUAGE_DELEGATE */
    const submitLanguage = (
        form,
        language
    ) => {
        const submitter =
            form.querySelector(
                `button[name="language"][value="${language}"]`
            );

        if (
            !(
                submitter
                instanceof HTMLButtonElement
            )
        ) {
            return false;
        }

        persistDrawerOpenIfNeeded();

        const api =
            window
                .StudentSatisfactionLanguageV16136;

        if (
            api
            && typeof api.change
                === "function"
        ) {
            api.change(
                form,
                language,
                submitter
            );

            return true;
        }

        if (
            typeof form.requestSubmit
                === "function"
        ) {
            form.requestSubmit(submitter);
        } else {
            submitter.click();
        }

        return true;
    };

    const buildLanguageSwitch = (
        form
    ) => {
        const control = document.createElement("div");
        control.className =
            "button r v168-language-switch";

        const checkbox = document.createElement("input");
        checkbox.className = "checkbox";
        checkbox.type = "checkbox";
        checkbox.setAttribute("role", "switch");
        checkbox.setAttribute(
            "aria-label",
            "FR / EN"
        );

        const knobs = document.createElement("span");
        knobs.className = "knobs";
        knobs.setAttribute("aria-hidden", "true");

        const layer = document.createElement("span");
        layer.className = "layer";
        layer.setAttribute("aria-hidden", "true");

        control.append(
            checkbox,
            knobs,
            layer
        );

        languageCheckboxes.add(checkbox);

        checkbox.addEventListener(
            "change",
            () => {
                const language =
                    checkbox.checked ? "en" : "fr";

                checkbox.disabled = true;
                control.setAttribute(
                    "aria-busy",
                    "true"
                );

                if (!submitLanguage(form, language)) {
                    checkbox.disabled = false;
                    control.removeAttribute("aria-busy");
                    checkbox.checked =
                        currentLanguage() === "en";
                }
            }
        );

        return control;
    };

    const enhanceLanguageForm = (
        form
    ) => {
        if (
            !(form instanceof HTMLFormElement)
            || form.classList.contains(
                "v168-enhanced-locale"
            )
        ) {
            return;
        }

        const fr = form.querySelector(
            'button[name="language"][value="fr"]'
        );
        const en = form.querySelector(
            'button[name="language"][value="en"]'
        );

        if (!fr || !en) return;

        const control = buildLanguageSwitch(
            form
        );

        form.appendChild(control);
        form.classList.add(
            "v168-enhanced-locale"
        );
    };

    const syncLanguageSwitches = () => {
        const english =
            currentLanguage() === "en";

        languageCheckboxes.forEach(
            (checkbox) => {
                checkbox.checked = english;
                checkbox.disabled = false;
                checkbox
                    .closest(".v168-language-switch")
                    ?.removeAttribute("aria-busy");
            }
        );
    };

    /* =====================================================
       Init / synchronization
       ===================================================== */

    const init = () => {
        enhanceTopbarTheme();
        enhanceDrawerTheme();

        document
            .querySelectorAll(
                ".app-locale-switch, .mobile-drawer-locale"
            )
            .forEach(enhanceLanguageForm);

        syncThemeSwitches();
        syncLanguageSwitches();

        const themeObserver = new MutationObserver(
            (mutations) => {
                const themeChanged = mutations.some(
                    (mutation) => (
                        mutation.type === "attributes"
                        && (
                            mutation.attributeName
                                === "data-app-theme"
                            || mutation.attributeName
                                === "data-theme-preference"
                        )
                    )
                );

                if (themeChanged) {
                    syncThemeSwitches();
                }
            }
        );

        themeObserver.observe(
            root,
            {
                attributes: true,
                attributeFilter: [
                    "data-app-theme",
                    "data-theme-preference",
                ],
            }
        );

        window.addEventListener(
            "app-theme-change",
            syncThemeSwitches
        );

        window.addEventListener(
            "pageshow",
            () => {
                syncThemeSwitches();
                syncLanguageSwitches();
            }
        );
    };

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            init,
            { once: true }
        );
    } else {
        init();
    }
})();
/* V16.8_SWITCH_CONTROLS_END */
