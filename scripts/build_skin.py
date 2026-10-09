"""Compile Jsonnet, validate the generated keyboard graph, and package a .cskin.

Python 3.10+ and the Jsonnet CLI are sufficient; no Python packages are required.
All emitted .yaml files use JSON syntax, which is valid YAML.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKIN = ROOT / "default"
REFERENCE_FIELDS = {
    "backgroundStyle", "foregroundStyle", "uppercasedStateForegroundStyle",
    "capsLockedStateForegroundStyle", "preeditStateForegroundStyle", "hintStyle",
    "hintSymbolsStyle", "hintSymbolsGridStyle", "candidateStyle", "cellStyle",
    "selectedBackgroundStyle", "styleName", "style", "notification", "dataSource",
}
LAYOUT_FIELDS = ("toolbarLayout", "keyboardLayout", "horizontalCandidatesLayout", "verticalCandidatesLayout")
STYLE_TYPES = {"geometry", "text", "systemImage", "assetImage", "fileImage"}
CELL_TYPES = {"button", "symbols", "classifiedSymbols", "subClassifiedSymbols", "horizontalSymbols",
              "horizontalCandidates", "verticalCandidates", "numericSymbols", "categorySymbols"}
STANDARD_ACTIONS = {"space", "enter", "tab", "shift", "backspace", "dismissKeyboard", "nextKeyboard",
                    "returnPrimaryKeyboard", "returnLastKeyboard", "symbolicKeyboardLockStateToggle", "none"}
SHORTCUTS = {"#中英切换", "#次选上屏", "#showPasteboardView", "#toggleScriptView", "#keyboardMenu",
             "#toggleSplitState", "#方案切换", "#candidatesBarStateToggle", "#verticalCandidatesPageUp", "#verticalCandidatesPageDown"}


class SkinError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SkinError(message)


def walk(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield path + "/" + key, key, item
            yield from walk(item, path + "/" + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, path + "/" + str(index))


def references(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                yield item


def validate_action(action, context):
    if isinstance(action, str):
        require(action in STANDARD_ACTIONS, f"{context}: unknown action {action}")
    else:
        require(isinstance(action, dict) and len(action) == 1, f"{context}: invalid action")
        kind, value = next(iter(action.items()))
        if kind == "combine":
            require(isinstance(value, list) and value, f"{context}: empty combine")
            for nested in value:
                validate_action(nested, context)
        else:
            require(kind in {"character", "symbol", "shortcut", "keyboardType"}, f"{context}: unknown action type {kind}")
            require(isinstance(value, str) and bool(value), f"{context}: empty action value")
            if kind == "shortcut":
                require(value in SHORTCUTS, f"{context}: unknown shortcut {value}")


def validate_document(doc):
    require(isinstance(doc, dict), "keyboard must be an object")
    for height in ("preeditHeight", "toolbarHeight", "keyboardHeight"):
        require(type(doc.get(height)) in (int, float) and doc[height] > 0, f"missing/invalid {height}")
    for path, key, value in walk(doc):
        if key in REFERENCE_FIELDS or key == "Cell":
            for name in references(value):
                require(name in doc, f"{path}: missing reference {name}")
        if key.endswith("Color"):
            require(isinstance(value, str) and re.fullmatch(r"#?(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value), f"{path}: invalid color {value}")
        if key == "buttonStyleType":
            require(value in STYLE_TYPES, f"{path}: invalid style type")
        if key == "type":
            require(value in CELL_TYPES, f"{path}: invalid cell type")
        if key == "action" or key.endswith("Action"):
            validate_action(value, path)
        if key == "notificationType":
            require(value in {"rime", "keyboardAction", "returnKeyType", "preeditChanged"}, f"{path}: invalid notification type")
    for name, node in doc.items():
        if not isinstance(node, dict):
            continue
        if node.get("type") == "classifiedSymbols":
            categories = doc[node["dataSource"]]
            require(isinstance(categories, list) and categories, f"{name}: missing categories")
            for category in categories:
                require(isinstance(category, str) and isinstance(doc.get(category), list) and doc[category], f"{name}: category {category} has no symbols")
        if node.get("type") in {"symbols", "classifiedSymbols", "subClassifiedSymbols"}:
            cell = doc[node["cellStyle"]]
            foreground = cell.get("foregroundStyle")
            require(isinstance(foreground, str) and doc[foreground].get("buttonStyleType") == "text", f"{name}: collection cell requires a text foreground")
        if node.get("notificationType") == "rime":
            require(node.get("rimeNotificationType") == "optionChanged" and node.get("rimeOptionName") and type(node.get("rimeOptionValue")) is bool, f"{name}: incomplete RIME notification")
        if node.get("notificationType") == "keyboardAction":
            require("notificationKeyboardAction" in node, f"{name}: missing notification action")
        if node.get("notificationType") == "returnKeyType":
            require(node.get("returnKeyType"), f"{name}: missing return-key types")
    for field in LAYOUT_FIELDS:
        require(isinstance(doc.get(field), list) and doc[field], f"missing {field}")
        layout_rectangles(doc, field, 390, 400)


def length(value, available):
    if value is None:
        return None
    if isinstance(value, dict):
        result = float(value["percentage"]) * available
    elif isinstance(value, str):
        numerator, denominator = value.split("/")
        denominator = float(denominator)
        require(denominator != 0, "size denominator must not be zero")
        result = float(numerator) / denominator * available
    else:
        require(type(value) in (int, float), f"invalid size {value}")
        result = float(value)
    require(math.isfinite(result) and result >= 0, f"invalid size {value}")
    return result


def layout_rectangles(doc, field, width, height):
    """Resolve the engine's HStack/VStack allocation; also detect silent overflows."""
    rectangles = []

    def allocate(nodes, rect, parent=None):
        require(nodes, "empty layout")
        kinds = {next(iter(node)) for node in nodes}
        require(len(kinds) == 1 and kinds <= {"HStack", "VStack", "Cell"}, "mixed/unknown layout siblings")
        kind = next(iter(kinds))
        require(parent is not None or kind != "Cell", "Cell cannot be a layout root")
        axis = "height" if kind == "HStack" or (kind == "Cell" and parent == "VStack") else "width"
        x, y, w, h = rect
        available = h if axis == "height" else w
        sizes = []
        for node in nodes:
            params = doc[node["Cell"]] if kind == "Cell" else doc.get(node[kind].get("style"), {})
            require(isinstance(params, dict), "layout style must be an object")
            sizes.append(length(params.get("size", {}).get(axis), available))
        remainder = available - sum(size for size in sizes if size is not None)
        require(remainder >= -0.01, f"{field}: {axis} overflow by {-remainder:.2f}pt")
        automatic = sizes.count(None)
        if not automatic:
            require(abs(remainder) < 0.01, f"{field}: explicit sizes leave {remainder:.2f}pt unused")
        cursor = 0
        for node, size in zip(nodes, sizes):
            size = max(0, remainder) / automatic if size is None else size
            child = (x, y + cursor, w, size) if axis == "height" else (x + cursor, y, size, h)
            cursor += size
            if kind == "Cell":
                rectangles.append((node["Cell"], child))
            else:
                allocate(node[kind]["subviews"], child, kind)
    allocate(doc[field], (0, 0, width, height))
    return rectangles


def split_document(doc):
    def apply(value):
        if isinstance(value, list):
            return [apply(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: apply(item) for key, item in value.items() if key != "split"}
        # The engine overlays split fields one level deep; no arbitrary deep merge.
        result.update(deepcopy(value.get("split", {})))
        return result
    return apply(doc)


def validate_image_resources(doc, folder):
    for name, node in doc.items():
        if not isinstance(node, dict) or node.get('buttonStyleType') != 'fileImage':
            continue
        require(node.get('contentMode') == 'scaleAspectFit', f'{name}: image must preserve aspect ratio')
        for field in ('normalImage', 'highlightImage'):
            resource = node.get(field)
            if resource is None and field == 'highlightImage':
                continue
            require(isinstance(resource, dict), f'{name}: missing {field}')
            filename = resource.get('file', '')
            require(isinstance(filename, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', filename), f'{name}: invalid image file')
            png, descriptor_path = folder / (filename + '.png'), folder / (filename + '.yaml')
            require(png.is_file() and descriptor_path.is_file(), f'{name}: missing image resource {filename}')
            data = png.read_bytes()
            require(len(data) >= 24 and data[:8] == b'\x89PNG\r\n\x1a\n', f'{name}: invalid PNG')
            width, height = struct.unpack('>II', data[16:24])
            descriptor = json.loads(descriptor_path.read_text(encoding='utf-8'))
            require(resource.get('image') in descriptor, f'{name}: missing sprite {resource.get("image")}')
            rect = descriptor[resource['image']].get('rect', {})
            require(all(type(rect.get(k)) is int for k in ('x', 'y', 'width', 'height')), f'{name}: invalid sprite rectangle')
            require(rect['x'] >= 0 and rect['y'] >= 0 and rect['width'] > 0 and rect['height'] > 0
                    and rect['x'] + rect['width'] <= width and rect['y'] + rect['height'] <= height, f'{name}: sprite outside image')


def validate_skin(skin=SKIN):
    config = json.loads((skin / "config.yaml").read_text(encoding="utf-8"))
    required = set()
    for keyboard in ("pinyin", "numeric", "symbolic"):
        for device, scenes in (("iPhone", ("portrait", "landscape")), ("iPad", ("portrait", "landscape", "floating"))):
            for scene in scenes:
                name = config.get(keyboard, {}).get(device, {}).get(scene)
                require(isinstance(name, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name), f"missing/invalid mapping {keyboard}/{device}/{scene}")
                required.add(name + ".yaml")
    for scheme in ("light", "dark"):
        require({path.name for path in (skin / scheme).glob("*.yaml")} == required, f"{scheme}: keyboard files do not match config")
        for filename in sorted(required):
            path = skin / scheme / filename
            doc = json.loads(path.read_text(encoding="utf-8"))
            try:
                validate_document(doc)
                validate_image_resources(doc, skin / scheme / 'resources')
                is_pad = filename.startswith("iPad")
                widths = [768, 1024] if is_pad else ([568, 680, 844] if "Landscape" in filename else [320, 390, 430])
                for width in widths:
                    for candidate in ([doc, split_document(doc)] if is_pad else [doc]):
                        layout_rectangles(candidate, "keyboardLayout", width, candidate["keyboardHeight"])
            except (SkinError, KeyError, TypeError, ValueError) as error:
                raise SkinError(f"{scheme}/{filename}: {error}") from error
    require((skin / "demo.png").is_file(), "missing demo.png")
    return len(required) * 2


def compile_skin(binary):
    completed = subprocess.run([str(binary), str(SKIN / "jsonnet" / "main.jsonnet")], capture_output=True, text=True, encoding="utf-8")
    require(completed.returncode == 0, completed.stderr)
    output = json.loads(completed.stdout)
    for relative, contents in output.items():
        path = (SKIN / relative).resolve()
        require(path.is_relative_to(SKIN) and path.suffix == ".yaml", f"invalid output path {relative}")
        require(isinstance(contents, str), f"{relative}: output is not text")
        json.loads(contents)
    for relative, contents in output.items():
        path = SKIN / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents + "\n", encoding="utf-8")


def package_skin(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = [SKIN / "config.yaml", SKIN / "README.md", SKIN / "demo.png"]
    paths += sorted(path for folder in ("light", "dark", "jsonnet") for path in (SKIN / folder).rglob("*") if path.is_file())
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            # One UTF-8 skin-name directory is required by the import format.
            info = zipfile.ZipInfo("扁平灰白/" + path.relative_to(SKIN).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(output) as archive:
        require(archive.testzip() is None, "archive CRC validation failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonnet", type=Path, help="Jsonnet executable path")
    parser.add_argument("--check", action="store_true", help="validate existing generated files only")
    parser.add_argument("--compile-only", action="store_true", help="compile and validate, without packaging")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "扁平灰白.cskin")
    args = parser.parse_args()
    try:
        if not args.check:
            binary = args.jsonnet or shutil.which("jsonnet") or ROOT / ".tools" / ("jsonnet.exe" if sys.platform == "win32" else "jsonnet")
            require(Path(binary).is_file(), "Jsonnet CLI not found; install jsonnet or pass --jsonnet PATH")
            compile_skin(binary)
        count = validate_skin()
        print(f"Validated {count} light/dark keyboard files, mappings, references, actions, colors, normal/split layouts.")
        if not args.check and not args.compile_only:
            package_skin(args.output)
            print(f"Packaged: {args.output}")
    except (SkinError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
