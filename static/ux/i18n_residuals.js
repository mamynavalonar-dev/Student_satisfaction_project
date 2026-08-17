(() => {
    "use strict";

    const isEnglish = () =>
        (document.documentElement.lang || "").toLowerCase().startsWith("en");

    if (!isEnglish()) return;

    const exact = new Map([
        ["Données", "Data"],

        ["Ce prédicteur utilise un", "This predictor uses an"],
        ["réseau de neurones MLP", "MLP neural network"],
        ["entraîné sur des données d'avis étudiants.", "trained on student feedback data."],
        ["entraîné sur des données d’avis étudiants.", "trained on student feedback data."],
        ["entraîné of des données d'avis étudiants.", "trained on student feedback data."],
        ["entraîné of des données d’avis étudiants.", "trained on student feedback data."],

        ["Choisir un fichier", "Choose CSV file"],
        ["Aucun fichier choisi", "No file selected"],
        ["Notes optionnelles sur cet entraînement...", "Optional notes for this training run..."],
        ["Le fichier CSV doit contenir les colonnes :", "The CSV file must contain the columns:"],
        ["Le fichier CSV doit contenir les colonnes:", "The CSV file must contain the columns:"],
        ["Binaire 1 (satisfait) ou 0 (non satisfait)", "Binary 1 (satisfied) or 0 (dissatisfied)"],

        ["Couches cachées :", "Hidden layers:"],
        ["Couches cachées:", "Hidden layers:"],
        ["Régularisation :", "Regularization:"],
        ["Régularisation:", "Regularization:"],
        ["Sélection :", "Selection:"],
        ["Sélection:", "Selection:"],
        ["Validation croisée :", "Cross-validation:"],
        ["Validation croisée:", "Cross-validation:"],
        ["Archivé", "Archived"],
        ["Fichier joblib introuvable.", "Joblib file not found."],
        ["Entraîner un modèle", "Train a model"],

        ["Présentiel", "In person"],
        ["Distanciel", "Online"],
        ["Hybride", "Hybrid"],

        ["Taux satisfait prédit (%)", "Predicted satisfaction rate (%)"],
        ["Cette mesure décrit ce que le MLP actif utilise pour prédire.", "This measure describes what the active MLP uses for prediction."],
        ["Elle est différente des « Observed Associations » et ne constitue pas une preuve de causalité.", "It differs from “Observed Associations” and is not evidence of causality."],
        ["Méthode : Importance par permutation", "Method: Permutation importance"],
        ["Méthode: Importance par permutation", "Method: Permutation importance"],
        ["Référence : jeu de test enregistré avec le modèle.", "Reference: test set stored with the model."],
        ["Référence: jeu de test enregistré avec le modèle.", "Reference: test set stored with the model."],

        ["Qualité de l'enseignement", "Teaching quality"],
        ["Qualité de l’enseignement", "Teaching quality"],
        ["Interactivité", "Interactivity"],
        ["Charge de travail", "Workload"],
        ["Type de cours", "Course type"],
        ["Niveau étudiant", "Student level"],

        ["Profil", "Profile"],
        ["Actualisation automatique", "Automatic refresh"],
        ["Tout lire", "Mark all read"],
        ["Aucune notification pour le moment.", "No notifications yet."],
        ["Fermer", "Close"]
    ]);

    const replacements = [
        [
            /seulement\s+(\d+)\s+prédictions?\s+enregistrées?\./gi,
            (_, count) => `only ${count} recorded prediction${count === "1" ? "" : "s"}.`
        ],
        [
            /Les taux par sous-groupes et les associations observées peuvent varier fortement avec si peu de données\.\s*Ils doivent être interprétés comme des indications descriptives, pas comme des conclusions générales\./gi,
            "Subgroup rates and observed associations may vary substantially with so little data. They should be interpreted as descriptive indications, not general conclusions."
        ],
        [
            /Enregistré avec scikit-learn\s+([^,]+),\s*environnement actuel\s+([^.]+)\.\s*Réentraîner ce modèle avant de l'activer\./gi,
            (_, saved, current) =>
                `Saved with scikit-learn ${saved}; current environment ${current}. Retrain this model before activation.`
        ],
        [
            /(\d+)\s+plis stratifiés/gi,
            (_, folds) => `${folds} stratified folds`
        ],
        [
            /(\([^)]*\))\s+neurones\b/gi,
            (_, architecture) => `${architecture} neurons`
        ],
        [
            /Ce graphique compare la précision des entraînements successifs, du plus ancien au plus récent\.\s*Chaque point correspond à un entraînement distinct\s*;\s*il ne s'agit pas d'un apprentissage continu\./gi,
            "This chart compares successive training accuracies from oldest to newest. Each point represents a distinct training run; this is not continuous learning."
        ],
        [
            /\*\s*signifie qu'un ancien artefact ne contient pas les métriques détaillées\.\s*L'activation ne supprime aucun fichier et ne réentraîne pas le réseau\./gi,
            "* means that a legacy artifact does not contain detailed metrics. Activation does not delete any file and does not retrain the network."
        ],
        [
            /Le fichier CSV doit contenir les colonnes\s*:\s*/gi,
            "The CSV file must contain the columns: "
        ],
        [
            /\bsatisfaction\s*\(0\s*ou\s*1\)/gi,
            "satisfaction (0 or 1)"
        ],
        [
            /\b1\s*\(satisfait\)\s*ou\s*0\s*\(non satisfait\)/gi,
            "1 (satisfied) or 0 (dissatisfied)"
        ]
    ];

    const excludedTags = new Set([
        "SCRIPT", "STYLE", "CODE", "PRE", "NOSCRIPT"
    ]);

    function translateString(value) {
        if (!value) return value;

        const leading = value.match(/^\s*/)?.[0] || "";
        const trailing = value.match(/\s*$/)?.[0] || "";
        let core = value.trim();

        if (!core) return value;

        if (exact.has(core)) {
            core = exact.get(core);
        }

        for (const [pattern, replacement] of replacements) {
            core = core.replace(pattern, replacement);
        }

        return leading + core + trailing;
    }

    function translateTextNodes(root) {
        if (!root) return;

        const walker = document.createTreeWalker(
            root,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode(node) {
                    const parent = node.parentElement;
                    if (!parent || excludedTags.has(parent.tagName)) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    return node.nodeValue && node.nodeValue.trim()
                        ? NodeFilter.FILTER_ACCEPT
                        : NodeFilter.FILTER_REJECT;
                }
            }
        );

        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);

        for (const node of nodes) {
            const translated = translateString(node.nodeValue);
            if (translated !== node.nodeValue) {
                node.nodeValue = translated;
            }
        }
    }

    const attributeNames = [
        "placeholder",
        "title",
        "aria-label",
        "data-confirm",
        "data-message",
        "data-title"
    ];

    function translateAttributes(root) {
        const elements = [];

        if (root.nodeType === Node.ELEMENT_NODE) elements.push(root);
        if (root.querySelectorAll) elements.push(...root.querySelectorAll("*"));

        for (const element of elements) {
            for (const attribute of attributeNames) {
                if (!element.hasAttribute(attribute)) continue;
                const oldValue = element.getAttribute(attribute);
                const newValue = translateString(oldValue);
                if (newValue !== oldValue) {
                    element.setAttribute(attribute, newValue);
                }
            }
        }
    }

    function translateCharts() {
        if (!window.Chart || !Chart.instances) return;

        const instances = Array.isArray(Chart.instances)
            ? Chart.instances
            : Object.values(Chart.instances);

        for (const chart of instances) {
            if (!chart?.data) continue;

            if (Array.isArray(chart.data.labels)) {
                chart.data.labels = chart.data.labels.map((label) =>
                    typeof label === "string" ? translateString(label) : label
                );
            }

            for (const dataset of chart.data.datasets || []) {
                if (typeof dataset.label === "string") {
                    dataset.label = translateString(dataset.label);
                }
            }

            chart.update("none");
        }
    }

    function enhanceFileInputs() {
        document.querySelectorAll('input[type="file"]').forEach((input, index) => {
            if (input.dataset.i18nEnhanced === "true") return;

            input.dataset.i18nEnhanced = "true";

            if (!input.id) {
                input.id = `i18n-file-${index + 1}`;
            }

            input.classList.add("i18n-file-native");

            const wrapper = document.createElement("div");
            wrapper.className = "i18n-file-control";

            const choose = document.createElement("label");
            choose.className = "i18n-file-button";
            choose.htmlFor = input.id;
            choose.textContent = "Choose CSV file";

            const filename = document.createElement("span");
            filename.className = "i18n-file-name";
            filename.textContent = input.files?.[0]?.name || "No file selected";

            input.insertAdjacentElement("afterend", wrapper);
            wrapper.append(choose, filename);

            input.addEventListener("change", () => {
                filename.textContent =
                    input.files?.[0]?.name || "No file selected";
            });
        });
    }

    function translateRoot(root = document.body) {
        if (!isEnglish() || !root) return;
        translateTextNodes(root);
        translateAttributes(root);
        enhanceFileInputs();
    }

    function run() {
        translateRoot(document.body);

        requestAnimationFrame(() => {
            translateCharts();
            setTimeout(translateCharts, 250);
        });

        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        translateRoot(node);
                    } else if (node.nodeType === Node.TEXT_NODE) {
                        const parent = node.parentElement;
                        if (parent && !excludedTags.has(parent.tagName)) {
                            const translated = translateString(node.nodeValue);
                            if (translated !== node.nodeValue) {
                                node.nodeValue = translated;
                            }
                        }
                    }
                }
            }
            translateCharts();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", run, { once: true });
    } else {
        run();
    }
})();
