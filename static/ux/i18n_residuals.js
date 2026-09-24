(() => {
    "use strict";

    const isEnglish = () =>
        (document.documentElement.lang || "").toLowerCase().startsWith("en");

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

        ["Insatisfait", "Dissatisfied"],
        ["Plutôt insatisfait / Peu satisfait", "Somewhat dissatisfied / Slightly satisfied"],
        ["Neutre / Sans opinion", "Neutral / No opinion"],
        ["Plutôt satisfait / Assez satisfait", "Somewhat satisfied / Fairly satisfied"],
        ["Satisfait", "Satisfied"],
        ["Léger", "Light"],
        ["Plutôt léger / Assez léger", "Somewhat light / Fairly light"],
        ["Moyen / Modéré", "Medium / Moderate"],
        ["Plutôt lourd / Assez lourd", "Somewhat heavy / Fairly heavy"],
        ["Lourd", "Heavy"],
        ["Non interactif", "Non-interactive"],
        ["Peu interactif / Plutôt passif", "Slightly interactive / Mostly passive"],
        ["Neutre / Interaction moyenne", "Neutral / Average interaction"],
        ["Plutôt interactif / Assez interactif", "Somewhat interactive / Fairly interactive"],
        ["Interactif", "Interactive"],

        ["Résultat de la Prediction", "Prediction result"],
        ["Résultat de la Prédiction", "Prediction result"],
        ["Confidence de la prédiction:", "Prediction confidence:"],
        ["Confiance de la prédiction:", "Prediction confidence:"],
        ["Données utilisées:", "Input data:"],
        ["Quality enseignement:", "Teaching quality:"],
        ["Qualité enseignement:", "Teaching quality:"],
        ["Contribution de chaque caractéristique à la probabilité d'être satisfait.", "Contribution of each feature to the probability of being satisfied."],
        ["💡 Recommandations:", "💡 Recommendations:"],
        ["Pour améliorer la satisfaction:", "To improve satisfaction:"],
        ["Points forts identifiés:", "Identified strengths:"],
        ["Améliorer la qualité de l'enseignement.", "Improve teaching quality."],
        ["Augmenter l'interactivité des cours.", "Increase course interactivity."],
        ["Envisager de réduire la charge de travail.", "Consider reducing the workload."],
        ["La charge de travail est peut-être trop légère, vérifier si le contenu est suffisant.", "The workload may be too light; check whether the course content is sufficient."],
        ["Analyser les retours qualitatifs pour identifier des points d'amélioration spécifiques.", "Analyze qualitative feedback to identify specific areas for improvement."],
        ["Excellente qualité d'enseignement perçue.", "Excellent perceived teaching quality."],
        ["Très bonne interactivité en cours.", "Very good course interactivity."],
        ["La charge de travail semble bien équilibrée.", "The workload appears well balanced."],
        ["La configuration générale du cours est favorable à la satisfaction.", "The overall course configuration supports student satisfaction."],
        ["Nouvelle Prediction", "New prediction"],
        ["Nouvelle Prédiction", "New prediction"],
        ["Prediction en cours...", "Prediction in progress..."],
        ["Prédiction en cours...", "Prediction in progress..."],

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
        [/^Non Satisfied\s*\(/, "Dissatisfied ("],
        [/(\d+(?:[.,]\d+)?%)\s+satisfait\b/g, "$1 satisfied"],
        [
            /Une contribution positive augmente cette probabilité\s*;\s*une contribution négative la diminue\./g,
            "A positive contribution increases this probability; a negative contribution decreases it."
        ],
        [
            /Valeurs de Shapley exactes sur la probabilité d'être satisfait/g,
            "Exact Shapley values for the probability of being satisfied"
        ],
        [/échantillon d'entraînement enregistré avec le modèle/g, "training sample saved with the model"],
        [
            /Ces contributions expliquent le comportement prédictif du modèle\s*;\s*elles ne prouvent pas une relation causale\./g,
            "These contributions explain the model's predictive behavior; they do not prove a causal relationship."
        ],
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
        if (!isEnglish()) return;
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
            if (!isEnglish()) return;
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

        // The document survives FR/EN switches. Keep the translator registered
        // after a French startup, and evaluate the current language each time.
        window.addEventListener("v16137:language-changed", () => {
            translateRoot(document.body);
            translateCharts();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", run, { once: true });
    } else {
        run();
    }
})();
