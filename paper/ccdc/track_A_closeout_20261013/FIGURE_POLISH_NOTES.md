# Data-figure polish (2026-10-13)

Scope: main-paper Figures 2–6 only. Figure numbering follows the current manuscript; filenames retain their historical names to preserve references.

| Paper figure | File | Presentation changes |
|---|---|---|
| 2 | figure2_confirmation | One shared key; short axis labels; panel letters instead of repeated titles; same 24 tasks, 19 common-safe pairs per predictor, symmetric-log threshold 3 m, all safety-status marks. Margin bounds −3 to 420 m contain every value (range −1.41234 to 329.04291 m). |
| 3 | figure5_rescue | Shared key above panels, short labels, unchanged complete tracks and 240–460 s clearance window, unchanged synchronized markers and exclusion circles. |
| 4 | figure6_adverse | Same style as Fig.3. R/L coincident paths stay coincident; different dash patterns and line widths make shared portions more visible without offsetting data. |
| 5 | figure3_guard | Mean/maximum use the same S15 color with filled-circle solid/open-square dashed encoding; no cross-method color implication. |
| 6 | figure4_prediction | Compact labels, no shaded bands, light snapshot separators, preserved protocol shapes and open-L/filled-S15 marks. |

Palette: R teal `#397F79`, L ochre `#B78147`, S15 blue `#507DA5`. Shapes and line styles provide redundant identity; gray denotes target/static entities. No simulated output or experimental result was changed.

## Caption integration required

- Fig.2: state (a) 19 common-safe pairs **per predictor** versus R; (c) circles denote safe completion and crosses failure. Keep symmetric-log definition and failed-pair exclusion.
- Fig.3: retain or add complete-run durations R 392 s, L 566 s, S15 519 s, removed from the crowded key. These are durations, not a claim that unsafe L arrival is efficient.
- Fig.4: retain/add R and L 279 s, S15 587 s, +308 s cost; R/L tracks coincide.
- Fig.5: state (a) ten common-safe pairs, (b) all twelve tasks per guard.
- Fig.6: define margin residual as predicted minus actual minimum margin over the common interval. Keep the ten 60 s / two 58 s windows and snapshot-4 nonindependence caveat.

## Reproduction and preservation

Run `python plot_figures.py` with Python, NumPy and Matplotlib. All inputs are in `plot_data.json`; no author-machine path or full recovery archive is needed for ordinary regeneration. Individual wrappers in `figures/` regenerate one plot. Editable text is retained in SVG, PDF is vector, PNG is 300 dpi.

`extract_figure_data.py ARCHIVE_PATH` documents optional input extraction. It reads only six existing trace members from the original recovery archive; it does not extract model weights or run experiments. Every case trace matches the current confirmation CSV on completion time, safety, minimum margin and path length. All trajectory coordinates and clearance samples are copied without simplification. `FIGURE_DATA_CHECK.json` records source hashes, sample counts and checks. The frozen matched-prediction records retain the S15 106.0636595 m maximum error and all adverse residuals.

Rendered all five PNGs and visually inspected them after plotting, including axis labels, bounds, keys, negative margins and protocol markers. Checked final adverse-case image separately. The final manuscript PDF still requires root-agent layout inspection. No independent review is claimed by this authoring step.
