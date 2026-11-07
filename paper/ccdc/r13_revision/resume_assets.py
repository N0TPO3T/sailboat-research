from pathlib import Path
import json,hashlib,zipfile,difflib,shutil
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-routing-v0/paper/ccdc/r13_revision')
ref='C. Yang, B. Guo, Y. Zhang, Y. Gu, Y. Li, S. Huang, H. Huang, J. Dong, and P. Li, “Learning to sail without wind information: reinforcement learning-based control for unmanned sailing vessels under partial observability,” Applied Ocean Research, vol. 175, Art. no. 105246, 2026, doi: 10.1016/j.apor.2026.105246.'
s=(p/'manuscript.md').read_text(encoding='utf-8');old=s
start=s.index('The local controller is an inherited');end=s.index('\n\n',start)
s=s[:start]+'''The dynamics implementation and pretrained assets were supplied by Chao Yang from the research codebase associated with Yang et al. [9] and are used with permission. We evaluate an inherited 18-input recurrent SAC policy with temporal attention, a matching frozen normalizer and deterministic tanh actions. This is distinct from the 14-dimensional wind-input-free policy formulation in [9]; checkpoint identity and reproduction of its benchmark results are not claimed. The Actor has hidden layers (256,256), persistent recurrent state and a ten-slot attention history. Reference [5] describes SAC. No policy is trained here. Separate instances of the inherited dynamics isolate physical execution and prediction; this does not isolate model-identification error.'''+s[end:]
start=s.index('The implemented four-degree');end=s.index('\n\n',start)
s=s[:start]+'''The implemented four-degree motion state includes position, roll, heading, body surge/sway velocities and roll/yaw rates, plus actual sail and rudder angles. Parameters include mass 25,900 kg and sail, rudder and keel areas 170, 1.17 and 8.7 m². Reference [8] supplies the original modeling lineage; software attribution to the associated research codebase [9] is separate. Exact equivalence of the Python port to the original model release is not established. Supplement S9 and S11–S12 specify the observation mapping, normalization, code/weight identities and authorized reproduction route. The internal recovery bundle loads the exact assets and reconstructs Table I from all 72 traces. The exact 18D checkpoint-to-training-run linkage remains undocumented.'''+s[end:]
s=s.replace('Author names, affiliations, funding and formal attribution/release permission for inherited assets remain to be confirmed.','Author names, affiliations and funding remain to be confirmed.')
s=s.replace('## Acknowledgment and Author Actions','''## Code and Model Availability

With permission from the inherited-asset provider, source code, pretrained weights, the matching normalizer, configurations and records needed to reproduce the reported experiments can be provided to editors and reviewers upon request. Supplement S9 and S11–S12 identify the versions and commands. This is an authorized provision route, not a claim of public release of the exact 18D assets.

## Acknowledgment and Author Actions''')
s+='\n[9] '+ref+'\n'
(p/'manuscript.md').write_text(s,encoding='utf-8')
(p/'review/round_04').mkdir(exist_ok=True)
(p/'review/round_04/MANUSCRIPT.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='round03',tofile='round04')),encoding='utf-8')
s=(p/'SUPPLEMENT.md').read_text(encoding='utf-8');old=s
start=s.index('`evidence/ASSET_HASHES.json`');end=s.index('\n\n',start)
s=s[:start]+'''`evidence/ASSET_HASHES.json`, `dynamics_parameters.json`, and `INHERITED_SOURCE_CHECK.json` specify the exact inherited files. Yang et al. [9] is the formal related research source; Chao Yang supplied the inherited dynamics implementation, 18D Actor and matching normalizer. On 2026-10-07 the user explicitly confirmed the provider's permission for this study and provision of complete source/model/reproduction materials to editors and reviewers. The confirmation is a user-reported statement, not a fabricated license file or signed correspondence. Exact asset identities and archive locations are checked in evidence/asset_resume_check.json. With this permission, the source, weights, matching normalizer, configurations and records can be provided upon request. No public release of the exact 18D assets or new open-source license is claimed. Original training-run linkage remains unknown; the journal's 14D benchmark is not reproduced or used as an identical checkpoint baseline.'''+s[end:]
s=s.replace("It is supplied for the user's authorized project work, not offered as a public release or grant of redistribution permission.","It is available for this project and, with the provider's permission confirmed by the user, can be provided to editors and reviewers upon request. It is not claimed to be publicly released and confers no additional open-source license.")
start=s.index('SOURCE_FOLLOWUP.md records a targeted source check.')
s=s[:start]+'''The supplied formal paper is Yang et al. [9], Applied Ocean Research 175 (2026) 105246, DOI 10.1016/j.apor.2026.105246. The actual supplied file is main.pdf (19 pages; SHA256 9bc5165d59141e64c32cea5f4fbc2f4464c6fe0f88b40334de85703b92d356b9), called main(1).pdf in the request. Page 1 verifies the bibliographic identity; Section 2.3, equation (27), page 6 specifies a 14-dimensional wind-input-free observation. Our actual asset is an 18-input attention variant from the related codebase, identified independently by code, input ordering, normalization and checkpoint hashes. We do not claim that the journal reports this exact variant's training or benchmark performance. Page 19 credits Chao Yang with Software and Methodology, while other authors also have Software roles; sole authorship of all inherited files is not asserted.

The journal's page 18 reports a public v1.0.3 release at https://github.com/Sailboat-RL-4DOF-Control/sailboat2026/releases/tag/v1.0.3 . This is the paper's availability statement; exact membership of our actor10800/normalizer in that release has not been checked and is not claimed. No released asset was downloaded to replace the evaluated files. The previously inspected local thesis draft remains an unpublished local document, not proof of an awarded thesis or this checkpoint's original training run.

The original author's software page https://www.mathworks.com/matlabcentral/fileexchange/47981-sailingyachtmodel-zip identifies Jerome Jouffroy's 2014-10-02 release and credits Xiao/Jouffroy [8]. Its existing notice/disclaimer conditions are preserved; equivalence of our Python port to the original source is not established. The journal's CC BY article license is not assigned to the Python code or weights. The user confirmation now resolves the previously missing provider attribution and research/reviewer-provision permission. It does not supply unknown training records, public-release status or this paper's author order, affiliations and funding. SOURCE_FOLLOWUP.md records the exact basis and scope.

[9] '''+ref+'\n'
(p/'SUPPLEMENT.md').write_text(s,encoding='utf-8')
(p/'review/round_04/SUPPLEMENT.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='round03',tofile='round04')),encoding='utf-8')
source='''# Inherited assets: confirmed source and provision scope

## Current status — user confirmation, 2026-10-07

The user explicitly reports that Chao Yang, the senior researcher who supplied the inherited research assets, has agreed to their use in this study and can provide complete source code, model weights and supporting reproduction files for editors/reviewers. This covers sailboat_s14.py, the 18D Actor and matching normalizer. The basis is the user's report of the provider's explicit agreement; no email, signature or license document is invented. Research use and reviewer provision are confirmed, not pending. No public release or new software/weight license is inferred.

## Formal research source and actual variant

'''+ref+'''

Read from the supplied 19-page main.pdf (request calls it main(1).pdf), SHA256 9bc5165d59141e64c32cea5f4fbc2f4464c6fe0f88b40334de85703b92d356b9. Page 1 gives publication identity; p6 Section2.3 Eq27 specifies 14D; p18 reports public release v1.0.3; p19 lists Yang's Software/Methodology contributions alongside other Software contributors. The paper is the research source, not proof that the exact 18D attention checkpoint was its evaluated baseline. No article benchmark number is transferred to this manuscript.

The actual 18D Actor/normalizer originate in the user-supplied saclstm_s14obst_noise_0204_actor10800.zip; docs/obstacle_candidate_identity.json records its identity and PART5/SAC-LSTM-att evaluation entries. Dynamics is the separately identified third_party/senior/sailboat_s14.py snapshot. Supplement S1 and evidence/ASSET_HASHES.json specify actual mapping/structure/identity. Full archive recheck: evidence/asset_resume_check.json. Exact hash-to-original-training-run linkage remains unknown. Membership of these assets in the journal's v1.0.3 release is not asserted.

## Preserved theory and third-party notices

Xiao and Jouffroy 2014 remains the original dynamics literature. The MathWorks FileExchange release47981, dated2014-10-02, identifies Jerome Jouffroy and credits that modeling source. Its linked copyright2014 notice and redistribution/disclaimer conditions remain intact. They are not a substitute for the separately confirmed provision of the inherited Python implementation and learned weights; code equivalence was not verified. The article's CC BY license is not converted into a license for all code or weights.

The previously read local thesis draft has a December2026 cover date and is not treated as a verified awarded thesis. Historical round01–03 uncertainty is retained in immutable submissions/reviews; it is superseded for current provider/source/provision status by the explicit user confirmation and formal paper supplied here.

Still for authors: current manuscript author order, affiliations, funding and submission metadata. These are not copied from Yang et al. No further authorization for the confirmed scope is requested.
'''
(p/'SOURCE_FOLLOWUP.md').write_text(source,encoding='utf-8')
(p/'AUTHOR_ASSET_CHECKLIST_ZH.md').write_text('''# 继承资产与作者确认表（更新）

2026-10-07 用户明确转述：师兄 Chao Yang 同意本研究使用继承资产，并可提供完整代码、权重及配套材料供编辑与审稿人复现。这是当前事实依据，不伪造书面许可证；该范围无需重复确认。

|项目|当前状态|边界|
|---|---|---|
|动力学 Python 实现、18D Actor、normalizer|由 Chao Yang 从相关研究代码库提供；本研究使用与评审材料提供已获同意|不称一人独立编写所有代码；不新增开源许可证|
|正式研究来源|Yang et al., Applied Ocean Research 175 (2026) 105246；正文[9]|期刊14D与实际18D注意力变体不同；不转移期刊成绩或声称同checkpoint复现|
|精确版本|原代码/检查点/归一化哈希、输入顺序及恢复包不变；asset_resume_check.json核验|原训练run关联未知；不保证训练holdout|
|理论及第三方说明|保留Xiao/Jouffroy与原有声明|未验证Python与原MATLAB逐项等价|
|复现材料|可依请求向编辑和审稿人提供；已有内部完整包|尚未声称公开发布，也未向真实会议提交|
|本稿作者事项|待作者确认|作者顺序、单位、邮箱、通讯作者、资助；不照抄来源论文|

当前来源与许可依据在 SOURCE_FOLLOWUP.md 统一维护。历史审稿快照保持原貌，但不作为当前未授权状态。
''',encoding='utf-8')
# Recheck existing archive bytes and exact required file presence, without running physics.
with zipfile.ZipFile(p/'R13_REPRODUCTION_internal.zip') as z:
 assert z.testzip() is None
 names=z.namelist();idx=json.loads(z.read('CONTENTS_SHA256.json'))
 print('index type',type(idx),str(idx)[:160])
 checked=[]
 for n,h in idx.items():
  assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  if any(x in n for x in ['sailboat_s14.py','actor10800','normalizer10800','freeze.json','calibration.json']):checked.append({'file':n,'sha256':h})
 traces=[n for n in names if n.endswith('trace.json')]
 assert len(traces)==72
 out={'archive_sha256':hashlib.sha256((p/'R13_REPRODUCTION_internal.zip').read_bytes()).hexdigest(),'indexed_members_verified':len(idx),'primary_traces':len(traces),'required_assets':checked,'experiments_run':0,'weights_or_method_changed':False,'permission_basis':'Explicit user report of provider agreement, 2026-10-07','paper_pdf_sha256':'9bc5165d59141e64c32cea5f4fbc2f4464c6fe0f88b40334de85703b92d356b9'}
 (p/'evidence/asset_resume_check.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
s=(p/'EVIDENCE_INDEX.md').read_text(encoding='utf-8').replace('actual primary/source lineage checks, limitations and outstanding human confirmations.','formal Yang et al. research source, confirmed provider/use/reviewer-provision scope, and 14D versus 18D identity limits.')
s+='\n## R13 asset-confirmation continuation\nUser confirmation and supplied formal paper: SOURCE_FOLLOWUP.md; exact unchanged archive check: evidence/asset_resume_check.json. Research/reviewer provision is confirmed; public release is not claimed. Review round04 contains the actual amended manuscript and concentrated A1/B1/C1 response. No experiments or figures regenerated for this source update.\n'
(p/'EVIDENCE_INDEX.md').write_text(s,encoding='utf-8')
# Metadata now nine references, no science conversion change.
f=p/'convert_to_latex.py';s=f.read_text(encoding='utf-8').replace("'references':8","'references':9");f.write_text(s,encoding='utf-8')
print('Actual source edits and unchanged reproduction archive verified')
