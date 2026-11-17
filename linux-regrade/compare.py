"""Compare the Linux official-harness results with the macOS records (AMENDMENT-02).

    python3 compare.py <stage-b-review-artifact dir> <output dir>

Reads:
- the harness reports for run ids "stageb-model" and "stageb-gold" under
  logs/run_evaluation/;
- linux-recheck.json.

Writes summary.json and prints a short table.
"""
import json
import sys
from pathlib import Path

TASKS = ['psf__requests-3362', 'pallets__flask-4045', 'pallets__flask-4992']
ROOT, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()


def harness_report(run_id, model, task):
    p = OUT / 'logs' / 'run_evaluation' / run_id / model / task / 'report.json'
    return json.loads(p.read_text())[task] if p.exists() else None


def main():
    recheck = json.loads((OUT / 'linux-recheck.json').read_text()) if (OUT / 'linux-recheck.json').exists() else None
    summary = {}
    for t in TASKS:
        A = json.loads((ROOT / 'runs' / t / 'analysis.json').read_text())
        mac_f2p_failed = sorted({k for g in A['grading'] for k, v in g['F2P'].items() if v != 'PASSED'})
        mac_p2p_failed = sorted({k for g in A['grading'] for k in g['P2P_failed']})
        m, g = harness_report('stageb-model', 'stageb', t), harness_report('stageb-gold', 'gold', t)
        row = {'macos_resolved': A['resolved'], 'macos_f2p_failed': mac_f2p_failed,
               'macos_p2p_failed': mac_p2p_failed}
        if m:
            ts = m.get('tests_status', {})
            row.update({'linux_patch_applied': m.get('patch_successfully_applied'),
                        'linux_resolved': m.get('resolved'),
                        'linux_f2p_failed': sorted(ts.get('FAIL_TO_PASS', {}).get('failure', [])),
                        'linux_p2p_failed': sorted(ts.get('PASS_TO_PASS', {}).get('failure', []))})
            row['resolved_agrees'] = row['linux_resolved'] == row['macos_resolved']
            row['f2p_failures_agree'] = row['linux_f2p_failed'] == mac_f2p_failed
            row['p2p_failures_agree'] = row['linux_p2p_failed'] == mac_p2p_failed
        row['gold_resolved_on_linux'] = g.get('resolved') if g else None
        if recheck and t in recheck['tasks']:
            rt = recheck['tasks'][t]
            row['linux_patch_apply_exit'] = rt['patch_apply_exit']
            row['linux_tree_matches_final_patch'] = rt['tree_matches_final_patch_sha256']
            row['recheck_rows'] = []
            for r in rt['rows']:
                la = [x['exit'] for x in r['as_run']]
                lf = [x['exit'] for x in r['source_forced']]
                row['recheck_rows'].append({
                    'command': r['command'][:160], 'macos': [r['macos_as_run'], r['macos_source_forced']],
                    'linux': [la, lf], 'same': [la, lf] == [r['macos_as_run'], r['macos_source_forced']],
                    'linux_as_run_equals_forced': la == lf})
        summary[t] = row
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2))
    for t, r in summary.items():
        print(f"\n{t}")
        print(f"  resolved   macOS={r['macos_resolved']}  Linux={r.get('linux_resolved')}  gold-on-Linux={r['gold_resolved_on_linux']}")
        print(f"  F2P fail   macOS={r['macos_f2p_failed']}  Linux={r.get('linux_f2p_failed')}")
        print(f"  P2P fail   macOS={len(r['macos_p2p_failed'])}  Linux={len(r.get('linux_p2p_failed') or [])}")
        for x in r.get('recheck_rows', []):
            flag = 'same' if x['same'] else 'DIFF'
            print(f"  recheck {flag:4s} mac={x['macos']} linux={x['linux']}  {x['command'][:70]}")


if __name__ == '__main__':
    main()
