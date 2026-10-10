"""Read the original action inside the exact, verified context guard protocol.

Used by symbol/geometry regressions; raw guards are tested separately.
"""
from copy import deepcopy

CANCEL = {'sendKeys': 'Control+Shift+F9'}
RESET = {'sendKeys': 'Control+Shift+F10'}


def semantic_action(action):
    if isinstance(action, dict) and set(action) == {'combine'}:
        parts = action['combine']
        if isinstance(parts, list) and len(parts) == 3 and parts[0] == CANCEL and parts[2] == RESET:
            return parts[1]
    return action


def semantic_document(value):
    if isinstance(value, list):
        return [semantic_document(v) for v in value]
    if isinstance(value, dict):
        return {k: deepcopy(semantic_action(v)) if k == 'action' or k.endswith('Action')
                else semantic_document(v) for k, v in value.items()}
    return value
