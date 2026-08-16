document.addEventListener('DOMContentLoaded', () => {
    const card = document.querySelector('[data-auth-card]');
    if (!card) return;

    const tabs = Array.from(card.querySelectorAll('[data-auth-target]'));
    const panels = Array.from(card.querySelectorAll('[data-auth-panel]'));

    const setPanel = (panelName, focusPanel = false) => {
        const safePanel = panelName === 'register' ? 'register' : 'login';
        card.dataset.panel = safePanel;

        tabs.forEach((tab) => {
            const selected = tab.dataset.authTarget === safePanel;
            tab.setAttribute('aria-selected', selected ? 'true' : 'false');
            tab.tabIndex = selected ? 0 : -1;
        });

        panels.forEach((panel) => {
            const selected = panel.dataset.authPanel === safePanel;
            panel.setAttribute('aria-hidden', selected ? 'false' : 'true');
        });

        if (focusPanel) {
            const selectedPanel = panels.find((panel) => panel.dataset.authPanel === safePanel);
            const firstInput = selectedPanel?.querySelector('input:not([type="hidden"])');
            firstInput?.focus();
        }
    };

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => setPanel(tab.dataset.authTarget, true));
        tab.addEventListener('keydown', (event) => {
            if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
            event.preventDefault();
            const currentIndex = tabs.indexOf(tab);
            const offset = event.key === 'ArrowRight' ? 1 : -1;
            const nextTab = tabs[(currentIndex + offset + tabs.length) % tabs.length];
            setPanel(nextTab.dataset.authTarget, true);
            nextTab.focus();
        });
    });

    setPanel(card.dataset.panel, false);
});

// V6 — afficher / masquer le nom d'utilisateur et le mot de passe.
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-visibility-target]').forEach((button) => {
        const input = document.getElementById(button.dataset.visibilityTarget);
        if (!input) return;

        const openIcon = button.querySelector('.auth-eye-open');
        const closedIcon = button.querySelector('.auth-eye-closed');

        const sync = () => {
            const visible = input.type !== 'password';
            button.setAttribute('aria-pressed', visible ? 'true' : 'false');
            button.setAttribute(
                'aria-label',
                visible
                    ? (input.name.includes('username') ? "Masquer le nom d'utilisateur" : 'Masquer le mot de passe')
                    : (input.name.includes('username') ? "Afficher le nom d'utilisateur" : 'Afficher le mot de passe')
            );
            // Icône = action disponible :
            // texte masqué  -> œil ouvert  = afficher
            // texte visible -> œil barré   = masquer
            if (openIcon) openIcon.hidden = visible;
            if (closedIcon) closedIcon.hidden = !visible;
        };

        button.addEventListener('click', () => {
            const start = input.selectionStart;
            const end = input.selectionEnd;
            input.type = input.type === 'password' ? 'text' : 'password';
            sync();
            input.focus({ preventScroll: true });
            try { input.setSelectionRange(start, end); } catch (_) {}
        });

        sync();
    });

    document.querySelectorAll('[data-auth-flash]').forEach((flash) => {
        window.setTimeout(() => {
            flash.style.transition = 'opacity .25s ease, transform .25s ease';
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-4px)';
            window.setTimeout(() => flash.remove(), 260);
        }, 4500);
    });
});

// V6.4 — rendu robuste de l'icône show/hide.
// On ne dépend plus des deux anciens SVG + attribut hidden.
// Une seule icône est reconstruite d'après l'état RÉEL du champ.
document.addEventListener('DOMContentLoaded', () => {
    const OPEN_EYE = `
        <svg class="auth-eye auth-eye-dynamic" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M2.25 12s3.75-6.75 9.75-6.75S21.75 12 21.75 12 18 18.75 12 18.75 2.25 12 2.25 12Z"></path>
            <circle cx="12" cy="12" r="2.75"></circle>
        </svg>`;

    const CLOSED_EYE = `
        <svg class="auth-eye auth-eye-dynamic" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M3 3 21 21"></path>
            <path d="M10.58 10.58a2 2 0 0 0 2.84 2.84"></path>
            <path d="M9.9 5.1A9.8 9.8 0 0 1 12 4.85c6.2 0 9.75 7.15 9.75 7.15a16.8 16.8 0 0 1-3.05 4.15"></path>
            <path d="M6.2 6.2C3.7 8 2.25 12 2.25 12S6 19.15 12 19.15a10.1 10.1 0 0 0 4.15-.85"></path>
        </svg>`;

    const renderIcon = (button, input) => {
        // L'icône représente l'ACTION disponible :
        // - champ masqué  => œil ouvert : cliquer pour afficher
        // - champ visible => œil barré  : cliquer pour masquer
        const visible = input.type !== 'password';
        button.innerHTML = visible ? CLOSED_EYE : OPEN_EYE;
        button.setAttribute('aria-pressed', visible ? 'true' : 'false');

        const isUsername = input.name.includes('username');
        button.setAttribute(
            'aria-label',
            visible
                ? (isUsername ? "Masquer le nom d'utilisateur" : "Masquer le mot de passe")
                : (isUsername ? "Afficher le nom d'utilisateur" : "Afficher le mot de passe")
        );
    };

    document.querySelectorAll('[data-visibility-target]').forEach((button) => {
        const input = document.getElementById(button.dataset.visibilityTarget);
        if (!input) return;

        // État initial.
        renderIcon(button, input);

        // Le listener V6 existant bascule d'abord le type du champ.
        // Ce listener, enregistré après, redessine ensuite l'icône
        // à partir de l'état réellement obtenu.
        button.addEventListener('click', () => {
            window.requestAnimationFrame(() => renderIcon(button, input));
        });
    });
});

