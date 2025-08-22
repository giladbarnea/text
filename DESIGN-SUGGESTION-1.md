### Design Suggestion: Extensible Table of Contents Extraction (DESIGN-SUGGESTION-1)

Goals
- High precision/recall heading detection first; level inference second.
- Handle diverse PDF formats via pluggable strategies.
- Support both pre-run strategy selection and post-run result selection.
- Preserve a small, stable public API: `get_toc(pdf_path) -> list[(level, text, page)]`.

Architecture Overview
- DocumentContext: single parse pass, shared across components.
- FeatureExtractors: compute shared global features (font stats, layout, links, TOC-page likelihood).
- HeadingDetectors: produce candidate headings with rich evidence.
- LevelInferers: assign levels to candidates, independent of detectors.
- StrategySelector: pre-run plan selection; Ensembler for post-run selection.
- ResultScorer: ranks complete TOC results by robust heuristics.
- Orchestrator: wires the above, runs plans in parallel, returns best result.

Key Data Types (sketch)
```python
from dataclasses import dataclass
from typing import Protocol, Optional

@dataclass(frozen=True)
class HeadingCandidate:
    text: str
    page: int
    x: float
    y: float
    size: float
    is_bold: bool
    features: dict  # numbering_prefix, is_toc_row, link_target, etc.

@dataclass
class TOCEntry:
    level: Optional[int]
    text: str
    page: int
    confidence: float
    provenance: dict  # detector/leveler names, key decisions

@dataclass
class TOCResult:
    entries: list[TOCEntry]
    score: float
    diagnostics: dict

class HeadingDetector(Protocol):
    name: str
    def detect(self, ctx: "DocumentContext") -> list[HeadingCandidate]: ...

class LevelInferer(Protocol):
    name: str
    def infer(self, candidates: list[HeadingCandidate], ctx: "DocumentContext") -> list[TOCEntry]: ...

class ResultScorer(Protocol):
    def score(self, entries: list[TOCEntry], ctx: "DocumentContext") -> float: ...
```

DocumentContext (shared)
- Built once from the PDF; caches expensive computations.
- Contains: spans with coordinates/size/bold/text; blocks/lines; link annotations; early-page TOC-page cues; header/footer patterns; column layout guess; font stats; line groupings; numeric/table detectors.
- Exposes light helper APIs; no global state.

Detectors (examples)
- EmbeddedTOCDetector: wraps `doc.get_toc()`.
- FontStatsDetector: existing size/bold/uniqueness heuristics.
- TOCPageDetector: detect “Contents” pages; parse leader dots and right-aligned page numbers.
- LinkAnnotationDetector: leverage link destinations on early pages.
- ColumnAwareDetector: adjust for multi-column layout.
- RunningHeaderFilter: filtering component to drop repeating headers/footers.

LevelInferers (examples)
- SizeClusterLeveler: cluster by font-size bands (generalized current logic).
- NumberingLeveler: derive levels from prefixes like `2.`, `2.1.`, `B.2.`.
- IndentationLeveler: use x-indentation deltas.
- TOCRowLeveler: align indentation/dots on TOC pages.
- HybridLeveler: weighted vote with fallbacks.

Strategy Selection
- Pre-run PlanSelector: use cheap global cues to pick plans (detectors + leveler), e.g.:
  - TOC rows with leader dots → TOCPageDetector + TOCRowLeveler + NumberingLeveler.
  - Many early-page link annotations → LinkAnnotationDetector + NumberingLeveler.
  - Default → FontStatsDetector + SizeClusterLeveler (+ IndentationLeveler).
- Post-run Ensembler: run a shortlist of plans in parallel; produce `TOCResult` for each; select via ResultScorer.
- Hybrid (recommended): pre-run narrows to 2–3 plans; post-run chooses best.

ResultScorer (robust, PDF-agnostic heuristics)
- Hard constraints (heavy penalties):
  - Non-monotonic page numbers.
  - Duplicated entries, repeated running headers/footers.
  - Too many entries on a single page; table-like line patterns.
- Soft signals (weighted):
  - Reasonable coverage across pages without density spikes.
  - Share of entries with numbering patterns.
  - Font-size distribution consistent with headings by level.
  - Agreement with link targets where available.
  - Consistent x-indentation per level.

Orchestrator Flow
1. Build `DocumentContext` (single parse).
2. Run feature extractors (font stats, layout, links, TOC cues).
3. Pre-run PlanSelector → shortlist of plans.
4. For each plan (in parallel):
   - Run detectors; merge/dedup candidates.
   - Run leveler(s); produce entries + confidences.
   - Apply sanity filters (tables, running headers).
   - Score via ResultScorer → TOCResult.
5. Pick best `TOCResult` and return `(level, text, page)`.
6. When debugging, expose diagnostics.

Pairing vs Independence
- Default to independence (detectors vs levelers) to maximize reuse and flexibility.
- Allow composite strategies as packaged plans for formats where pairing is natural.
- Orchestrator supports both seamlessly.

Extensibility & DI
- Registry for detectors, levelers, and scorers, with default batteries included.
- Users add custom components via registration/config.
- Components take `DocumentContext`; heavy state lives there; no globals.

Incremental Adoption (no regressions)
- Wrap current analyzer as `FontStatsDetector` + `SizeClusterLeveler`.
- Keep `embedded_strategy` as first plan.
- Introduce `ResultScorer` and Orchestrator without changing public API.
- Add TOCPageDetector as the next plan; then expand corpus and tune weights.

Public API
- Keep `extract_toc.get_toc(pdf_path)` unchanged.
- Optionally provide `extract(pdf_path, debug=True)` returning a `TOCResult` for diagnostics.

First Implementation Slice
- Scaffold `DocumentContext`, registry, and orchestrator skeleton.
- Wrap existing logic into `FontStatsDetector` + `SizeClusterLeveler`.
- Implement conservative `ResultScorer` with hard constraints only.
- Implement `TOCPageDetector` (leader dots + right-aligned numbers).