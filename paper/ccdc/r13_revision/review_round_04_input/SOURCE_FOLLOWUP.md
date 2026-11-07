# Inherited assets: confirmed source and provision scope

## Current status — user confirmation, 2026-10-07

The user explicitly reports that Chao Yang, the senior researcher who supplied the inherited research assets, has agreed to their use in this study and can provide complete source code, model weights and supporting reproduction files for editors/reviewers. This covers sailboat_s14.py, the 18D Actor and matching normalizer. The basis is the user's report of the provider's explicit agreement; no email, signature or license document is invented. Research use and reviewer provision are confirmed, not pending. No public release or new software/weight license is inferred.

## Formal research source and actual variant

C. Yang, B. Guo, Y. Zhang, Y. Gu, Y. Li, S. Huang, H. Huang, J. Dong, and P. Li, “Learning to sail without wind information: reinforcement learning-based control for unmanned sailing vessels under partial observability,” Applied Ocean Research, vol. 175, Art. no. 105246, 2026, doi: 10.1016/j.apor.2026.105246.

Read from the supplied 19-page main.pdf (request calls it main(1).pdf), SHA256 9bc5165d59141e64c32cea5f4fbc2f4464c6fe0f88b40334de85703b92d356b9. Page 1 gives publication identity; p6 Section2.3 Eq27 specifies 14D; p18 reports public release v1.0.3; p19 lists Yang's Software/Methodology contributions alongside other Software contributors. The paper is the research source, not proof that the exact 18D attention checkpoint was its evaluated baseline. No article benchmark number is transferred to this manuscript.

The actual 18D Actor/normalizer originate in the user-supplied saclstm_s14obst_noise_0204_actor10800.zip; docs/obstacle_candidate_identity.json records its identity and PART5/SAC-LSTM-att evaluation entries. Dynamics is the separately identified third_party/senior/sailboat_s14.py snapshot. Supplement S1 and evidence/ASSET_HASHES.json specify actual mapping/structure/identity. Full archive recheck: evidence/asset_resume_check.json. Exact hash-to-original-training-run linkage remains unknown. Membership of these assets in the journal's v1.0.3 release is not asserted.

## Preserved theory and third-party notices

Xiao and Jouffroy 2014 remains the original dynamics literature. The MathWorks FileExchange release47981, dated2014-10-02, identifies Jerome Jouffroy and credits that modeling source. Its linked copyright2014 notice and redistribution/disclaimer conditions remain intact. They are not a substitute for the separately confirmed provision of the inherited Python implementation and learned weights; code equivalence was not verified. The article's CC BY license is not converted into a license for all code or weights.

The previously read local thesis draft has a December2026 cover date and is not treated as a verified awarded thesis. Historical round01–03 uncertainty is retained in immutable submissions/reviews; it is superseded for current provider/source/provision status by the explicit user confirmation and formal paper supplied here.

Still for authors: current manuscript author order, affiliations, funding and submission metadata. These are not copied from Yang et al. No further authorization for the confirmed scope is requested.
