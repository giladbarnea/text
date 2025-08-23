# User

Read the documentation of the project, including the project context file. Ignore everything related to the lee frumer case. 
I want us to think together about a better, more extensible high level design for the table of contents extraction.
In its current state, it a script that was split into a few files, but it's still in essence, a bunch of logic thrown in together.
The basic assumptions are as follows. PDFs are messy and widely different. Down the line, there are going to be a bunch of different strategies to extract the table of contents. Each strategy hopefully fits a hopefully common PDF format. Logically, it follows that there should be some logic to deduce which strategy would be a best fit for any input PDF, before executing it; alternatively, just running all of them at once in parallel and selecting the one with the best results. In either case, this entails yet another stage that, quote, guesses something. In the first case, it tries to guess the best matching strategy pre-run. In the second case, it tries to guess which set of results is better than the others. I don't know by which metric but it's possible.
Another factor is the two-fold purpose of extracting a table of contents. Not only the headings with their page numbers, but also each headings level. These two efforts entail rather different methodologies. So maybe they shouldn't go in pairs in the first place (e.g. two independent analysis tracks with different sets of strategies).
Some dialectic out loud thinking: An argument for pairing the strategies is that the format of the PDF dictates how you should parse it, therefore, given a specific format, Both the heading location and heading level algorithms are dictated by it. They are not inseparable. The argument against it is that you don't know whether this assumption is true, and you would get more flexibility if you made them independent. But the counter-argument for making them independent is that you would have to somehow reconcile between their results and discuss whether one runs before the other, and the latter one utilizes the first one's results or not - does that require a unified interface, etc. 
So far all these thoughts were like walking down the tree of thoughts, but zooming out, looking at the entirety of it at once, I wonder what's shared between all these steps, objects,, dependency injection, interfaces, maybe something global about the PDF that is rolled around the entire process, shared context, etc?

---

# Assistant

<thoughts>
### Goals
- High precision/recall heading detection first; level inference second.
- Handle diverse PDF formats via pluggable strategies.
- Allow both pre-run strategy selection and post-run result selection.
- Maintain a small, stable public API: `get_toc(pdf_path) -> list[(level, text, page)]`.

### Architecture overview
- DocumentContext: one parse pass, shared across all strategies.
- FeatureExtractors: compute reusable global features (font stats, layout, links, TOC-page likelihood).
- Detectors (heading location): produce candidate headings with rich features.
- LevelInferers (heading level): assign levels to candidates, independent of detector.
- StrategySelector: chooses which detectors/levelers to run (pre-run) and/or which results to keep (post-run).
- ResultScorer: ranks complete TOC results for the post-run path.
- Orchestrator: wires the above, runs in parallel, returns best result.
</thoughts>

<response>
### DocumentContext (shared, cached)
- Parsed once from the PDF (extend current `parsing.py` output).
- Contains:
  - Spans with x/y, size, bold, text; page metadata; link annotations; blocks/lines; optional font family; early-page TOC-page likelihood; header/footer patterns; column layout guess.
  - Feature caches (font stats you already compute, line groupings, number-pattern detectors).
- Exposed via light methods to avoid re-parsing and to encourage reuse.

### Detectors (examples just for illustration)
- EmbeddedTOCDetector: wraps `doc.get_toc()`.
- FontStatsDetector: wraps current size/bold/uniqueness heuristics.
- TOCPageDetector: detects “Contents” pages; extracts left labels + leader dots + right page numbers.
- LinkAnnotationDetector: uses link destinations on early pages to infer headings.
- ColumnAwareDetector: accounts for multi-column layout to suppress false positives.
- RunningHeaderFilter: not a detector, but a filter component to drop repeating headers/footers.

Detectors output candidates; they should do minimal dedup/filtering and attach evidence in `features`.

### LevelInferers (examples just for illustration)
- SizeClusterLeveler: cluster by font-size bands (your current approach generalized).
- NumberingLeveler: derive levels from prefixes like “2.”, “2.1.”, “B.2.”.
- IndentationLeveler: infer levels from x-indentation deltas.
- TOCRowLeveler: use indentation/leader dot alignment on TOC pages.
- HybridLeveler: weighted vote from the above, with fallbacks.

Levelers don’t discard items; they assign levels and may add per-entry confidence.

### Strategy selection: pre-run, post-run, hybrid
- Pre-run PlanSelector: uses cheap global cues to pick a plan (detectors + leveler), e.g.:
  - If “contents/ table of contents” rows with leader dots → run TOCPageDetector + TOCRowLeveler + NumberingLeveler.
  - If many link annotations on early pages → LinkAnnotationDetector + NumberingLeveler.
  - Otherwise → FontStatsDetector + SizeClusterLeveler (+ IndentationLeveler).
- Post-run Ensembler: run a shortlist of plans in parallel; compute `TOCResult` per plan; pick best via ResultScorer.
- Hybrid (recommended): pre-run narrows to 2–3 plans; post-run chooses best.

### ResultScorer (robust, PDF-agnostic heuristics)
- Hard constraints (penalize heavily):
  - Non-monotonic page numbers, duplicated entries, too many entries per page, repeated running headers.
- Soft signals (weighted):
  - Coverage across pages without excessive density spikes.
  - Share of entries with numbering patterns.
  - Font-size distribution consistent with headings.
  - Agreement with link targets.
  - Consistency of x-indentation by level.
  - Low overlap with numeric table-like rows (you already detect these).
Weights configurable; default tuned against a growing corpus of PDFs.

### Orchestrator flow
1. Build `DocumentContext` (parse once).
2. Run FeatureExtractors (font stats, layout, link scan, TOC-page clues).
3. Pre-run PlanSelector → shortlist of (detector set, leveler).
4. In parallel for each plan:
   - Run detectors, merge/dedup candidates.
   - Run leveler(s), produce entries + confidences.
   - Sanity filters (remove tables, running headers).
   - Score with ResultScorer → TOCResult.
5. Pick best `TOCResult`, map to `(level, text, page)` for `get_toc`.
6. Optional: return `diagnostics` when debugging.

### Pairing vs independence
- Default: independence (detectors find headings; levelers assign levels) for flexibility and reuse across PDF formats.
- Allow composite strategies where pairing is natural (e.g., TOCPageDetector+TOCRowLeveler) by packaging them as a “plan”.
- Orchestrator supports both seamlessly.

### Extensibility and DI
- Simple registry for detectors/levelers/scorer:
  - Default registry with batteries included.
  - Users can register custom components via code or config.
- Components receive `DocumentContext`; no globals; all heavy state cached in `DocumentContext`.

### Incremental adoption (no regressions)
- Wrap current analyzer as:
  - `FontStatsDetector` (your existing `_infer_headings`) and
  - `SizeClusterLeveler` (map H1/H2 as you do).
- Keep `embedded_strategy` as first plan.
- Introduce `ResultScorer` and Orchestrator without changing public API.
- Add one new plan at a time (e.g., TOCPageDetector), expand test corpus, adjust weights.

### Minimal public API
- Keep `extract_toc.get_toc(pdf_path)` as-is.
- Optionally add `extract_toc.extract(pdf_path, debug=True)` to return `TOCResult` with diagnostics.

### What I’d implement first (thin slice)
- `DocumentContext` + registry + orchestrator skeleton.
- Wrap existing logic into `FontStatsDetector` + `SizeClusterLeveler`.
- A conservative `ResultScorer` with only hard constraints.
- One additional detector: `TOCPageDetector` (leader dots + right-aligned page numbers).

Would you like me to scaffold these interfaces and the orchestrator so we can iterate on the selection and scoring next?
</response>

---

# User

Does the design account for extensibility in the sense of allowing for implementing highly different strategies in the future?
For example, the only existing strategy right now capitalizes on font sizes and frequencies to infer headings and heading levels, and some statistics for dynamic thresholds.
Another PDF may utilize different colors and fonts to specify headings and heading levels.
Another one may have completely useless information in the embedded span data and instead would explicitly outline a table of contents somewhere at the top of the document. In that case, the best strategy would be to detect the TOC and parse it. This is a categorically different strategy because it only relies on string matching (and has to be clever to handle different TOC styles). 
I am sure that there are additional, categorically different strategies that I can't think of now, but I will when I stumble upon a PDF with yet another different format.
Perform some brainstorming, a mix of drawing upon your training data to recall different PDF parsing strategies that you have seen, and some creative thinking, musing on how different formats PDF can have and what kind of strategies would they require (no ML and AI; besides this constraint, anything goes).
Compile a list of three to five such format->strategy pairs. The list should aim for precision and the items orthogonal in their essence, rather than exhaustiveness.
Once you have this, then you have a good basis to extrapolate it back to the right design: how do you design to allow for the development to implement creative parsing strategies that at the time of design, you cannot imagine, without limiting the future developers, and making the design make sense in the grand scheme of things? what inputs should an abstract strategy expect? what outputs? (think of what's leading to a strategy and what follows it) How could this be synergistic with the rest of their design?

---

# Assistant

<thoughts>
### Planning our approach
I need to keep my responses concise, following the developer's tool-use protocol. This task is more about brainstorming without code changes, so I can skip some steps unless it’s a multi-step task. Since we likely won’t use any tools here, I don’t need to provide status updates. I’ll compile 3-5 format and strategy pairs, focusing on design implications for extensibility. I also should incorporate the user’s earlier question about independence versus pairing to ensure the design document covers extensibility.

### Explaining architectural flexibility
I need to clarify how the architecture accommodates unknown strategies and define a minimal protocol for them. One idea is to propose a Strategy interface with two variants: a "Detector-based strategy" that produces HeadingCandidates and a "Full TOC strategy" that outputs TOCEntries. However, we might unify these by requiring all strategies to output a TOCResult. Strategies could involve various methods like OCR of TOC pages, embedded metadata, color-coded fonts, and more. Since the user prefers not to use ML/AI, we should focus on heuristics.

### Designing for future strategies
I want to ensure that our design accommodates unknown future strategies by introducing a plugin system with registration, capabilities, and optional dependencies. I’ll create a base BaseStrategy that includes a prepare(ctx) method for warm-ups like parsing or caching, and a run(ctx) method that returns a TOCResult along with an optional cost estimate. Additionally, I'll provide various typed "StrategyCapability" enumerations. DocumentContext should offer best-effort transforms, and we’ll extend it for more advanced features like color info and hyperlinks, while also implementing a lifecycle for plugins.

### Defining TOC outputs and strategies
I need to specify the outputs as a list of TOCEntry objects, which will include details like text, page, level (which can be None), section_id, confidence, and possibly source and evidence. I’ll establish normalization rules to ensure entries are sorted by page and duplicates are removed. Additionally, I plan to create synergy with the design by integrating scorers and blending detectors with levelers, using separate pipelines for different detection strategies. 
For example, one approach could focus on classic academic PDFs that utilize font size and numbering for detection, while another could use color-coded headings, leveraging a color palette-based detector.

### Supporting extensibility in design
Yes, the design explicitly supports extensibility for a variety of strategies. 
Here are three to five format->strategy pairs:
Format: Font-size/bold cluster | Strategy: Size-based detection; uses size clustering and numbering.
Format: Color/font family keyed | Strategy: Color feature detection; relies on color consistency and font identification.
Format: Printed TOC page parser | Strategy: Scans for "table of contents"; handles multiple columns and patterns.
Format: Link-annotation / outline anchor-based detection | Strategy: Parses link annotations to deduce headings and page numbers.
Format: Running headers/footers detection | Strategy: Identifies section titles in headers and derives headings using page numbering.

Regarding design implications, we’ll need to define interfaces for the core components such as the "Strategy" protocol, "Detector", "Leveler", and "ResultScorer". The DocumentContext should feature capability negotiation and facilitate plugin registration to accommodate diverse inputs.
We also emphasize synergy by utilizing pre-run selections, parallel execution, and shared feature caches. I'll keep this concise, since the user prefers high-level information rather than extensive code snippets.
</thoughts>

### Short answer
Yes. The design deliberately separates “what the PDF offers” (DocumentContext) from “how a strategy uses it” (pluggable detectors/levelers or monolithic strategies), with capability negotiation, partial outputs allowed, and post-run scoring/selection. That supports adding categorically different strategies later without redesign.

### 3–5 orthogonal format → strategy pairs

- Color-coded headings
  - Strategy: Palette-driven detector clusters spans by consistent RGB/CMYK color + font family/style across the doc; leveler uses color bands first, size/indent as tie-breakers.
  - Signals: fill color, font family, bold/italic, x-indent, repetition patterns.

- Printed “Table of Contents” pages (explicit TOC)
  - Strategy: TOC-page finder (look for “contents/table of contents” and rows with leader dots or right-aligned page numbers), then row parser (left title, leader fill, right page) across columns; leveler uses indentation and numbering in the TOC itself.
  - Signals: line grouping, dotted leaders, right-edge numeric blocks, column detection, page-range spans.

- Link-annotation/anchor-driven documents
  - Strategy: Collect intra-document links/bookmarks/anchors; map anchors to nearest visible text spans; deduplicate by unique destinations; leveler uses numbering/indent/size around anchors.
  - Signals: link annotations, outline tree, destination pages/rects, nearest-span association.

- Running headers/footers as section titles
  - Strategy: Header/footer profiler detects repeating lines; identify change-points over pages to infer section boundaries and titles; leveler uses numbering in headers and relative header styles.
  - Signals: per-page top/bottom lines, repetition frequency, change-point detection, page sequence monotonicity.

- Classic academic (size/bold/frequency)
  - Strategy: Current font-stats detector (bold, short, unique, large) with dynamic thresholds; leveler by size bands + numbering as override.
  - Signals: size distribution, bold flags, uniqueness by span text/size, number-patterns.

### Designing for unknown future strategies

- Abstract inputs (DocumentContext)
  - One parse, shared cache; lazy features on demand. Provide:
    - Spans: text, page, x/y, bbox, size, bold/italic, font family, fill color.
    - Lines/blocks with reading order; page metadata; early-page TOC cues.
    - Link annotations, outline tree; header/footer profiles; column layout guess.
    - Precomputed stats: font histograms, size clusters, line groups, numeric/dot-leader detectors.
  - Capability negotiation: strategies declare needs (e.g., needs_links, needs_colors, needs_columns). Context computes heavy features only when requested.

- Strategy interfaces (simple, future-proof)
  - Minimal unified strategy protocol (monolithic allowed):
    - `prepare(ctx) -> None` (optional warmup; respects capabilities/time budget)
    - `run(ctx) -> TOCResult`
  - Composable path (preferred for reuse):
    - HeadingDetector: `detect(ctx) -> list[HeadingCandidate]`
    - LevelInferer: `infer(candidates, ctx) -> list[TOCEntry]`
    - Or a plan bundles {detectors, leveler} for pairing when natural (e.g., TOC-page parsing).

- Outputs
  - `TOCEntry`: `text`, `page`, `level | None`, `confidence`, `provenance` (which detector/leveler, key evidence), optional `span_ids`.
  - `TOCResult`: `entries[]` (sorted, deduped), `score`, `diagnostics`.
  - Allow partial results (e.g., level=None) so a downstream leveler can refine.

- Selection and scoring
  - Pre-run plan selector (cheap cues) narrows candidate plans.
  - Parallel execution of shortlisted plans.
  - Post-run ResultScorer picks best using robust, PDF-agnostic constraints:
    - Hard: monotonic pages, no header/footer repeats, no table-like lines, sensible density.
    - Soft: numbering consistency, indentation by level, color/size coherence, link agreement.

- Extensibility ergonomics
  - Registry for strategies, detectors, levelers, scorers with metadata:
    - id, name, version, capabilities, time/memory estimate, applicability heuristics.
  - Monolithic strategies can implement `run(ctx)` only; composable ones register detectors/levelers.
  - No globals; everything flows through `DocumentContext`. Heavy computations are cached per capability flag.

- Synergy with the rest
  - Detectors and levelers can be mixed-and-matched; monolithic strategies can still plug into the same scoring/selection pipeline.
  - Shared Context prevents re-parsing; features benefit all strategies.
  - Diagnostics (provenance/evidence) aid debugging and future heuristic tuning, without coupling components.

This keeps the public API stable, supports radically different techniques (color, TOC parsing, links, headers), and leaves room for novel future strategies by constraining only the strategy I/O and shared context, not the internal method.
