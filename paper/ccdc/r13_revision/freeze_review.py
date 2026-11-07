from pathlib import Path
import shutil,hashlib,json
p=Path(__file__).parent; out=p/'review_round_01_input';out.mkdir(exist_ok=True)
for n in ['manuscript.md','manuscript.docx','manuscript.pdf','SUPPLEMENT.md','CODE_FORMULA_AUDIT.md','EVIDENCE_INDEX.md','VENUE_CHECK.md','figures','evidence','code']:
 a=p/n;b=out/n
 if a.is_dir():shutil.copytree(a,b,dirs_exist_ok=True)
 else:shutil.copy2(a,b)
(out/'NEUTRAL_INDEX.md').write_text('Read full manuscript and supplement, inspect PDF pages. The main data are unchanged R12 frozen24 tasks; additional R13 evidence is log-only same-state260s comparison. evidence/analysis.json, episodes.csv, decision_260.csv, case_analysis.json and matched_prediction_quality.json support the tables/figures. Scientific source lives on donghai at /home/ot/Students/hs/sailboat-routing-v0 (read-only for review); ssh -F C:/Users/74095/.ssh/config donghai. R12 complete raw traces at runs/r12_revision_20261006/confirmation/. Local R12_raw_results.tar.gz contains raw traces if needed. Primary sources in bibliography; source provenance unresolved and explicitly disclosed. Review scope ideal-compute single-target simulation. No previous reviews supplied.\n',encoding='utf8')
h={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['manuscript.md','manuscript.docx','manuscript.pdf','SUPPLEMENT.md']}
(out/'VERSION.json').write_text(json.dumps(h,indent=2));(p/'review/round_01').mkdir(parents=True,exist_ok=True)
print(h)
