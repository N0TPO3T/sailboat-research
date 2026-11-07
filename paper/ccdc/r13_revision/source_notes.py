from pathlib import Path
import hashlib,json
p=Path(__file__).parent
(p/'SOURCE_FOLLOWUP.md').write_text('''# Targeted inherited-source follow-up (R13)

Verified local lineage: the 18D Actor and normalizer are the members of the user-supplied saclstm_s14obst_noise_0204_actor10800.zip (archive SHA256 f3d8f7c0c715fc6e2c312f8ba7656c9f8e0b726a598279bb071e03c8d561c73f); docs/obstacle_candidate_identity.json points to PART5/SAC-LSTM-att/modeltest_noise.py and batchtest.py. The runtime physics is separately the sailboat_RL/gymnasium/envs/sailboat/sailboat_s14.py snapshot in UPSTREAM_MANIFEST, not automatically the obstacle-training environment. R6 source and asset identity records remain authoritative.

A relevant local thesis draft was found at /home/ot/Students/hs/sailboat-research/大论文-Final.pdf (SHA256 d04dc4813a01d2dff1f643c056f6f689c4ead38d1c9886a60b6e42185abe4b29). Title page names Chao Yang (杨潮), Zhejiang University, “The Research on Unmanned Sailboat Control Model Based on Reinforcement Learning”, dated December2026, later than this October2026 verification. It must be treated as an unpublished/local draft, not a verified awarded thesis or published source. Section2.3 (printed p29–30) explicitly attributes the four-degree dynamics structure/parameters to Xiao and Jouffroy; Chapter5 discusses temporal attention and a10step window. This is a source-author statement, not independent proof that the exact current code/checkpoint reproduces that work. The older 师兄大论文.pdf (SHA256 e73ea4c85a1f5bcd1b29d54b5e1ef69c2f5161f3166f652371e6eddf2b35b0e0) leaves author blanks and bears June2026 on the cover.

No checkpoint hash-to-training-run mapping, completed/public thesis identity, or release license was established by these documents. Do not transfer their reported performance to the current method. Do not publish the full private thesis in the preview. The user was asked once for original attribution/training linkage and release permission; pending response. Local lineage is materially clearer, but exact training provenance and public reproduction remain unresolved.
''',encoding='utf8')
(p/'latex/README_ZH.md').write_text('''# LaTeX编辑版
main.tex由同目录上级manuscript.md转换；正文和6个公式、2张表、6幅图保持对应。IEEEtran.cls来自用户提供的模板，图使用矢量PDF。建议在已有TeX环境或Overleaf以pdfLaTeX编译。当前Codex内置编译器报Unable to find standard directories for platform，尚未成功编译；正式可读PDF为Word模板导出的../manuscript.pdf，不能冒称LaTeX编译产物。最终审稿修改后再次生成本文件。
''',encoding='utf8')
(p/'latex/compile.log').write_text('Native compiler: compile-failed\nUnable to find standard directories for platform\nNo LaTeX PDF generated.\n')
print('Source lineage and actual compile limitation saved')
