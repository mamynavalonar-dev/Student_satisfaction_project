(() => {
    "use strict";

    const STORAGE_KEY = "student-satisfaction-theme";
    const VALID = new Set(["auto", "light", "dark"]);
    const root = document.documentElement;
    const media = window.matchMedia("(prefers-color-scheme: dark)");

    function readPreference() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            return VALID.has(stored) ? stored : "auto";
        } catch (_) {
            return "auto";
        }
    }

    function effectiveTheme(preference) {
        if (preference === "auto") {
            return media.matches ? "dark" : "light";
        }
        return preference;
    }

    function updateThemeColor(effective) {
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.setAttribute("content", effective === "dark" ? "#0f1722" : "#ffffff");
        }
    }

    function updateChartTheme(effective) {
        if (!window.Chart) return;

        const textColor = effective === "dark" ? "#d8e3f1" : "#495057";
        const gridColor = effective === "dark"
            ? "rgba(184, 197, 215, .18)"
            : "rgba(0, 0, 0, .10)";

        try {
            window.Chart.defaults.color = textColor;
            window.Chart.defaults.borderColor = gridColor;

            const instances = window.Chart.instances || {};
            Object.values(instances).forEach((chart) => {
                if (!chart || !chart.options) return;

                const scales = chart.options.scales || {};
                Object.values(scales).forEach((scale) => {
                    if (!scale) return;
                    scale.ticks = scale.ticks || {};
                    scale.grid = scale.grid || {};
                    scale.ticks.color = textColor;
                    scale.grid.color = gridColor;
                });

                if (chart.options.plugins &&
                    chart.options.plugins.legend &&
                    chart.options.plugins.legend.labels) {
                    chart.options.plugins.legend.labels.color = textColor;
                }

                chart.update("none");
            });
        } catch (_) {}
    }

    function syncButtons(preference, effective) {
        const ui = window.APP_I18N || {};
        const labels = {
            auto: ui.themeAuto || "Automatique",
            light: ui.themeLight || "Clair",
            dark: ui.themeDark || "Sombre",
        };
        const themeWord = ui.theme || "Thème";
        const changeTheme = ui.changeTheme || "Changer le thème";

        document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
            const readable = labels[preference] || labels.auto;
            button.setAttribute("aria-label", `${themeWord} : ${readable}. ${changeTheme}`);
            button.setAttribute("title", `${themeWord} : ${readable}`);
            button.setAttribute("data-effective-theme", effective);

            const status = button.querySelector("[data-theme-status]");
            if (status) status.textContent = `${themeWord} ${readable}`;
        });
    }

    function apply(preference, persist = true) {
        const safePreference = VALID.has(preference) ? preference : "auto";
        const effective = effectiveTheme(safePreference);

        root.dataset.themePreference = safePreference;
        root.dataset.appTheme = effective;
        root.style.colorScheme = effective;

        if (persist) {
            try {
                localStorage.setItem(STORAGE_KEY, safePreference);
            } catch (_) {}
        }

        updateThemeColor(effective);
        syncButtons(safePreference, effective);
        updateChartTheme(effective);

        window.dispatchEvent(new CustomEvent("app-theme-change", {
            detail: {
                preference: safePreference,
                effectiveTheme: effective,
            },
        }));
    }

    function cycle() {
        const current = root.dataset.themePreference || readPreference();
        const next = current === "auto" ? "light" : current === "light" ? "dark" : "auto";
        apply(next, true);
    }

    function onSystemThemeChange() {
        const preference = root.dataset.themePreference || readPreference();
        if (preference === "auto") apply("auto", false);
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
            button.addEventListener("click", cycle);
        });
        apply(readPreference(), false);
    });

    if (typeof media.addEventListener === "function") {
        media.addEventListener("change", onSystemThemeChange);
    } else if (typeof media.addListener === "function") {
        media.addListener(onSystemThemeChange);
    }
})();
