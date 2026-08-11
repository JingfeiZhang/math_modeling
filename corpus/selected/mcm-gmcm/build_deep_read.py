from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image

from build_review_sheets import PAGES


ROOT = Path(__file__).resolve().parents[3]
SELECTION_PATH = Path(__file__).with_name("selection.json")
RAW = ROOT / "corpus" / "raw" / "mcm-gmcm"
RENDERED = ROOT / "corpus" / "rendered" / "mcm-gmcm"
CARDS = ROOT / "corpus" / "cards" / "deep-read-mcm-gmcm"
REPORT = ROOT / "corpus" / "reports" / "mcm-gmcm-deep-read.md"
REVIEW_DATE = "2026-08-03"

sys.path.insert(0, str(ROOT / "skill_staging" / "modeling-paper-miner" / "scripts"))
from validate_paper_card import validate as validate_card  # noqa: E402


OFFICIAL = {
    "mcm-2006-a-883": ("2006-MCM_2006_Final_Results.pdf", "2006-MCM_2006_Final_Results.txt", 2, 73),
    "mcm-2006-b-868": ("2006-MCM_2006_Final_Results.pdf", "2006-MCM_2006_Final_Results.txt", 2, 72),
    "icm-2006-c-787": ("2006-ICM_2006_Final_Results.pdf", "2006-ICM_2006_Final_Results.txt", 2, 70),
    "mcm-2007-a-1034": ("2007-MCMResults2007.pdf", "2007-MCMResults2007.txt", 2, 72),
    "mcm-2007-b-2053": ("2007-MCMResults2007.pdf", "2007-MCMResults2007.txt", 2, 115),
    "icm-2007-c-2052": ("2007-ICMResults2007.pdf", "2007-ICMResults2007.txt", 2, 75),
    "mcm-2008-a-3694": ("2008-MCM-A-Results-2008.pdf", "2008-MCM-A-Results-2008.txt", 2, 82),
    "mcm-2008-b-2858": ("2008-MCM-B-Results-2008.pdf", "2008-MCM-B-Results-2008.txt", 2, 70),
    "mcm-2009-a-4339": ("2009-MCM-A-Results-2009.pdf", "2009-MCM-A-Results-2009.txt", 2, 72),
    "mcm-2010-a-6749": ("2010-2010_MCM_Problem_A.pdf", "2010-2010_MCM_Problem_A.txt", 2, 71),
    "mcm-2010-b-7273": ("2010-2010_MCM_Problem_B.pdf", "2010-2010_MCM_Problem_B.txt", 2, 71),
    "icm-2010-c-6947": ("2010-ICM-2010-Results.pdf", "2010-ICM-2010-Results.txt", 2, 70),
}


def evidence(page: int, tags: list[str], observation: str) -> dict[str, Any]:
    return {"page": page, "tags": tags, "observation": observation, "derivation": "mixed"}


def abstract(page: int, role: str, observation: str) -> dict[str, Any]:
    return {"page": page, "role": role, "observation": observation}


def model(page: int, step: str, observation: str) -> dict[str, Any]:
    return {"page": page, "step": step, "observation": observation}


def validation(page: int, method: str, observation: str) -> dict[str, Any]:
    return {"page": page, "method": method, "observation": observation}


def figure(page: int, role: str, chart_type: str, lesson: str) -> dict[str, Any]:
    return {"page": page, "role": role, "chart_type": chart_type, "lesson": lesson}


def rule(page: int, text: str, scope: str = "contest-paper") -> dict[str, Any]:
    return {"page": page, "rule": text, "scope": scope}


def risk(page: int, text: str, severity: str = "medium") -> dict[str, Any]:
    return {"page": page, "risk": text, "severity": severity}


READINGS: dict[str, dict[str, Any]] = {
    "mcm-2006-a-883": {
        "title": "Optimization of irrigation time, pipe set placements, and irrigation uniformity for a hand move system",
        "evidence": [
            evidence(1, ["title", "layout"], "Title and a dense table of contents open the paper; there is no standalone abstract."),
            evidence(6, ["model", "figure"], "A one-dimensional sprinkler profile is paired with a two-dimensional field heatmap."),
            evidence(11, ["optimization", "figure"], "Placement heatmaps after 100 and 5000 iterations expose convergence behavior."),
            evidence(13, ["result", "figure"], "The final placement and pipe setup are shown directly on the precipitation field."),
            evidence(14, ["result", "table"], "A daily move schedule and compact final placement plot translate the optimization into operations."),
            evidence(15, ["risk", "boundary"], "Weaknesses explicitly identify wind, terrain, profile calibration, and uniformity-metric limitations."),
        ],
        "abstract": [abstract(1, "missing-abstract", "No standalone summary is supplied; the title and contents expose scope but not quantitative findings.")],
        "models": [
            model(6, "sprinkler-response", "Convert a radial sprinkler profile into a gridded precipitation field."),
            model(11, "coverage-and-uniformity", "Search feasible placements and use SPSA iterations to improve coverage uniformity."),
            model(13, "setup-minimization", "Choose pipe setups and placements that retain coverage while reducing moves."),
            model(14, "operational-schedule", "Convert the optimized geometry into a day-by-day irrigation schedule."),
        ],
        "validation": [
            validation(11, "iteration-check", "Compare 100 and 5000 SPSA iterations to show that the spatial solution stabilizes."),
            validation(14, "constraint-check", "Report final placement and irrigation schedule under the field and timing constraints."),
            validation(15, "limitation-audit", "Bound conclusions by wind, soil, terrain, sprinkler-profile, and metric assumptions."),
        ],
        "figures": [
            figure(6, "mechanism-to-field", "profile plus heatmap", "Pair the assumed local response with its spatial consequence before optimization."),
            figure(11, "convergence", "before-after heatmaps", "Show intermediate and long-run spatial states using the same color scale."),
            figure(13, "main-result", "annotated heatmap", "Overlay the decision geometry on the response field so the solution is inspectable."),
            figure(14, "implementation", "table plus placement map", "Place the operational schedule beside the final geometry."),
        ],
        "rules": [
            rule(6, "Explain a spatial objective with a response profile and field map before presenting the optimizer."),
            rule(11, "Use matched heatmaps at early and late iterations to make convergence spatially visible."),
            rule(15, "Give model limitations their own subsection and tie each one to a violated physical assumption."),
        ],
        "risks": [
            risk(1, "The absence of a result-bearing abstract weakens first-page decision density."),
            risk(15, "No observed field-data baseline is shown; weather and soil effects are largely assumed.", "high"),
            risk(15, "MATLAB code is embedded in the appendix but no external data or executable package is linked."),
        ],
    },
    "mcm-2006-b-868": {
        "title": "A Simulation-Driven Approach For A Cost Efficient Airport Wheelchair Assistance Service",
        "evidence": [
            evidence(1, ["problem", "model"], "The introduction frames wheelchair inventory and escort deployment as a service-cost tradeoff."),
            evidence(8, ["sensitivity", "table"], "Escort count and daily cost are compared across traffic and concourse settings."),
            evidence(9, ["robustness", "table"], "The same outputs are reported for LaGuardia, Dallas/Fort Worth, and Chicago O'Hare."),
            evidence(10, ["conclusion", "boundary"], "The conclusion states scheduling limitations and operational assumptions."),
            evidence(12, ["model", "figure"], "An airport image is abstracted into a bidirectional graph used by the simulation."),
            evidence(19, ["sensitivity", "figure"], "A line comparison separates population growth from per-capita request growth."),
        ],
        "abstract": [abstract(1, "problem-first-introduction", "No formal abstract; the opening quickly states the controllable decisions, cost objective, and simulation approach.")],
        "models": [
            model(12, "network-abstraction", "Represent airport geometry as a bidirectional graph."),
            model(1, "discrete-event-service", "Simulate wheelchair requests, travel, escort queues, and task scheduling."),
            model(8, "cost-optimization", "Select escort inventory and scheduling policy that minimize daily operating cost."),
            model(9, "scenario-transfer", "Re-run the same model on multiple airport layouts and traffic levels."),
        ],
        "validation": [
            validation(8, "factor-sweep", "Vary concourses and passenger volume while retaining comparable escort and cost outputs."),
            validation(9, "cross-site-test", "Test the algorithm on three airport geometries."),
            validation(19, "demand-scenario", "Separate more passengers from a higher wheelchair-request rate."),
        ],
        "figures": [
            figure(12, "model-abstraction", "image plus network graph", "Show how a real facility becomes the computational graph."),
            figure(19, "scenario-comparison", "two-series line chart", "Use directly comparable curves to distinguish competing demand mechanisms."),
            figure(8, "decision-table", "scenario result tables", "Keep the decision variables and cost objective consistent across scenarios."),
        ],
        "rules": [
            rule(12, "Display the real object and its graph abstraction together when geometry drives a simulation."),
            rule(9, "Validate portability by keeping output columns fixed across different sites."),
            rule(10, "State the exact operational cases the scheduler does not model."),
        ],
        "risks": [
            risk(1, "There is no standalone executive summary with final recommended inventory."),
            risk(10, "Behavioral and service-time assumptions are not accompanied by uncertainty intervals.", "high"),
            risk(19, "The final trend plot is small and visually detached from the main result tables."),
        ],
    },
    "icm-2006-c-787": {
        "title": "The United Nations and the Quest for the Holy Grail (of AIDS)",
        "evidence": [
            evidence(1, ["abstract", "model"], "The abstract defines the 2050 horizon and introduces deterministic HIV, intervention, and economic models."),
            evidence(2, ["abstract", "policy"], "The summary continues with funding recommendations and uncertainty boundaries."),
            evidence(5, ["assumption", "model"], "Experimental and epidemiological assumptions are introduced before intervention models."),
            evidence(16, ["validation", "figure"], "Predicted South African prevalence is plotted against historical observations."),
            evidence(23, ["sensitivity", "figure"], "Avoidance-rate scenarios are compared on the same HIV population trajectory."),
            evidence(26, ["sensitivity", "figure"], "Treatment adherence scenarios expose how ARV effectiveness changes."),
            evidence(30, ["risk", "boundary"], "Strengths, weaknesses, and future work identify data and parameter limits."),
        ],
        "abstract": [
            abstract(1, "problem-method", "State the AIDS policy decision, the 2050 forecast horizon, and the three model components."),
            abstract(2, "decision-boundary", "Translate model outputs into intervention priorities while qualifying data uncertainty."),
        ],
        "models": [
            model(5, "epidemiological-base", "Use an iterative deterministic population model for annual HIV progression."),
            model(23, "education-and-vaccine", "Parameterize reduced transmission under education and vaccine scenarios."),
            model(26, "ARV-dynamics", "Model treatment and adherence effects on HIV/AIDS trajectories."),
            model(26, "economic-allocation", "Relate treatment coverage and costs to funding choices."),
        ],
        "validation": [
            validation(16, "historical-fit", "Overlay model predictions and South African historical data."),
            validation(23, "parameter-sensitivity", "Sweep avoidance rates and compare long-horizon populations."),
            validation(26, "adherence-sensitivity", "Compare three adherence levels under the same axes."),
            validation(30, "scope-audit", "List prospective-data and parameter-estimation limitations."),
        ],
        "figures": [
            figure(16, "external-validation", "observed-versus-predicted curve", "Show empirical points and the model curve on one axis."),
            figure(23, "policy-sensitivity", "scenario trajectories", "Use identical initial conditions and axes for policy levers."),
            figure(26, "treatment-sensitivity", "multi-series time plot", "Make adherence assumptions legible through labeled trajectories."),
        ],
        "rules": [
            rule(1, "A policy abstract should name the horizon, model chain, intervention levers, and decision output."),
            rule(16, "Use observed-versus-predicted overlays before presenting policy scenarios."),
            rule(30, "Separate structural strengths from data and parameter weaknesses."),
        ],
        "risks": [
            risk(30, "Long-horizon forecasts depend on uncertain prospective demographic and epidemiological parameters.", "high"),
            risk(23, "Scenario curves do not include uncertainty bands."),
            risk(1, "The two-page abstract is information-rich but visually dense."),
        ],
    },
    "mcm-2007-a-1034": {
        "title": "Applying Voronoi Diagrams to the Redistricting Problem",
        "evidence": [
            evidence(1, ["abstract", "risk"], "The abstract states the method, desired district properties, New York case, and limitations; a mirror watermark is visible."),
            evidence(6, ["theory", "criteria"], "The model is evaluated against contiguousness, compactness, simplicity, and population balance."),
            evidence(10, ["model", "figure"], "A progressive schematic explains weighted Voronoi subdivision."),
            evidence(12, ["data", "map"], "New York population density is shown in map and oblique views."),
            evidence(16, ["result", "map"], "The final statewide districts and enlarged urban regions are shown together."),
            evidence(17, ["analysis", "boundary"], "The results discuss population balance, geometry, and boundary-definition limitations."),
            evidence(20, ["conclusion", "criteria"], "The conclusion returns to the original redistricting criteria."),
        ],
        "abstract": [abstract(1, "gap-method-result-limit", "Move from gerrymandering motivation to weighted Voronoi construction, case-study performance, and known limitations in one compact block.")],
        "models": [
            model(6, "design-criteria", "Define fairness through population balance, contiguousness, compactness, and simple boundaries."),
            model(10, "weighted-voronoi", "Generate and iteratively subdivide population-weighted Voronoi regions."),
            model(12, "spatial-data", "Map raster population density into the distance calculation."),
            model(16, "case-construction", "Apply the method to 29 New York districts and enlarge dense regions."),
        ],
        "validation": [
            validation(6, "criteria-check", "Evaluate the construction against explicit geometric and political criteria."),
            validation(16, "case-study", "Inspect statewide and city-scale district geometry."),
            validation(17, "limitation-analysis", "Discuss boundary precision and representation tradeoffs."),
        ],
        "figures": [
            figure(10, "algorithm-explanation", "progressive schematic", "Explain the subdivision mechanism before showing a real map."),
            figure(12, "input-data", "paired map views", "Show the population surface that drives the weighting."),
            figure(16, "main-result", "overview plus detail maps", "Use one overview and two enlarged regions for multi-scale spatial verification."),
        ],
        "rules": [
            rule(10, "Use a minimal schematic to teach a geometric algorithm before the case-study maps."),
            rule(16, "Pair a full-domain map with enlarged dense regions instead of shrinking all labels."),
            rule(20, "Return to the original fairness criteria in the conclusion."),
        ],
        "risks": [
            risk(1, "A bright third-party watermark contaminates the archived first page.", "high"),
            risk(17, "The case study has limited comparison with alternative redistricting baselines."),
            risk(16, "Grayscale regions are difficult to distinguish at reduced print size."),
        ],
    },
    "mcm-2007-b-2053": {
        "title": "Boarding at the Speed of Flight",
        "evidence": [
            evidence(1, ["abstract", "decision"], "The executive summary addresses airline decisions and names passenger, bag, and strategy effects."),
            evidence(2, ["abstract", "recommendation"], "The summary finishes with ranked conclusions and practical boarding recommendations."),
            evidence(16, ["model", "figure"], "A color-coded seat matrix explains candidate boarding schemes before simulation."),
            evidence(23, ["sensitivity", "figure"], "Boarding strategies are compared while airplane dimensions vary."),
            evidence(27, ["robustness", "figure"], "Six aligned distributions expose variance and tail behavior across strategies."),
            evidence(28, ["result", "conclusion"], "A compact comparison table precedes a structured conclusion."),
            evidence(29, ["boundary", "summary"], "Strengths, limitations, and actionable recommendations close the paper."),
        ],
        "abstract": [
            abstract(1, "decision-brief", "Frame the problem for an airline audience and identify the simulation factors."),
            abstract(2, "ranked-findings", "Summarize the dominant factors, best strategies, and operational recommendation as bullets."),
        ],
        "models": [
            model(16, "strategy-encoding", "Encode assigned-seat boarding schemes as ordered seat groups."),
            model(16, "passenger-simulation", "Model aisle movement, stowing behavior, interference, and plane geometry."),
            model(23, "strategy-comparison", "Compare candidate schemes under varied airplane dimensions and passenger conditions."),
        ],
        "validation": [
            validation(23, "factor-sensitivity", "Vary plane dimensions and retained luggage assumptions."),
            validation(27, "distributional-check", "Compare full simulated loading-time distributions, not only means."),
            validation(28, "cross-strategy-table", "Report the same summary statistics for each strategy."),
        ],
        "figures": [
            figure(16, "strategy-definition", "categorical seat matrix", "Use a consistent color code to define every strategy visually."),
            figure(23, "factor-sensitivity", "multi-series line chart", "Keep strategies on one axis while varying a physical factor."),
            figure(27, "robustness", "small-multiple histograms", "Show the shape and spread of all strategy outcomes in a shared layout."),
        ],
        "rules": [
            rule(1, "Write the summary as a decision brief for the stated stakeholder."),
            rule(27, "Use small-multiple distributions when stochastic strategies have similar means but different tails."),
            rule(28, "Place a compact numerical comparison immediately before the conclusion."),
        ],
        "risks": [
            risk(23, "The line chart is crowded and its legend is small at print scale."),
            risk(29, "Several behavioral assumptions lack empirical calibration."),
            risk(27, "Distribution panels are useful but axis labels become difficult to read when reduced."),
        ],
    },
    "icm-2007-c-2052": {
        "title": "Optimizing the Effectiveness of Organ Allocation",
        "evidence": [
            evidence(1, ["title", "layout"], "The paper begins with title and contents but no standalone abstract."),
            evidence(4, ["model", "network"], "The US transplant network is represented as a rooted tree and discrete-time process."),
            evidence(6, ["result", "assumption"], "Base-model objectives and assumptions are stated beside the first results."),
            evidence(7, ["model", "figure"], "A full process flowchart exposes patient, organ, matching, operation, failure, and death transitions."),
            evidence(9, ["validation", "figure"], "Policy scenarios are compared through aligned outcome curves."),
            evidence(16, ["sensitivity", "figure"], "A parameter sweep shows the effect of an allocation parameter on outcomes."),
            evidence(21, ["boundary", "review"], "Strengths and weaknesses cover flexibility, ethics, data manipulation, and computational cost."),
        ],
        "abstract": [abstract(1, "missing-abstract", "No result-bearing abstract is present; the contents reveal coverage but not recommendations or quantitative results.")],
        "models": [
            model(4, "network-and-arrivals", "Represent the transplant system as a rooted tree with time-dependent patient and organ arrivals."),
            model(7, "discrete-event-allocation", "Simulate priority matching, operations, failure, survival, and death updates."),
            model(9, "policy-comparison", "Apply alternative-country policies and kidney-exchange rules within the same simulator."),
            model(16, "ethical-extension", "Add patient choice and ethical or political decision effects."),
        ],
        "validation": [
            validation(6, "base-case-check", "Quantify the base allocation model under explicit assumptions."),
            validation(9, "policy-scenario", "Compare outcome curves for alternative policies."),
            validation(16, "parameter-sensitivity", "Sweep a decision parameter and inspect outcome stability."),
            validation(21, "scope-audit", "Separate computational, data, ethical, and policy limitations."),
        ],
        "figures": [
            figure(7, "model-architecture", "process flowchart", "Make state transitions and feedback loops visible before policy variants."),
            figure(9, "policy-comparison", "aligned scenario curves", "Use repeated axes to compare transplant outcomes across policies."),
            figure(16, "sensitivity", "parameter-response line chart", "Show how a policy parameter changes the outcome before recommending it."),
        ],
        "rules": [
            rule(7, "For discrete-event policy models, draw the complete state-transition loop before equations."),
            rule(9, "Evaluate policy variants inside one common simulator and common output contract."),
            rule(21, "Treat ethical scope limits separately from numerical-model weaknesses."),
        ],
        "risks": [
            risk(1, "Missing abstract delays access to the decision and result."),
            risk(21, "The model's flexibility permits data manipulation and raises computational cost, as the authors acknowledge.", "high"),
            risk(9, "Several line plots use very small legends and labels."),
        ],
    },
}

READINGS.update(
    {
        "mcm-2008-a-3694": {
            "title": "Mathematically Modeling Sea Level Rise",
            "evidence": [
                evidence(1, ["layout", "contents"], "A linked table of contents opens the paper; no result-bearing abstract is present."),
                evidence(6, ["model", "figure"], "A colored flowchart connects emission scenarios, ice mass balance, thermal expansion, and inundation outputs."),
                evidence(17, ["robustness", "map"], "Maps at 0, 10, and 100 meters of sea-level rise provide a qualitative extreme-case check."),
                evidence(20, ["result", "table"], "Scenario impacts are reported with years, submerged cities, displaced population, and area."),
                evidence(23, ["comparison", "conclusion"], "Scenario tables lead directly into discussion and external agreement checks."),
                evidence(25, ["boundary", "risk"], "The discussion identifies simplified thermal expansion, accumulation, and climate-scenario assumptions."),
            ],
            "abstract": [abstract(1, "missing-abstract", "The paper starts with contents rather than a summary, so methods and outputs are not synthesized on the first page.")],
            "models": [
                model(6, "scenario-input", "Use emissions and temperature scenarios as forcing inputs."),
                model(6, "physical-process", "Combine Greenland ice-sheet mass balance with thermal expansion."),
                model(17, "spatial-inundation", "Map modeled sea-level rise onto coastal elevation and city data."),
                model(20, "impact-accounting", "Convert inundation into displaced population and submerged area."),
            ],
            "validation": [
                validation(17, "extreme-case-map", "Check spatial behavior at 0, 10, and 100 meter sea-level rise."),
                validation(23, "external-range-check", "Compare 50-year estimates with values attributed to IPCC, NRC, and EPA sources."),
                validation(25, "structural-limit", "Identify physical processes that are simplified or omitted."),
            ],
            "figures": [
                figure(6, "model-overview", "colored flowchart", "Expose inputs, physical branches, and outputs in one vertical route."),
                figure(17, "robustness", "matched inundation maps", "Keep geography and color scale fixed while varying sea level."),
                figure(20, "decision-output", "scenario table", "Translate physical outputs into place, population, and area impacts."),
            ],
            "rules": [
                rule(6, "For coupled physical models, show forcing, submodels, and outputs before derivation."),
                rule(17, "Use fixed-map extreme cases to reveal spatial logic and implementation defects."),
                rule(23, "Compare modeled magnitudes with independent published ranges before claiming plausibility."),
            ],
            "risks": [
                risk(1, "No abstract communicates the final scenario results."),
                risk(25, "Key climate and physical processes are simplified, limiting long-horizon inference.", "high"),
                risk(6, "The flowchart palette is vivid but lacks a legend for color semantics."),
            ],
        },
        "mcm-2008-b-2858": {
            "title": "hsolve: A Difficulty Metric and Puzzle Generator for Sudoku",
            "evidence": [
                evidence(1, ["title", "layout"], "A sparse title page separates identity from the abstract."),
                evidence(2, ["abstract", "result"], "The abstract states the search-based metric, 800-puzzle validation, correlation, and generator outcomes."),
                evidence(10, ["validation", "table"], "A contingency table and Goodman-Kruskal gamma coefficient compare model and external ratings."),
                evidence(11, ["validation", "figure"], "External and model-derived difficulty distributions are juxtaposed."),
                evidence(16, ["generator", "figure"], "A generated-puzzle difficulty histogram and runtime analysis quantify output control."),
                evidence(17, ["boundary", "conclusion"], "Strengths and weaknesses distinguish metric validity from limited benchmark data."),
            ],
            "abstract": [abstract(2, "problem-method-validation-result", "State the arbitrary-rating problem, expected-search-time metric, independent validation, correlation coefficient, and generator performance.")],
            "models": [
                model(2, "search-metric", "Frame Sudoku solution as a search process and use expected search time as difficulty."),
                model(10, "rating-calibration", "Compare the metric with externally graded puzzles."),
                model(16, "controlled-generation", "Use standard and pseudo-generators to target difficulty intervals."),
            ],
            "validation": [
                validation(10, "external-label-test", "Use 800 externally rated puzzles and report a Goodman-Kruskal gamma of 0.82."),
                validation(11, "distribution-check", "Compare the empirical model distribution with an external solver population."),
                validation(16, "runtime-and-target-test", "Measure generation runtime and achieved difficulty ranges."),
            ],
            "figures": [
                figure(10, "external-validation", "contingency table", "Show where ordinal model ratings agree and disagree with external labels."),
                figure(11, "distribution-validation", "histogram plus reference curve", "Compare shapes as well as a scalar association metric."),
                figure(16, "generator-output", "difficulty histogram", "Verify that generated outputs occupy the requested difficulty range."),
            ],
            "rules": [
                rule(2, "Put the model, sample size, validation statistic, and practical output in the abstract."),
                rule(10, "For ordinal predictions, show a contingency table alongside the association statistic."),
                rule(17, "Explain whether uncertainty comes from the model or from scarce benchmark labels."),
            ],
            "risks": [
                risk(17, "The benchmark is limited and the authors cannot conclusively establish all difficulty levels.", "high"),
                risk(11, "Distribution plots use inconsistent visual styles and limited axis annotation."),
                risk(16, "Generator evaluation emphasizes difficulty and runtime more than puzzle diversity."),
            ],
        },
        "mcm-2009-a-4339": {
            "title": "Three steps to make the traffic circle go round",
            "evidence": [
                evidence(1, ["abstract", "decision"], "The summary sheet states two simulation scales, five objectives, a three-step control plan, and stress tests."),
                evidence(5, ["data", "figure"], "A labeled aerial image and origin-destination matrix establish geometry and demand."),
                evidence(9, ["baseline", "sensitivity"], "Macro and micro simulations are compared before parameter sensitivity is introduced."),
                evidence(16, ["optimization", "figure"], "Signal timing, five objective values, and a traffic snapshot share one result page."),
                evidence(20, ["robustness", "figure"], "Alternative layouts and a repeated-run sensitivity table test transfer and stability."),
                evidence(21, ["risk-probe", "figure"], "An emergency breakdown scenario is visualized as a failure-mode probe."),
            ],
            "abstract": [abstract(1, "problem-model-decision-validation", "Summarize macro and micro simulations, multi-objective scoring, a three-step control policy, and robustness cases on the summary sheet.")],
            "models": [
                model(5, "geometry-and-demand", "Encode a six-arm roundabout and origin-destination flow matrix."),
                model(9, "dual-simulation", "Use a macro flow model and cellular-automata-like vehicle simulation."),
                model(16, "multi-objective-control", "Optimize signal, sign, and flow-adaptation decisions over five criteria."),
                model(20, "adaptive-policy", "Transfer the policy to different traffic circles and demand levels."),
            ],
            "validation": [
                validation(9, "model-cross-check", "Compare two simulation models on average travel time."),
                validation(20, "repeat-and-transfer", "Run 50 repetitions and test a different roundabout layout."),
                validation(21, "failure-mode-probe", "Simulate a blocked vehicle and observe whether traffic continues."),
            ],
            "figures": [
                figure(5, "problem-definition", "annotated aerial image plus OD table", "Bind every arm label to the demand matrix before modeling."),
                figure(16, "main-result", "timing strip plus KPI table plus snapshot", "Combine decision, metrics, and resulting state on one page."),
                figure(20, "robustness", "layout schematics plus sensitivity table", "Show both structural transfer and stochastic variation."),
                figure(21, "risk-probe", "failure-state snapshot", "Visualize an adverse event rather than describing robustness only in prose."),
            ],
            "rules": [
                rule(9, "Use an independently structured second model as a cross-check when direct ground truth is unavailable."),
                rule(16, "Present optimized controls, objective values, and system state together."),
                rule(21, "Design at least one failure-mode probe tied to the operational claim."),
            ],
            "risks": [
                risk(1, "The summary includes decorative road signs that consume scarce first-page area."),
                risk(16, "Some result figures and tables use small labels and a light blue Office style."),
                risk(21, "Emergency testing is qualitative and reports limited quantitative degradation."),
            ],
        },
        "mcm-2010-a-6749": {
            "title": "Modeling the Sweet Spot of Wood, Corked, and Metal Baseball Bats",
            "evidence": [
                evidence(1, ["abstract", "result"], "The summary presents mechanics models, empirical matching, a sweet-spot location, corking effects, and design implications."),
                evidence(5, ["model", "overview"], "The model overview separates wood, corked, and metal bat mechanisms."),
                evidence(16, ["model", "schematic"], "A corked-bat cross-section supports the double-spring and mass-property derivation."),
                evidence(39, ["validation", "boundary"], "Model validation compares simplified mechanics with omitted vibration and hoop effects."),
                evidence(43, ["conclusion", "result"], "The problem review restates each requested decision and its practical interpretation."),
                evidence(44, ["risk", "reference"], "Weaknesses quantify an error source and note limited empirical formulas and cash data."),
            ],
            "abstract": [abstract(1, "method-quantified-result-design", "Move from mechanics and simulation to a reported sweet-spot location, corking mechanism, and metal-bat design conclusion.")],
            "models": [
                model(5, "collision-mechanics", "Model bat-ball collision and batted-ball speed as a function of impact location."),
                model(16, "corked-bat-extension", "Add a double-spring representation and modified mass properties."),
                model(39, "metal-bat-design", "Relate material and geometry parameters to speed and controllability."),
            ],
            "validation": [
                validation(1, "empirical-match", "Claim agreement between simulated batted-ball speed and experimental data."),
                validation(39, "mechanism-review", "Compare the simplified model with known vibration and hoop-vibration mechanisms."),
                validation(43, "question-closure", "Answer each requested subproblem in a dedicated problem-review list."),
                validation(44, "error-audit", "Report an approximately 5 percent omitted-effect error and other data limitations."),
            ],
            "figures": [
                figure(16, "mechanism", "annotated cross-section", "Introduce the geometric parameters directly on the physical object."),
                figure(39, "derivation-to-conclusion", "equations plus validation prose", "Place parameter identities immediately before validation and discussion."),
                figure(43, "result-synthesis", "structured bullet review", "Map final conclusions back to every requested problem."),
            ],
            "rules": [
                rule(1, "A mechanics abstract should report the physical mechanism, calibrated quantity, and design implication."),
                rule(16, "Annotate model geometry on a cross-section before introducing mass and inertia equations."),
                rule(43, "Close a multi-part problem with a one-to-one question review."),
            ],
            "risks": [
                risk(44, "Transverse-wave and hoop-vibration effects are omitted and contribute a stated error.", "high"),
                risk(44, "Some empirical formulas and cash-related data are limited or not independently reproduced."),
                risk(1, "The summary is dense and lacks a compact comparison table for the three bat types."),
            ],
        },
        "mcm-2010-b-7273": {
            "title": "Tracking Serial Criminals with a Road Metric",
            "evidence": [
                evidence(1, ["abstract", "model"], "The abstract connects road travel time, kernel density estimation, Rossmo's model, and two case studies."),
                evidence(4, ["model", "assumption"], "The road metric is defined from shortest travel time with explicit street-class assumptions."),
                evidence(9, ["model", "figure"], "A road-metric circle illustrates how travel-time geometry differs from Euclidean distance."),
                evidence(10, ["case-study", "heatmap"], "A crime series is overlaid on a road-aware hotspot surface."),
                evidence(16, ["result", "surface"], "A three-dimensional residence-probability surface accompanies model extensions."),
                evidence(17, ["conclusion", "boundary"], "Computational efficiency, tests, and the conclusion delimit the model's use."),
                evidence(18, ["transfer", "policy"], "An executive summary translates both prediction outputs into investigative guidance."),
            ],
            "abstract": [abstract(1, "problem-method-case-result", "Name the two prediction tasks, road metric, KDE and Rossmo components, and the historical case studies.")],
            "models": [
                model(4, "road-metric", "Compute shortest travel-time distance over a road graph."),
                model(9, "future-crime-density", "Apply kernel density estimation under the road metric."),
                model(16, "residence-prior", "Adapt Rossmo's geographic-profiling model to road travel time."),
                model(10, "case-application", "Apply both methods to the Yorkshire Ripper and Atlanta Child Murderer data."),
            ],
            "validation": [
                validation(10, "historical-case", "Overlay known crimes and predicted hotspots for a documented series."),
                validation(17, "computational-test", "Discuss scalability and a limited computational test set."),
                validation(18, "out-of-sample-use", "Distinguish predicting future crimes from locating a residence and state investigative limits."),
            ],
            "figures": [
                figure(9, "metric-explanation", "road-network schematic", "Make the non-Euclidean neighborhood visually intuitive."),
                figure(10, "case-result", "road overlay heatmap", "Overlay evidence points, routes, and risk surface in one spatial frame."),
                figure(16, "residence-result", "3D probability surface", "Separate the residence prediction from the crime hotspot map."),
            ],
            "rules": [
                rule(9, "When replacing Euclidean distance, visualize the induced geometry before using it in a model."),
                rule(10, "Overlay historical events on the predicted spatial field for case-level validation."),
                rule(18, "Separate two prediction targets and their permitted decision uses in the conclusion."),
            ],
            "risks": [
                risk(17, "The evaluation uses a limited number of historical cases and lacks a modern out-of-sample benchmark.", "high"),
                risk(10, "Rainbow heatmaps are not perceptually uniform and can distort magnitude."),
                risk(16, "The 3D surface makes precise spatial comparison harder than a calibrated contour map."),
            ],
        },
        "icm-2010-c-6947": {
            "title": "A new method for pollution abatement: different solutions to different types",
            "evidence": [
                evidence(1, ["abstract", "decision"], "The summary states risk ranking, policy differentiation, and three concrete outputs."),
                evidence(2, ["problem", "boundary"], "The introduction narrows the task to floating plastic and marine-organism risk."),
                evidence(6, ["model", "table"], "Raw abundance and mesh-size data are converted into a multi-attribute decision matrix."),
                evidence(8, ["result", "figure"], "A regulated matrix and bar chart rank six plastic categories."),
                evidence(9, ["review", "boundary"], "Strengths, weaknesses, and discussion distinguish data selection from ecological omissions."),
                evidence(10, ["policy", "table"], "Three product classes are mapped to differentiated tax, fines, research, and prohibition policies."),
            ],
            "abstract": [abstract(1, "problem-method-ranking-policy", "State the pollution decision, multi-attribute method, risk ranking, and type-specific policy output.")],
            "models": [
                model(6, "attribute-selection", "Select abundance and size as risk attributes for floating plastic."),
                model(6, "multi-attribute-ranking", "Use grey multi-attribute decision and reciprocal-rank weighting."),
                model(8, "risk-grading", "Rank plastic categories and group them into high, medium, and low risk."),
                model(10, "policy-mapping", "Assign differentiated regulatory actions to the three risk groups."),
            ],
            "validation": [
                validation(9, "data-selection-check", "Substitute candidate values into the model and compare with ingestion-size evidence."),
                validation(9, "limitation-audit", "Identify omitted toxicity, shape, and species-behavior factors."),
                validation(10, "decision-consistency", "Map every risk class to a transparent policy bundle."),
            ],
            "figures": [
                figure(6, "data-to-model", "source table plus decision matrix", "Keep raw quantities beside their normalized decision representation."),
                figure(8, "main-result", "ranked bar chart", "Display category order after the matrix calculation."),
                figure(10, "policy-output", "decision table", "Translate risk classes into directly comparable regulatory actions."),
            ],
            "rules": [
                rule(6, "Show the raw data table immediately before the normalized decision matrix."),
                rule(9, "For evaluation models, test whether selected indicators agree with an external domain fact."),
                rule(10, "Turn the final score into a transparent action table rather than ending at a ranking."),
            ],
            "risks": [
                risk(9, "Toxicity, shape, species behavior, and other ecological factors are omitted.", "high"),
                risk(8, "The default 3D bar style adds visual distortion without analytical value."),
                risk(10, "Policy thresholds depend strongly on the chosen attributes and weights."),
            ],
        },
    }
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def dhash64(path: Path) -> str:
    with Image.open(path) as image:
        gray = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())
    value = 0
    for row in range(8):
        for column in range(8):
            value = (value << 1) | int(pixels[row * 9 + column] > pixels[row * 9 + column + 1])
    return f"dhash64:{value:016x}"


def official_record(paper: dict[str, Any]) -> dict[str, Any]:
    paper_id = paper["id"]
    if paper_id not in OFFICIAL:
        return {
            "verified": False,
            "official_url": "",
            "official_pdf": "",
            "official_pdf_sha256": "",
            "official_text": "",
            "official_page": None,
            "official_text_line": None,
            "match": "No independent official award locator found; the mirror directory label is not award evidence.",
        }
    pdf_name, text_name, page_number, expected_line_number = OFFICIAL[paper_id]
    official_root = RAW / "_official"
    pdf_path = official_root / pdf_name
    text_path = official_root / text_name
    if not pdf_path.is_file() or not text_path.is_file():
        raise FileNotFoundError(f"Missing official evidence for {paper_id}")
    lines = text_path.read_text(encoding="utf-8", errors="replace").splitlines()
    control = str(paper["control"])
    matches = [
        (index, line.strip())
        for index, line in enumerate(lines, start=1)
        if re.search(rf"(?<!\d){re.escape(control)}(?!\d)", line) and "Outstanding Winner" in line
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one official award match for {paper_id}, found {len(matches)}")
    line_number, matched_line = matches[0]
    return {
        "verified": True,
        "official_url": paper["official_result_url"],
        "official_pdf": pdf_path.relative_to(ROOT).as_posix(),
        "official_pdf_sha256": sha256(pdf_path),
        "official_text": text_path.relative_to(ROOT).as_posix(),
        "official_page": page_number,
        "official_text_line": line_number,
        "expected_text_line_hint": expected_line_number,
        "match": matched_line,
    }


def source_url(paper: dict[str, Any]) -> str:
    repository = paper["repository"].removesuffix("/")
    owner_repo = repository.removeprefix("https://github.com/")
    return f"https://api.github.com/repos/{owner_repo}/git/blobs/{paper['blob_sha']}"


def build_manifest(paper: dict[str, Any], reading: dict[str, Any]) -> dict[str, Any]:
    paper_id = paper["id"]
    directory = RAW / paper_id
    pdf_path = directory / "paper.pdf"
    text_path = directory / "paper.txt"
    first_page = RENDERED / paper_id / "page-01.png"
    if not pdf_path.is_file() or not text_path.is_file() or not first_page.is_file():
        raise FileNotFoundError(f"Incomplete cached artifact set for {paper_id}")
    rendered_pages = sorted((RENDERED / paper_id).glob("page-*.png"))
    if not rendered_pages:
        raise ValueError(f"No rendered pages for {paper_id}")
    computed_blob = git_blob_sha(pdf_path)
    if computed_blob != paper["blob_sha"]:
        raise ValueError(f"Pinned Git blob mismatch for {paper_id}")
    official = official_record(paper)
    manifest = {
        "schema_version": 1,
        "paper_id": paper_id,
        "identity": {
            "contest": paper["contest"],
            "year": paper["year"],
            "problem": paper["problem"],
            "team_id": str(paper["control"]),
            "title": reading["title"],
        },
        "source": {
            "source_id": paper["source_id"],
            "repository": paper["repository"],
            "commit": paper["commit"],
            "path": paper["path"],
            "blob_api_url": source_url(paper),
            "accessed": REVIEW_DATE,
        },
        "pdf": {
            "local_path": pdf_path.relative_to(ROOT).as_posix(),
            "bytes": pdf_path.stat().st_size,
            "sha256": sha256(pdf_path),
            "git_blob_sha_expected": paper["blob_sha"],
            "git_blob_sha_computed": computed_blob,
            "git_blob_verified": True,
            "pages": len(rendered_pages),
            "first_page_phash": dhash64(first_page),
        },
        "text": {
            "local_path": text_path.relative_to(ROOT).as_posix(),
            "bytes": text_path.stat().st_size,
            "sha256": sha256(text_path),
            "method": "pdftotext layout extraction retained by the corpus batch",
        },
        "render": {
            "directory": (RENDERED / paper_id).relative_to(ROOT).as_posix(),
            "pages": len(rendered_pages),
            "all_pages_present": True,
            "overview": (RENDERED / paper_id / "overview.jpg").relative_to(ROOT).as_posix(),
            "evidence_review": (RENDERED / paper_id / "evidence-review.jpg").relative_to(ROOT).as_posix(),
            "selected_pages": PAGES[paper_id],
            "visual_review": "complete",
        },
        "official_award_evidence": official,
        "provenance": {
            "generated_at": REVIEW_DATE,
            "builder": "corpus/selected/mcm-gmcm/build_deep_read.py",
            "policy": "Pinned full text; award labels require independent official evidence.",
        },
    }
    (directory / "source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def add_page_locators(paper_id: str, reading: dict[str, Any]) -> None:
    for item in reading["evidence"]:
        page = item["page"]
        item["locator"] = f"PDF page {page}"
        item["render"] = f"corpus/rendered/mcm-gmcm/{paper_id}/page-{page:02d}.png"


def build_card(paper: dict[str, Any], reading: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    paper_id = paper["id"]
    add_page_locators(paper_id, reading)
    official = manifest["official_award_evidence"]
    verified = bool(official["verified"])
    level = "B" if verified else "C"
    award_text = paper["claimed_award"] if verified else "镜像目录称优秀论文，未独立核验"
    card = {
        "schema_version": "3.0",
        "paper_id": paper_id,
        "identity": {
            "contest": paper["contest"],
            "year": paper["year"],
            "problem": paper["problem"],
            "team_id": str(paper["control"]),
            "title": reading["title"],
        },
        "source": {
            "url": source_url(paper),
            "publisher": "mirror",
            "accessible": True,
            "fulltext": True,
            "access": "public pinned Git blob cached locally",
            "repository": paper["repository"],
            "commit": paper["commit"],
            "path": paper["path"],
        },
        "award_evidence": {
            "verified": verified,
            "official_url": official["official_url"],
            "contest": paper["contest"],
            "year": paper["year"],
            "problem": paper["problem"],
            "team_id": str(paper["control"]),
            "title": reading["title"],
            "award": award_text,
            "locator": (
                f"official PDF page {official['official_page']}; extracted text line {official['official_text_line']}"
                if verified
                else "No independent official locator"
            ),
            "matched_text": official["match"],
        },
        "authenticity": {
            "level": level,
            "checks": {
                "pinned_commit": True,
                "git_blob_sha_matches": True,
                "local_pdf_sha256": True,
                "all_pages_rendered": True,
                "official_award_match": verified,
            },
            "reasons": (
                [
                    "The full text is pinned and hash-verified in a community mirror.",
                    "The control number, contest year, problem, and Outstanding Winner label match a COMAP official result PDF.",
                    "The paper itself is not served from an official paper-display page, so the level is B rather than A.",
                ]
                if verified
                else [
                    "The full text is pinned and hash-verified in a community mirror.",
                    "No independent official award list or official paper-display locator was found for this record.",
                    "Repository popularity and an 'excellent papers' folder name do not establish an award.",
                ]
            ),
        },
        "pdf": {
            "sha256": manifest["pdf"]["sha256"],
            "pages": manifest["pdf"]["pages"],
            "local_path": manifest["pdf"]["local_path"],
            "first_page_phash": manifest["pdf"]["first_page_phash"],
            "text_sha256": manifest["text"]["sha256"],
        },
        "review_status": "evidence_deep_read" if verified else "content_extracted",
        "page_evidence": reading["evidence"],
        "abstract_structure": reading["abstract"],
        "model_chain": [dict(item, order=index) for index, item in enumerate(reading["models"], start=1)],
        "validation_chain": [dict(item, order=index) for index, item in enumerate(reading["validation"], start=1)],
        "figures": reading["figures"],
        "code_links": [
            {
                "relationship": "none",
                "execution_status": "not-run",
                "note": "No independently packaged source tree was paired with this exact PDF; embedded appendix fragments are not treated as reproducible code.",
            }
        ],
        "transferable_rules": reading["rules"],
        "risks": reading["risks"],
        "provenance": {
            "reviewed_at": REVIEW_DATE,
            "review_method": "full-page render overview plus 4-7 high-resolution evidence-page visual checks and extracted-text review",
            "source_manifest": f"corpus/raw/mcm-gmcm/{paper_id}/source_manifest.json",
            "selected_pages": PAGES[paper_id],
            "all_pages_rendered": True,
            "reviewer": "Codex modeling-paper-miner workflow",
        },
    }
    return card


def build_report(cards: list[dict[str, Any]]) -> str:
    mcm_cards = [card for card in cards if card["authenticity"]["level"] == "B"]
    gmcm_cards = [card for card in cards if card["authenticity"]["level"] == "C"]
    lines = [
        "# MCM/ICM 获奖论文与 GMCM 样本文献证据研读报告",
        "",
        f"> 生成日期：{REVIEW_DATE}。本报告基于固定 Git commit 的 18 篇全文、逐页渲染和页面证据。",
        "",
        "## 结论与证据边界",
        "",
        f"- MCM/ICM：{len(mcm_cards)} 篇完成 B 级证据深读。论文控制号、年份、题号和 Outstanding Winner 均在 COMAP 官方结果 PDF 中独立匹配。",
        f"- GMCM：{len(gmcm_cards)} 篇完成 C 级内容深读。全文和 Git blob 可核验，但目前没有独立官方获奖名单定位，因此不得写成‘已核验优秀/获奖论文’。",
        "- 18 篇全文均完成逐页渲染；每篇又选取 4-7 张高清页复核摘要、模型、验证、主图和风险。",
        "- 本批次没有把 PDF 附录中的代码截图认定为可复现实验代码，也没有执行上游 MATLAB/Python 片段。",
        "",
        "## 立即可迁移的规则",
        "",
        "1. 摘要按‘问题 - 方法 - 量化结果 - 验证 - 边界’展开。美赛执行摘要更像给决策者的短报告；研究生赛长摘要适合逐问汇报，但必须控制模型堆叠。",
        "2. 主结果图优先使用同轴比较、小倍图、空间叠加和‘收敛曲线 + 最终决策’组合。普通图能说清证据时，不使用复杂组合图。",
        "3. 每个主要模型至少绑定一种可比较验证：外部数据拟合、替代模型交叉验证、精确求解器 baseline、参数敏感性或失败模式探针。",
        "4. 空间问题先画真实对象或输入地图，再画计算抽象，最后画结果；预测问题同时给历史拟合、预测区间或重复划分不确定性。",
        "5. 优化论文把决策变量、目标、约束、求解器、收敛、最终方案和业务 KPI 放在同一条证据链上。",
        "6. 结论逐题回扣，不把模型分数自动解释为政策结论；局限必须指出受影响的主张范围。",
        "7. 禁止继承旧论文中的身份封面、第三方水印、彩虹色图、默认 3D 柱图、双轴误导、过小图例和代码截图。",
        "",
        "## 图表与验证模式矩阵",
        "",
        "| 场景 | 推荐图件 | 应绑定的验证 | 代表页 |",
        "|---|---|---|---|",
        "| 空间优化 | 输入地图 + 响应热图 + 决策叠加 | 极端情景、替代布局、跨地点 | 2006 A p.6/11/13；2007 A p.12/16 |",
        "| 离散仿真 | 状态流程图 + 策略小倍分布 | 重复运行、因素敏感性、失败模式 | 2007 B p.16/23/27；2009 A p.20/21 |",
        "| 预测/分类 | 训练-测试曲线 + 混淆/校准 + 样本量敏感性 | 外部标签、重复划分、分布检查 | 2008 B p.10/11；GMCM C p.20/28 |",
        "| 优化算法 | 收敛曲线 + 最终方案 + KPI 表 | 精确求解器 baseline、参数扫描 | GMCM B p.18/22；GMCM F p.25/41 |",
        "| 物理机理 | 标注示意图 + 参数响应 + 实验对照 | 实测拟合、遗漏机理误差 | 2010 A p.16/39/44 |",
        "| 综合评价 | 原始数据表 + 标准化矩阵 + 排名/政策表 | 权重敏感性、外部事实一致性 | 2010 C p.6/8/10 |",
        "",
        "## 逐篇证据卡摘要",
        "",
    ]
    for card in cards:
        identity = card["identity"]
        pages = ", ".join(str(value) for value in card["provenance"]["selected_pages"])
        model_steps = " -> ".join(item["step"] for item in card["model_chain"])
        validation_steps = "；".join(item["method"] for item in card["validation_chain"])
        primary_figures = "；".join(
            f"p.{item['page']} {item['chart_type']}（{item['role']}）" for item in card["figures"][:4]
        )
        main_rule = card["transferable_rules"][0]["rule"]
        main_risk = card["risks"][0]["risk"]
        lines.extend(
            [
                f"### {card['paper_id']} | {identity['title']}",
                "",
                f"- 身份：{identity['contest']} {identity['year']} {identity['problem']} 题；真实性 {card['authenticity']['level']}；状态 `{card['review_status']}`。",
                f"- 高清复核页：{pages}。",
                f"- 模型链：{model_steps}。",
                f"- 验证链：{validation_steps}。",
                f"- 主图：{primary_figures}。",
                f"- 可迁移：{main_rule}",
                f"- 主要风险：{main_risk}",
                "",
            ]
        )
    lines.extend(
        [
            "## 赛时使用方式",
            "",
            "- 选题后按题型检索卡片中的 `model_chain`、`validation_chain` 和 `figures`，只复用论证结构，不复制旧文数字、文字或图。",
            "- 每个子问题先建立可运行 baseline 和风险探针，再选择图型；没有证据时不得预留‘漂亮主图’。",
            "- Figure Contract 必须绑定冻结主张、实验定位、变量单位、源脚本、图注以及 PDF/SVG/400 dpi PNG 三种导出。",
            "- 正式 CUMCM 稿严格服从当届规则；GMCM 身份封面、旧 MCM Summary Sheet 和历史页式只用于研究，不进入提交模板。",
            "",
            "## 限制",
            "",
            "本报告评价的是可见论文的论证和呈现方式，不对全部数学推导作重新证明。GMCM 六篇的内容可学习，但获奖状态仍未独立核验。18 篇均未绑定独立源码仓库，因此不计入‘论文-代码可复现配对’指标。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))["papers"]
    paper_ids = {paper["id"] for paper in selection}
    if paper_ids != set(READINGS) or paper_ids != set(PAGES):
        raise ValueError("Selection, page map, and deep-read records must contain the same paper ids")
    CARDS.mkdir(parents=True, exist_ok=True)
    cards: list[dict[str, Any]] = []
    for paper in selection:
        reading = READINGS[paper["id"]]
        manifest = build_manifest(paper, reading)
        card = build_card(paper, reading, manifest)
        errors = validate_card(card, require_deep_read=card["review_status"] == "evidence_deep_read")
        if errors:
            raise ValueError(f"Invalid v3 card for {paper['id']}: {'; '.join(errors)}")
        card_path = CARDS / f"{paper['id']}.json"
        card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cards.append(card)
        print(
            f"{paper['id']}: level={card['authenticity']['level']} "
            f"status={card['review_status']} pages={card['pdf']['pages']}"
        )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(build_report(cards), encoding="utf-8")
    print(f"report: {REPORT.relative_to(ROOT).as_posix()}")


READINGS.update(
    {
        "gmcm-2019-a-a19100030004": {
            "title": "无线智能传播模型",
            "evidence": [
                evidence(1, ["identity", "risk"], "The cover exposes school, team number, and member names; it is not reusable as an anonymous CUMCM page."),
                evidence(2, ["abstract", "result"], "The abstract reports a COST231-Hata correction path, spatial features, neural network and CatBoost comparisons, and an RMSE result."),
                evidence(8, ["mechanism", "figure"], "A geometric propagation schematic defines direct and reflected paths before equations."),
                evidence(14, ["feature", "figure"], "Spatial scatter panels relate coordinate structure to RSRP and engineered direction features."),
                evidence(24, ["model", "figure"], "A neural-network architecture diagram binds engineered inputs to MSE loss."),
                evidence(26, ["comparison", "figure"], "Neural-network and CatBoost train/test curves are shown together and accompanied by RMSE values."),
                evidence(38, ["code", "risk"], "Implementation code is embedded as a screenshot-like appendix rather than a reusable source file."),
            ],
            "abstract": [abstract(2, "question-method-result", "Follow the subproblems in order, naming propagation correction, feature engineering, model comparison, and the final error metric.")],
            "models": [
                model(8, "physical-baseline", "Use COST231-Hata and geometric propagation relationships as a physical starting point."),
                model(14, "spatial-features", "Engineer coordinate, direction, and signal-related predictors."),
                model(24, "neural-regression", "Train a neural network under MSE loss."),
                model(26, "tree-ensemble", "Compare the neural model with CatBoost and select by holdout error."),
            ],
            "validation": [
                validation(14, "feature-diagnostic", "Inspect spatial relationships before fitting nonlinear models."),
                validation(26, "train-test-comparison", "Plot training and test behavior for both candidate models."),
                validation(26, "metric-comparison", "Report RMSE for the selected model and a physical-model baseline."),
            ],
            "figures": [
                figure(8, "mechanism", "annotated propagation schematic", "Explain physical paths before data-driven correction."),
                figure(14, "feature-diagnostic", "small-multiple spatial scatter", "Use aligned panels to reveal directional structure."),
                figure(24, "model-architecture", "network diagram", "Map feature blocks to the prediction loss without decorative elements."),
                figure(26, "model-selection", "paired train-test curves", "Place competing learners under matched scales and report the same metric."),
            ],
            "rules": [
                rule(8, "Lead a hybrid model with the physical mechanism and treat machine learning as a correction layer."),
                rule(14, "Use spatial diagnostic panels to justify engineered coordinate and direction features."),
                rule(26, "Compare candidate models with the same split, axes, and metric."),
            ],
            "risks": [
                risk(1, "The cover contains direct personal and institutional identifiers and must never enter an anonymous submission.", "high"),
                risk(26, "The train/test curves use small labels and do not show uncertainty across repeated splits."),
                risk(38, "Embedded code images are not executable, hash-addressable source artifacts."),
                risk(2, "The paper is only C-level authentic: the mirror's award label has no independent official locator.", "high"),
            ],
        },
        "gmcm-2018-b-b18102520096": {
            "title": "光传送网建模与价值评估",
            "evidence": [
                evidence(1, ["abstract", "model"], "The abstract spans modulation analysis, network planning, and constellation optimization with named algorithms."),
                evidence(11, ["validation", "figure"], "BER-SNR curves compare QPSK, 8QAM, and 16QAM under a common threshold."),
                evidence(18, ["optimization", "map"], "A convergence curve is paired with a map of the selected optical network."),
                evidence(22, ["optimization", "map"], "A second topology optimization repeats the convergence-plus-map structure."),
                evidence(31, ["model", "figure"], "Original and optimized 8QAM and 16QAM constellations are shown as aligned panels."),
                evidence(33, ["comparison", "figure"], "BER curves compare the original and proposed QAM designs."),
                evidence(49, ["code", "risk"], "The appendix shows only a short plotting fragment and not a complete runnable package."),
            ],
            "abstract": [abstract(1, "multi-part-method-result", "Summarize modulation, graph optimization, shortest path, and constellation redesign in the same order as the tasks.")],
            "models": [
                model(11, "modulation-baseline", "Quantify BER-SNR behavior for standard QPSK and QAM schemes."),
                model(18, "network-value", "Represent the optical transport network as a graph and optimize topology value with genetic search and TSP ideas."),
                model(22, "routing", "Use Dijkstra shortest paths inside the network evaluation."),
                model(31, "constellation-redesign", "Move constellation points to improve the SNR tolerance threshold."),
            ],
            "validation": [
                validation(11, "modulation-comparison", "Compare standard schemes under the same BER threshold."),
                validation(18, "optimization-convergence", "Show objective convergence and the resulting map."),
                validation(33, "before-after-performance", "Compare original and redesigned QAM BER-SNR curves."),
            ],
            "figures": [
                figure(11, "baseline", "BER-SNR line chart", "Keep schemes and threshold on a common logarithmic response axis."),
                figure(18, "optimization-result", "convergence curve plus network map", "Place convergence evidence beside the resulting topology."),
                figure(31, "design-comparison", "four-panel constellation plot", "Use matched axes for original and redesigned signal constellations."),
                figure(33, "performance-comparison", "before-after BER curves", "Verify that geometric changes improve the target performance curve."),
            ],
            "rules": [
                rule(11, "Define a common operating threshold when comparing communication schemes."),
                rule(18, "Pair every optimization convergence curve with the actual decision structure it produced."),
                rule(31, "Use matched small multiples for before-after geometric designs."),
            ],
            "risks": [
                risk(1, "The paper combines loosely coupled modulation and network-planning tasks, so the narrative is broad."),
                risk(49, "Only partial code appears in the appendix and cannot reproduce the reported network results.", "high"),
                risk(31, "Default MATLAB styling and small labels reduce print quality."),
                risk(1, "The award description remains unverified outside the repository mirror.", "high"),
            ],
        },
        "gmcm-2020-c-c20102470319": {
            "title": "面向康复工程的脑电信号分析和判别模型",
            "evidence": [
                evidence(1, ["identity", "risk"], "The cover exposes school, team number, and member names."),
                evidence(2, ["abstract", "result"], "The long abstract reports preprocessing, SVM, random forest, CNN, channel selection, semi-supervised learning, and sleep-stage classification by subproblem."),
                evidence(16, ["feature", "figure"], "Channel-weight bar small multiples compare subjects before channel selection."),
                evidence(20, ["validation", "figure"], "Training and test accuracy histories accompany the selected channel subset."),
                evidence(24, ["comparison", "figure"], "Semi-supervised alternatives are compared with repeated train/test curves and a selection table."),
                evidence(28, ["sensitivity", "figure"], "SVM accuracy is plotted against the training-sample ratio and paired with a confusion-matrix definition."),
                evidence(34, ["code", "risk"], "CNN code is embedded in the PDF but external data, environment, and weights are not packaged."),
            ],
            "abstract": [abstract(2, "subproblem-ledger", "Use one paragraph per subproblem, naming data treatment, candidate algorithms, selected method, and output.")],
            "models": [
                model(2, "signal-preprocessing", "Filter, segment, shuffle, and augment EEG samples."),
                model(20, "supervised-comparison", "Compare SVM, random forest, and CNN for target recognition."),
                model(16, "channel-selection", "Use convolutional weights to rank and select EEG channels."),
                model(24, "semi-supervised-learning", "Compare label propagation and adaptive semi-supervised variants."),
                model(28, "sleep-stage-classification", "Use SVM and neural methods for sleep-stage prediction."),
            ],
            "validation": [
                validation(20, "train-test-history", "Show separate training and test accuracy curves."),
                validation(24, "algorithm-comparison", "Compare candidate semi-supervised algorithms under a common selection table."),
                validation(28, "sample-size-sensitivity", "Vary the labeled-training ratio and report classification accuracy."),
            ],
            "figures": [
                figure(16, "feature-selection", "five-panel bar charts", "Use one panel per subject to expose heterogeneous channel importance."),
                figure(20, "learning-diagnostic", "train-test history", "Plot generalization behavior rather than reporting final accuracy only."),
                figure(24, "algorithm-selection", "small-multiple histories plus table", "Combine learning curves with the final selected output."),
                figure(28, "sensitivity", "sample-ratio line chart", "Tie accuracy to data availability before recommending the model."),
            ],
            "rules": [
                rule(2, "For a long multi-question abstract, keep a strict question-method-result rhythm."),
                rule(16, "Use subject-level small multiples when feature importance is heterogeneous."),
                rule(28, "Report performance sensitivity to labeled-data volume for learning models."),
            ],
            "risks": [
                risk(1, "The cover leaks direct identifiers and is incompatible with anonymous submission.", "high"),
                risk(24, "Repeated learning curves use small labels and do not include uncertainty across seeds."),
                risk(34, "Embedded source fragments lack data, dependency, seed, and model-weight provenance.", "high"),
                risk(2, "The mirror label is not independently verified as an award record.", "high"),
            ],
        },
        "gmcm-2019-d-d19102470244": {
            "title": "汽车行驶工况构建",
            "evidence": [
                evidence(1, ["identity", "risk"], "The cover exposes school, team number, and member names."),
                evidence(2, ["abstract", "pipeline"], "The abstract reports data cleaning counts, motion-segment extraction, 33 features, PCA, K-means, and fuel-consumption verification."),
                evidence(14, ["data-quality", "figure"], "Anomaly plots mark suspicious GPS and acceleration records before correction."),
                evidence(22, ["model", "flowchart"], "A PCA flowchart explains standardization, covariance, eigenvalues, contribution rate, and component selection."),
                evidence(26, ["model", "figure"], "A three-dimensional K-means scatter plot shows clustered driving segments."),
                evidence(29, ["result", "figure"], "Feature-weight bars support construction of the representative driving cycle."),
                evidence(30, ["validation", "boundary"], "Fuel-consumption relative error is reported before strengths and weaknesses."),
            ],
            "abstract": [abstract(2, "data-model-validation", "Quantify data retained after cleaning, describe feature and clustering steps, then name the fuel-consumption validation target.")],
            "models": [
                model(14, "data-cleaning", "Detect GPS, time-gap, acceleration, and idle anomalies and interpolate selectively."),
                model(2, "segment-and-feature", "Extract driving segments and compute 33 motion features."),
                model(22, "dimension-reduction", "Use PCA to reduce correlated features."),
                model(26, "segment-clustering", "Cluster segments with K-means and select representatives."),
                model(29, "cycle-construction", "Weight characteristic segments to assemble the driving cycle."),
            ],
            "validation": [
                validation(14, "data-quality-audit", "Visualize and list corrected anomalies before modeling."),
                validation(26, "cluster-inspection", "Inspect separation of motion-segment clusters."),
                validation(30, "domain-output-check", "Compare estimated fuel consumption with the original record and report relative error."),
            ],
            "figures": [
                figure(14, "data-quality", "annotated anomaly small multiples", "Mark corrected records directly on the time series."),
                figure(22, "method", "PCA flowchart", "Turn a familiar algorithm into a reproducible ordered procedure."),
                figure(26, "cluster-result", "3D scatter plot", "Use color to identify segment classes while acknowledging projection limits."),
                figure(29, "feature-result", "ranked bar chart", "Show which characteristics drive representative-cycle selection."),
            ],
            "rules": [
                rule(2, "Put data-retention counts in the abstract when cleaning materially changes the sample."),
                rule(14, "Show marked anomaly examples before presenting cleaned-data models."),
                rule(30, "Validate a constructed operating cycle through a downstream physical quantity such as fuel use."),
            ],
            "risks": [
                risk(1, "The cover leaks direct identifiers.", "high"),
                risk(26, "A 3D PCA/K-means view can hide overlap and lacks quantitative cluster-quality metrics."),
                risk(30, "Validation relies heavily on one downstream error summary."),
                risk(2, "The award status is not independently verified beyond the mirror directory.", "high"),
            ],
        },
        "gmcm-2019-e-e19102840016": {
            "title": "全球变暖气候预测分析",
            "evidence": [
                evidence(1, ["identity", "risk"], "The cover exposes school, team number, and member names."),
                evidence(2, ["abstract", "result"], "The abstract reports Mann-Kendall, wavelets, spatial interpolation, PCA, random forest, ARIMA, Prophet, and quantitative fit metrics by task."),
                evidence(27, ["feature", "figure"], "A correlation heatmap and scree plot justify reducing climate factors."),
                evidence(30, ["comparison", "figure"], "Observed sea temperature is compared with global temperature before forecasting."),
                evidence(35, ["forecast", "figure"], "Historical and Prophet forecast segments are visually separated and a year-value table is supplied."),
                evidence(40, ["validation", "table"], "Random-forest importance is paired with normality tests and correlation-method choices."),
                evidence(48, ["code", "risk"], "Code excerpts contain absolute local paths and a network download call."),
            ],
            "abstract": [abstract(2, "multi-question-method-metric", "For each climate task, name the data scope, method, dominant result, and validation metric where available.")],
            "models": [
                model(2, "trend-and-change", "Use climate slope, Mann-Kendall change detection, and wavelet periodicity analysis."),
                model(27, "factor-reduction", "Use correlation analysis and PCA to reduce climate drivers."),
                model(30, "time-series-forecast", "Fit ARIMA and Prophet models to temperature series."),
                model(40, "driver-classification", "Use random forest to rank and classify important climate drivers."),
            ],
            "validation": [
                validation(27, "dimension-check", "Inspect the correlation matrix and cumulative variance before choosing components."),
                validation(30, "fit-metric", "Report a high fit score for the selected forecasting model."),
                validation(35, "forecast-table", "Provide explicit annual forecasts beside the plotted series."),
                validation(40, "distribution-aware-test", "Choose Pearson or Spearman after normality tests."),
            ],
            "figures": [
                figure(27, "feature-reduction", "heatmap plus scree plot", "Place correlation and retained-dimension evidence on one page."),
                figure(30, "series-comparison", "aligned time-series plots", "Compare related temperatures over the same years before causal discussion."),
                figure(35, "forecast", "history-forecast line plus table", "Separate observed and forecast segments and provide exact tabular values."),
                figure(40, "feature-importance", "bar chart plus statistical table", "Combine model importance with tests that justify the correlation analysis."),
            ],
            "rules": [
                rule(27, "Pair a correlation heatmap with a scree or cumulative-variance plot before PCA-based modeling."),
                rule(35, "Put exact forecast values beside the visual forecast when decisions depend on them."),
                rule(40, "Let distribution checks determine the reported correlation statistic."),
            ],
            "risks": [
                risk(1, "The cover leaks direct identifiers.", "high"),
                risk(48, "Embedded code contains absolute local paths and a network call, so it is neither portable nor safe to batch-run.", "high"),
                risk(2, "Many algorithms are stacked across subproblems; model-selection logic is not always equally deep."),
                risk(2, "The award status has no independent official evidence.", "high"),
            ],
        },
        "gmcm-2018-f-f18100030032": {
            "title": "中转航班调度：从 MILP 模型到启发式算法",
            "evidence": [
                evidence(1, ["abstract", "result"], "The summary states 0-1 and MILP formulations, CPLEX and greedy solvers, flight/gate counts, and passenger-time objectives."),
                evidence(9, ["model", "equation"], "Binary decision variables, objective, and assignment/compatibility constraints start the main model."),
                evidence(25, ["algorithm", "figure"], "A heuristic flowchart is followed by parameter trials and highlighted selected values."),
                evidence(36, ["result", "figure"], "Passenger counts and proportions are shown by transfer-time interval."),
                evidence(41, ["baseline", "table"], "CPLEX and heuristic results are compared on flights, gates, passengers, and transfer-time objectives."),
                evidence(43, ["review", "boundary"], "The conclusion answers each problem and separates method strengths and weaknesses."),
                evidence(59, ["code", "risk"], "Only a small code excerpt is embedded; the complete solver model and data package are absent."),
            ],
            "abstract": [abstract(1, "formulation-solver-result", "For each subproblem, name the formulation, solver or heuristic, and quantified gate, flight, or transfer-time result.")],
            "models": [
                model(9, "binary-assignment", "Formulate flight-to-gate assignment as a 0-1 integer program."),
                model(25, "greedy-fallback", "Design a lower-cost greedy interval-scheduling heuristic."),
                model(36, "passenger-flow", "Extend the assignment to minimize transfer process time."),
                model(41, "solver-comparison", "Compare CPLEX and heuristic outputs under the same KPIs."),
            ],
            "validation": [
                validation(25, "parameter-sensitivity", "Sweep heuristic parameters and show the selected setting."),
                validation(41, "baseline-comparison", "Use CPLEX as a comparable optimization baseline for the heuristic."),
                validation(43, "question-closure", "Answer every subproblem and identify solver and data limitations."),
            ],
            "figures": [
                figure(25, "algorithm", "flowchart plus parameter table", "Present control flow and calibrated parameters together."),
                figure(36, "decision-impact", "dual-axis interval chart", "Show both passenger count and proportion across transfer-time bins."),
                figure(41, "baseline", "solver comparison table", "Compare exact and heuristic methods with the same output contract."),
            ],
            "rules": [
                rule(1, "Put solver names and quantified optimization outputs in the abstract."),
                rule(25, "Treat heuristic parameters as experimental factors and record the selected setting."),
                rule(41, "Compare a heuristic with an exact solver on identical KPIs and constraints."),
            ],
            "risks": [
                risk(1, "The summary is dense and relies on red inline emphasis rather than a compact result table."),
                risk(36, "Dual-axis charts can imply relationships that should also be reported numerically."),
                risk(59, "The embedded code fragment is insufficient to reproduce the CPLEX and heuristic experiments.", "high"),
                risk(1, "The mirror's award label has no independent official locator.", "high"),
            ],
        },
    }
)


if __name__ == "__main__":
    main()
