#!/usr/bin/env python3
# script.py
import os
import re
import sys
import html
from pathlib import Path
from collections import defaultdict

# -------------------------
# Config
# -------------------------
# Root to scan; override by passing a path as argv[1]
DEFAULT_SRC_ROOT = Path(__file__).resolve().parent.parent / "frontend" / "src"
# Output file
OUTPUT_XML = Path(__file__).resolve().parent / "diagram.drawio"

# Layout
COLS = 3                  # number of file columns
FILE_W, FILE_H = 180, 60  # parallelogram size
CELL_W, CELL_H = 180, 40  # var/func cell size
X_GAP, Y_GAP = 280, 220   # gaps between file boxes in grid
STACK_VGAP = 66           # vertical spacing between stacked var/func cells
# Where variables/functions stack relative to the file box (offsets)
VARS_OFFSET = (0, 100)    # left/below the file box
FUNCS_OFFSET = (220, 0)   # right of the file box

# -------------------------
# Unique ID factory
# -------------------------
_id_counters = defaultdict(int)

def _sanitize(s: str) -> str:
    return re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')

def next_id(prefix: str) -> str:
    _id_counters[prefix] += 1
    return f"{prefix}_{_id_counters[prefix]}"

# -------------------------
# Parsing helpers
# -------------------------
RE_IMPORT = re.compile(r'^\s*import\s+(?:[^"\']+?\s+from\s+)?["\'](.+?)["\']', re.M)
RE_FUNC_DECL = re.compile(r'^\s*export\s+function\s+([A-Za-z0-9_$]+)\s*\(|^\s*function\s+([A-Za-z0-9_$]+)\s*\(', re.M)
RE_FUNC_EXPR = re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*\(.*?\)\s*=>', re.M)
RE_VAR = re.compile(r'^\s*(?:export\s+)?(const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(.+?);?\s*$', re.M)

# very lightweight "top-level-ish" filter: ignores lines starting with whitespace + closing braces
def rough_top_level(lines):
    # Track simple brace depth to (very roughly) avoid inner function blocks.
    depth = 0
    for ln in lines.splitlines():
        open_count = ln.count('{')
        close_count = ln.count('}')
        # decide top-level by previous depth
        yield ln, depth == 0
        depth += open_count - close_count

def infer_type(init_expr: str) -> str:
    s = init_expr.strip()
    # Strip trailing comments
    s = re.sub(r'//.*$', '', s).strip()
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S).strip()

    # Literals
    if re.match(r'^[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$', s):
        return "number"
    if re.match(r"""^(['"]).*\1$""", s):
        return "string"
    if s in ("true", "false"):
        return "boolean"
    if s.startswith('['):
        return "array"
    if s.startswith('{'):
        return "object"
    # new Something(...)
    m = re.match(r'^new\s+([A-Za-z0-9_$\.]+)\s*\(', s)
    if m:
        return m.group(1)
    # Qualified call like Math.hypot(...), THREE.Matrix3(...), Some.ns(...)
    m = re.match(r'^([A-Za-z0-9_$\.]+)\s*\(', s)
    if m:
        return f"{m.group(1)}"
    # reference / identifier / member
    m = re.match(r'^([A-Za-z0-9_$\.]+)(?:\W|$)', s)
    if m:
        return m.group(1)
    return "unknown"

def parse_js(file_path: Path):
    text = file_path.read_text(encoding="utf-8", errors="ignore")

    # imports
    imports = RE_IMPORT.findall(text)

    # functions (declarations)
    fn_names = []
    for m in RE_FUNC_DECL.finditer(text):
        name = m.group(1) or m.group(2)
        if name:
            fn_names.append(name)
    # arrow function assignments
    for m in RE_FUNC_EXPR.finditer(text):
        name = m.group(1)
        if name:
            fn_names.append(name)

    # variables/consts (roughly top-level only)
    top_vars = {}
    for ln, is_top in rough_top_level(text):
        if not is_top:
            continue
        m = RE_VAR.match(ln)
        if m:
            kind, name, init = m.group(1), m.group(2), m.group(3)
            top_vars[name] = infer_type(init)

    return {
        "imports": imports,
        "functions": fn_names,
        "vars": top_vars
    }

# -------------------------
# Draw.io cell builders
# -------------------------
def build_file_box(rel_path, label, x, y, w=FILE_W, h=FILE_H):
    prefix = f"file_{_sanitize(rel_path)}"
    cell_id = next_id(prefix)
    xml = f"""
    <mxCell id="{cell_id}" value="{html.escape(label)}" style="shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;fixedSize=1;" vertex="1" parent="1">
      <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />
    </mxCell>
    """
    return cell_id, xml

def build_function_cells(function_names, rel_path, x, y, w=CELL_W, h=CELL_H, vgap=STACK_VGAP):
    cells = []
    id_map = {}  # name -> id
    base = f"fn_{_sanitize(rel_path)}"
    for i, fn in enumerate(function_names):
        cell_id = next_id(base)
        id_map[fn] = cell_id
        value = f"{fn}()"
        xml = f"""
        <mxCell id="{cell_id}" value="{html.escape(value)}" style="shape=step;perimeter=stepPerimeter;whiteSpace=wrap;html=1;fixedSize=1;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y + i*vgap}" width="{w}" height="{h}" as="geometry" />
        </mxCell>
        """
        cells.append(xml)
    return id_map, cells

def build_var_cells(vars_dict, rel_path, x, y, w=CELL_W, h=CELL_H, vgap=STACK_VGAP):
    cells = []
    id_map = {}  # var -> [ids]
    base = f"var_{_sanitize(rel_path)}"
    for i, (var_name, var_type) in enumerate(vars_dict.items()):
        cell_id = next_id(f"{base}_{_sanitize(var_name)}")
        id_map.setdefault(var_name, []).append(cell_id)
        value = f"{var_name}:\n{var_type}"
        xml = f"""
        <mxCell id="{cell_id}" value="{html.escape(value)}" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y + i*vgap}" width="{w}" height="{h}" as="geometry" />
        </mxCell>
        """
        cells.append(xml)
    return id_map, cells

def build_edge(source_id, target_id, points=None, curved=False):
    eid = next_id("edge")
    pts_xml = ""
    if points:
        pts = "".join(f'<mxPoint x="{px}" y="{py}" />' for px, py in points)
        pts_xml = f'<Array as="points">{pts}</Array>'
    style = "endArrow=classic;html=1;rounded=0;"
    if curved:
        style = "curved=1;" + style
    return f"""
    <mxCell id="{eid}" style="{style}" edge="1" parent="1" source="{source_id}" target="{target_id}">
      <mxGeometry width="50" height="50" relative="1" as="geometry">
        {pts_xml}
      </mxGeometry>
    </mxCell>
    """

# -------------------------
# Main: scan, parse, layout, emit
# -------------------------
def main():
    src_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SRC_ROOT.resolve()
    if not src_root.exists():
        print(f"[!] Source root not found: {src_root}")
        sys.exit(1)

    js_exts = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}  # include TS if present (we still regex)
    files = sorted([p for p in src_root.rglob("*") if p.is_file() and p.suffix in js_exts])

    files_data = {}
    for p in files:
        try:
            files_data[p] = parse_js(p)
        except Exception as e:
            print(f"[warn] Failed to parse {p}: {e}")

    # Layout grid positions for file boxes
    file_positions = {}  # path -> (x, y)
    row = col = 0
    for i, p in enumerate(files):
        x = col * X_GAP
        y = row * Y_GAP
        file_positions[p] = (x, y)
        col += 1
        if col >= COLS:
            col = 0
            row += 1

    # Build XML
    xml_cells = []
    file_box_ids = {}   # path -> file_id
    var_ids = {}        # path -> {var: [ids]}
    fn_ids = {}         # path -> {fn: id}

    # File boxes + stacks
    for p in files:
        rel = p.relative_to(src_root)
        x, y = file_positions[p]
        fid, fxml = build_file_box(str(rel), str(rel), x, y, FILE_W, FILE_H)
        file_box_ids[p] = fid
        xml_cells.append(fxml)

        data = files_data.get(p, {"vars": {}, "functions": [], "imports": []})
        # Vars (left/below)
        vx = x + VARS_OFFSET[0]
        vy = y + VARS_OFFSET[1]
        vmap, vcells = build_var_cells(data.get("vars", {}), str(rel), vx, vy, CELL_W, CELL_H, STACK_VGAP)
        var_ids[p] = vmap
        xml_cells.extend(vcells)

        # Functions (right)
        fx = x + FUNCS_OFFSET[0]
        fy = y + FUNCS_OFFSET[1]
        fmap, fcells = build_function_cells(data.get("functions", []), str(rel), fx, fy, CELL_W, CELL_H, STACK_VGAP)
        fn_ids[p] = fmap
        xml_cells.extend(fcells)

    # Import edges between file boxes
    # Try to resolve import specifiers to files in the set; simple heuristic:
    # - absolute-like starting with "." resolve relative to importing file
    # - otherwise, skip (external deps)
    edges = []
    import_map = {}  # for optional dedup if desired

    # Build a map from module key -> path to try resolve quickly
    # Key candidates: relative path without extension, with extension
    path_key_map = {}
    for p in files:
        rel = p.relative_to(src_root)
        noext = str(rel.with_suffix(""))
        path_key_map[noext] = p
        path_key_map[str(rel)] = p

    for p in files:
        data = files_data.get(p, {})
        for spec in data.get("imports", []):
            tgt_path = None
            if spec.startswith("."):
                # relative
                base = (p.parent / spec).resolve()
                # Try exact file or with common JS/TS extensions or default index
                candidates = [
                    base,
                    base.with_suffix(".js"),
                    base.with_suffix(".mjs"),
                    base.with_suffix(".cjs"),
                    base.with_suffix(".jsx"),
                    base.with_suffix(".ts"),
                    base.with_suffix(".tsx"),
                    base / "index.js",
                    base / "index.ts",
                    base / "index.jsx",
                    base / "index.tsx",
                ]
                for c in candidates:
                    try:
                        relc = c.resolve().relative_to(src_root)
                    except Exception:
                        continue
                    # if we actually scanned that file
                    if c in files:
                        tgt_path = c
                        break
                    # fallback: if a key match exists
                    key_noext = str(relc.with_suffix(""))
                    if key_noext in path_key_map:
                        tgt_path = path_key_map[key_noext]
                        break
            else:
                # external module (skip)
                pass

            if tgt_path and tgt_path in file_box_ids:
                src_id = file_box_ids[p]
                dst_id = file_box_ids[tgt_path]
                # Build an edge (curved for readability)
                edges.append(build_edge(src_id, dst_id, curved=True))

    xml_cells.extend(edges)

    # Wrap in draw.io doc
    doc = f"""<mxfile host="Electron" agent="Generated by script.py" version="28.1.2">
  <diagram name="Page-1" id="AUTO-GEN">
    <mxGraphModel dx="1600" dy="1200" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
{"".join(xml_cells)}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""
    OUTPUT_XML.write_text(doc, encoding="utf-8")
    print(f"[ok] Wrote {OUTPUT_XML} (files: {len(files)})")

if __name__ == "__main__":
    main()