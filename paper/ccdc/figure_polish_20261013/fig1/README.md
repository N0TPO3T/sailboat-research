# Fig. 1 visual draft v1 — 2026-10-13

Source: track_A_closeout_20261009, Fig. 1 and Algorithm 1. This is an isolated visual proposal; no manuscript or scientific result has been replaced.

Layout: intended full two-column width 7.05 inches, height 4.7 inches. Nodes use 8.2–9 pt serif text, panel labels 10 pt. Color supplements explicit Pass/Fail text; the graph remains interpretable in grayscale. Reconstruction, nominal-first guard selection, early return and delayed real execution are preserved. The dashed line is the eligibility bypass; there is no prediction-to-real-history update.

Files: draw_fig1.py (Matplotlib source), figure1_v1.svg (editable vector), figure1_v1.pdf (vector), figure1_v1.png (300 dpi preview). The FigureSpec helper in the installed ARIS checkout is incomplete; this draft reuses the existing plotting runtime and was visually inspected, not validated by that missing helper. No independent review or full-paper pagination claim is made for this exploratory design.

Proposed caption: Reference-protocol selection and execution. (a) Eligibility is checked before local wind fitting and the separate reconstruction of controller memory and actuator setpoints. (b) A valid, integration-successful nominal rollout meeting the guard returns without evaluating alternatives; otherwise available continuation and side protocols are predicted and ranked using the existing fallback. Each predicted history remains isolated from real history. The pending old action executes first; a changed reference applies at t+1 and first affects the interval t+1 to t+2.

Pending author choice: adopt a full-width layout or retain a single-column format. Full-paper placement and page count will be checked only after that choice.
