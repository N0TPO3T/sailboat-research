# Track A visual closeout — 2026-10-13

## Scope and source

The author approved the compact Fig. 1 v2 and delegated review/polish of all figures and tables. This later instruction authorizes presentation-only redraws beyond the October 9 prompt's default of preserving other plots. The content source is the completed local track_A_closeout_20261009 edition, not an R12/R13 manuscript. The October 9 response and actual independent check are preserved under provenance/ with dated names; their conclusions apply to that edition, not automatically to this PDF.

Read-only server listing on October 13 still showed track_A_submit and historical R11–R13 drafts, with no October 8/9/13 editing directory. This is a new local edition and has not been synchronized, pushed, uploaded or submitted. Existing local modifications and every earlier edition are preserved. No method, parameter, weight, scientific implementation, experiment or Track B artifact is changed.

## Figure and table changes

| Item | Actual change | Preservation check |
| --- | --- | --- |
| Fig. 1 | Adopted approved short-label two-panel diagram; full-width placement before Section III. Blue denotes reconstruction/prediction, teal nominal return, ochre alternative evaluation. | Guard pass returns directly; only failure evaluates alternatives. Memory/setpoints remain distinct; history isolation and old-action / delayed-reference timing remain explicit. Detailed conditions remain in III-A, Algorithm 1 and Supplement S2. No claimed computational improvement. |
| Fig. 2 | Shared key, short axes, panel letters, distinct method shapes and muted palette. | All 24 tasks, 19 common-safe pairs per predictor versus R, all 72 margins and safety marks retained; failed pairs are not zero time. Symlog threshold remains 3 m. |
| Fig. 3 | Shared trajectory key outside the data, redundant line styles; durations moved to caption. | All original trajectory samples, target motion, 260 s markers, static and dynamic exclusions, minimum-margin endpoints and 240–460 s encounter window retained. Unsafe arrival is not described as efficiency. |
| Fig. 4 | Matches Fig. 3 styling with unshifted coincident R/L tracks. | R/L 279 s, S15 587 s and +308 s counterexample retained. Full tracks and clearance histories retained. |
| Fig. 5 | Short axes; filled-circle mean and open-square maximum in the S15 color. | Same four guards; ten common-safe pairs for time, twelve tasks for worst margin. No monotonic-performance or optimal-guard claim. |
| Fig. 6 | Removed long titles/shaded bands, kept snapshot separators and protocol labels. | All twelve branches, ten 60 s and two 58 s common intervals, open L/filled S15 markers, 106.064 m adverse error and snapshot-4 dependence retained. |
| Tables I–III | Consistent light-blue header, aligned numerical cells, explicit light rules, adequate cell spacing and non-splitting rows. | All original cell text and numerical values preserved. |
| Tables S1–S4 | Editable single-column supplement layout; tailored column widths and consistent headers/rules. | All cell text, units, identifiers, historical overlap and denominators preserved. Independent numbering unchanged. |

## Existing M1–M4 and limitations

M1's measured safety–time–computation trade-off wording and M2's design/consistency/integrated-effect distinction are unchanged. M3's 23 common-safe S15/L pairs are recomputed from unchanged confirmation CSV: 5 faster, 13 equal, 5 slower; range −136 to +308 s, mean +7 s, median 0. Equal travel times do not imply identical trajectories. M4's nominal-first branch is preserved in the accepted figure. The full manuscript keeps the 19/23/24 result, 3/7/8 pressure split, computational costs, paused physical time, calibration limitation, negative results and 12-prefix versus 6-selected-continuation distinction.

## Reproducibility and verification

plot_data.json contains only frozen plotting columns needed for Figures 2–6, including all displayed case samples. FIGURE_DATA_CHECK.json records source identities and checks; plot_figures.py regenerates the five plots without private machine paths. This is not the complete simulator or weights. The unchanged evidence directory and minimal paired-time check remain supplied. Full recovery access stays separate, as described in README.md and Supplement S5/S11.

The existing Word template and Microsoft Word export chain generate the primary PDF. No official margins or body styles were reduced. The packaged LibreOffice renderer was attempted but soffice.exe is unavailable; therefore actual Word-exported PDFs are rasterized with Poppler for page inspection. The main paper is 8 pages; the supplement is 6 pages. Figure vectors and 300 dpi PNGs are supplied. Optional LaTeX is not a delivered build in this edition.

Author self-check covers every final page, figure, table, numerical-cell preservation and Markdown-to-Word consistency. A separate independent agent checks this same final PDF, supplement and response once; its signed-scope report is INDEPENDENT_VISUAL_CHECK.md. No acceptance scoring or repeated research review is requested. Only corresponding author, email and applicable funding remain for the authors to supply.
