from pathlib import Path
import shutil,hashlib,json,zipfile
p=Path(__file__).parent;out=p/'review_round_02_input';out.mkdir(exist_ok=True)
for n in ['manuscript.md','manuscript.docx','manuscript.pdf','SUPPLEMENT.md','EVIDENCE_INDEX.md','VENUE_CHECK.md','SOURCE_FOLLOWUP.md','NUMERIC_PLAN.md','figures','evidence','code']:
 a=p/n;b=out/n
 if a.is_dir():shutil.copytree(a,b,dirs_exist_ok=True)
 else:shutil.copy2(a,b)
assert zipfile.ZipFile(p/'R13_REPRODUCTION_internal.zip').testzip() is None
(out/'NEUTRAL_INDEX.md').write_text('Revised whole paper and supplement; same original frozen scientific methods/results. Read SOURCE_FOLLOWUP.md for actual discovered primary/local source lineage and still-unconfirmed attribution/access. Actual complete internal reproduction archive is one directory above at R13_REPRODUCTION_internal.zip; evidence/recovery_check.json/log prove fresh-directory model load and primary table reconstruction. Three extra numerical replays of existing commands are in new_case_substeps.json, not new tasks. No first-round reviews/opinions from other reviewers included. Your own response and original opinion are provided separately. Native Word PDF is actual; LaTeX source is supplementary and native compiler unavailable, not claimed compiled.\n',encoding='utf8')
(out/'VERSION.json').write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['manuscript.md','manuscript.docx','manuscript.pdf','SUPPLEMENT.md']},indent=2))
(p/'review/round_02').mkdir(parents=True,exist_ok=True)
print((out/'VERSION.json').read_text())
