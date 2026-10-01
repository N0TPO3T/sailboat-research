"""Read-only artifact inventory and weights-only chapter-5 compatibility check.

No pickle execution, key remapping, partial loading, or directory writes in search
roots. Run on hs against explicitly authorized roots (including read-only yc).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import zipfile
from datetime import datetime, timezone

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OMP_NUM_THREADS'] = '1'
sys.dont_write_bytecode = True


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def inventory(roots):
    weights, related, errors = [], [], []
    seen = set()
    for root in roots:
        if not root.exists(): errors.append({'path':str(root),'error':'not found'}); continue
        def onerror(exc): errors.append({'path':exc.filename,'error':str(exc)})
        for directory, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            dirs[:] = [d for d in dirs if d not in ['.git','.venv','venv','node_modules','__pycache__',
                        'site-packages','.cache','cache','tmp'] and not (Path(directory)/d).is_symlink()]
            for name in files:
                path = Path(directory)/name
                if path.is_symlink():
                    errors.append({'path':str(path),'error':'symlink not followed'}); continue
                if str(path) in seen: continue
                seen.add(str(path))
                suffix = path.suffix.lower(); lower = name.lower()
                if suffix in ['.pt','.pth','.ckpt','.zip','.pkl','.bin'] or lower.startswith(('best_model','final_model')):
                    weights.append(path)
                elif (suffix in ['.yaml','.yml','.toml','.json','.csv','.log'] or 'tfevents' in lower
                      or any(x in lower for x in ['attention','lstm','sac','chapter5','obstacle','config','train'])):
                    related.append(str(path))
    return sorted(weights), sorted(related), errors


def check(path, actor, critic):
    import torch
    stat = path.stat()
    row = {'path':str(path), 'bytes':stat.st_size, 'mtime_utc':datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat(),
           'birthtime_utc':datetime.fromtimestamp(stat.st_birthtime,timezone.utc).isoformat() if hasattr(stat,'st_birthtime') else None,
           'creation_time_limit':'mtime is not training time; birthtime unavailable on many Linux filesystems',
           'sha256':sha(path), 'attention_window':'not encoded in plain state_dict',
           'protocol_compatibility':'unknown until associated training code/config is bound'}
    if path.suffix.lower() == '.pkl':
        row.update(load_status='NOT_UNPICKLED', reason='No arbitrary pickle execution'); return row
    if path.suffix.lower() == '.zip':
        try:
            with zipfile.ZipFile(path) as z:
                row['archive_members'] = z.namelist()
            row.update(load_status='ARCHIVE_INVENTORIED_NOT_EXECUTED')
        except (OSError,zipfile.BadZipFile) as exc: row.update(load_status='INVALID_ARCHIVE', reason=str(exc))
        return row
    if stat.st_size > 512*1024**2:
        row.update(load_status='SKIPPED_OVERSIZE', reason='512MiB inspection cap; not evidence of mismatch'); return row
    try:
        obj = torch.load(path, map_location='cpu', weights_only=True)
        if not isinstance(obj, dict): row.update(load_status='NOT_STATE_DICT', type=type(obj).__name__); return row
        if isinstance(obj.get('state_dict'),dict): obj=obj['state_dict']
        row['top_keys'] = list(obj.keys())
        shapes = {k:list(v.shape) for k,v in obj.items() if isinstance(v,torch.Tensor)}
        row['tensor_shapes'] = shapes
        row['all_tensor_values_finite'] = all(bool(torch.isfinite(v).all()) for v in obj.values() if isinstance(v,torch.Tensor))
        if 'mean' in obj and 'var' in obj:
            row.update(kind='normalizer', obs_dim=int(obj['mean'].numel()), count=float(obj.get('count',0)),
                       variance_nonnegative=bool((obj['var']>=0).all()), load_status='NORMALIZER_INSPECTED')
        else:
            row['kind'] = 'actor' if 'mu_layer.weight' in shapes else 'critic' if 'Q_1.weight' in shapes else 'other'
            row['action_dim'] = shapes.get('mu_layer.weight',[None])[0]
            row['obs_dim'] = shapes.get('current_state_fc.0.weight',[None,None])[1]
            if row['obs_dim'] is None and 'fc_input.0.weight' in shapes:
                row['obs_dim'] = shapes['fc_input.0.weight'][1] - 2
            if row['kind']=='critic':
                row['obs_dim'] = shapes.get('fc_input_q1.0.weight',[None,2])[1]-2
                row['action_dim'] = 2 if row['obs_dim']==18 else 'not independently inferred'
            row['attention_keys'] = [k for k in shapes if 'att' in k.lower()]
            row['lstm_shapes'] = {k:v for k,v in shapes.items() if 'lstm' in k and 'weight' in k}
            model = actor if row['kind']=='actor' else critic if row['kind']=='critic' else None
            if model is None: row['load_status']='NOT_IDENTIFIED_AS_CURRENT_NETWORK'
            else:
                try:
                    model.load_state_dict(obj, strict=True)
                    row['load_status']='STRICT_CURRENT_CHAPTER5_PASS'
                except RuntimeError as exc:
                    row['load_status']='STRICT_CURRENT_CHAPTER5_FAIL'
                    row['load_error']=str(exc)
    except Exception as exc:
        row.update(load_status='WEIGHTS_ONLY_LOAD_FAILED',reason=f'{type(exc).__name__}: {exc}')
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', action='append', type=Path, required=True)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): parser.error('output already exists')
    if sys.platform.startswith('linux') and not args.output.resolve().is_relative_to(Path('/home/ot/Students/hs')):
        parser.error('server output must resolve inside hs')
    sys.path.insert(0,str(args.reference))
    import torch
    from utils_lstm_att_normal import Actor,Double_Q_Critic
    torch.set_num_threads(1)
    weights,related,errors=inventory(args.root)
    actor=Actor(18,2,(256,256));critic=Double_Q_Critic(18,2,(256,256),(256,128))
    rows=[]; cached={}
    for path in weights:
        row=check(path,actor,critic)
        row['nearby_evidence']=[p for p in related if str(path.parent.parent) in p][:80]
        rows.append(row)
        print(path, row['load_status'],flush=True)
    result={'roots':[str(p) for p in args.root], 'checked_at':datetime.now(timezone.utc).isoformat(),
            'reference':str(args.reference), 'reference_sha256':sha(args.reference/'utils_lstm_att_normal.py'),
            'candidates':rows,'related_files':related,'coverage_errors':errors,
            'rules':'No symlink traversal. No unsafe pickle loading. No partial state_dict loading. Missing roots are not empty roots.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f: json.dump(result,f,indent=2,ensure_ascii=False)


if __name__=='__main__':main()
