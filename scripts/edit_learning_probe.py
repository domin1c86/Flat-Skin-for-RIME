"""Analyze observable Rime edits into an UNVERIFIED shadow text.

This deliberately has no database writer. Rime events do not establish the
host cursor, selection, document identity, final text, or reading alignment.
Even a plausible suffix reconstruction is not sufficient permission to learn.
"""
import argparse
import json
from pathlib import Path


def analyze(events):
    draft = ''
    editing = False
    invalid = None
    commits = []
    last_commit_time = None
    for event in events:
        kind = event.get('event')
        if kind == 'init':
            draft, editing, invalid, commits, last_commit_time = '', False, None, [], None
        elif kind == 'commit':
            text = event.get('text', '')
            if not isinstance(text, str):
                invalid = 'invalid_commit'
                continue
            draft += text
            last_commit_time = event.get('time')
            commits.append({'text': text, 'observed_code': event.get('code', ''),
                            'script': event.get('script', '')})
        elif kind == 'key':
            key = event.get('key', '')
            if key in ('Left', 'Right', 'Home', 'End'):
                invalid = 'host_cursor_not_observable'
            elif key == 'BackSpace' and not event.get('preedit_input'):
                editing = True
                timestamp = event.get('time')
                if last_commit_time is None or not isinstance(timestamp, (int, float)) or (
                        timestamp < last_commit_time or timestamp - last_commit_time > 3):
                    invalid = 'outside_recent_edit_window'
                elif draft:
                    draft = draft[:-1]
                else:
                    invalid = 'deletion_outside_observed_text'
            elif key in ('Control+Shift+F10', 'Return', 'Escape'):
                invalid = 'context_boundary'
        elif kind in ('host_selection', 'host_focus_changed', 'external_text_changed', 'context_boundary'):
            invalid = 'host_edit_not_fully_observable'
    return {
        'status': 'unsupported_edit' if invalid else ('partial_reconstruction' if editing else 'commit_sequence_only'),
        'assumed_text': draft if not invalid else None,
        'learn_allowed': False,
        'reason': invalid or 'missing_confirmed_host_text_cursor_and_reading_alignment',
        'commits': commits,
        'writes_to_user_dictionary': 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path, help='isolated JSONL event trace')
    args = parser.parse_args(argv)
    events = [json.loads(line) for line in args.trace.read_text(encoding='utf-8').splitlines() if line.strip()]
    print(json.dumps(analyze(events), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
