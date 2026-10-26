"""Check audit integrity and reproduce scoring examples without editing the key."""
import hashlib
import importlib.util
import json
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent
ROOT = AUDIT_DIR.parent.parent
audit = json.loads((AUDIT_DIR / 'findings.json').read_text())
key = ROOT / 'reference/bookshelf-benchmark/data/ground_truth.json'
assert hashlib.sha256(key.read_bytes()).hexdigest() == audit['answer_key_sha256_before'] == audit['answer_key_sha256_after']
truth = json.loads(key.read_text())
assert sum(len(v['books']) for v in truth.values()) == audit['total_entries'] == 295
for finding in audit['findings']:
    photo = ROOT / 'reference/bookshelf-benchmark/data/images' / finding['photo']
    assert hashlib.sha256(photo.read_bytes()).hexdigest() == finding['source_image_sha256']
    assert (AUDIT_DIR / finding['evidence_crop']).is_file()
    if finding['classification'] == 'confirmed_readable_omission':
        assert finding['title_as_read'].casefold() not in {b['title'].casefold() for b in truth[finding['photo']]['books']}
    if finding['classification'] == 'confirmed_author_error':
        record = truth[finding['photo']]['books'][finding['key_entry_1_based']-1]
        assert record == {'title': finding['key_title'], 'author': finding['key_author']}
scorer_path = ROOT / 'reference/bookshelf-benchmark/benchmark/evaluate.py'
assert hashlib.sha256(scorer_path.read_bytes()).hexdigest() == audit['scorer_sha256']
spec = importlib.util.spec_from_file_location('reference_evaluator', scorer_path)
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)
for case in audit['scorer_reproductions']:
    score = scorer.title_score(case['predicted_title'], case['key_title'])[0]
    assert score == case['title_score']
    assert (score >= scorer.TITLE_THRESHOLD) == case['accepted_as_match']
    print(f"{score:.1f}: {case['predicted_title']} -> {case['key_title']}")
print('PASS: original key unchanged; source evidence integrity and scorer results reproduced.')
print('Visual judgements require human review; this script does not certify the remaining 295 entries.')
