from pathlib import Path
import shutil,hashlib,json
p=Path(__file__).parent;o=p/'review_round_03_input';o.mkdir(exist_ok=True)
for n in ['manuscript.md','manuscript.pdf','manuscript.docx','SUPPLEMENT.md','SOURCE_FOLLOWUP.md','rendered']:
 a=p/n;b=o/n
 if a.is_dir():shutil.copytree(a,b,dirs_exist_ok=True)
 else:shutil.copy2(a,b)
(o/'VERSION.json').write_text(json.dumps({n:hashlib.sha256((o/n).read_bytes()).hexdigest() for n in ['manuscript.md','manuscript.docx','manuscript.pdf','SUPPLEMENT.md']},indent=2))
(o/'NEUTRAL_INDEX.md').write_text('Final copyedit identity check only: II-A supplement pointer and S12 primary-software version display clarification. All scientific evidence remains exactly review_round_02_input/evidence, one directory up. Full input text/PDF and pages included. No new human attribution/access evidence. See own previous review and review/round_02/FINAL_COPYEDIT_RESPONSE.md; do not read other reviewers.\n')
(p/'review/round_03').mkdir(exist_ok=True);print((o/'VERSION.json').read_text())
