import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("budget_dashboard_tour", {
    steps: () => [
        {
            content: "Open the budget dashboard",
            trigger: ".o_dashboard_name:contains('Budget')",
            run: "click",
        },
        {
            content: "The key figures and the monthly chart are rendered",
            trigger: ".o-figure",
            run() {
                // 4 key figures and the monthly chart
                const count = document.querySelectorAll(".o-figure").length;
                if (count !== 5) {
                    throw new Error(`Expected 5 figures, found ${count}`);
                }
            },
        },
    ],
});
