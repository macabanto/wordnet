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
DEFAULT_SRC_ROOT = Path(__file__).resolve().parent.parent / "frontend" / "src"
OUTPUT_XML = Path(__file__).resolve().parent / "diagram.drawio"

# Layout
COLS = 3
FILE_W, FILE_H = 180, 60
CELL_W, CELL_H = 180, 40
X_GAP, Y_GAP = 280, 220
STACK_VGAP = 66
VARS_OFFSET = (0, 100)
FUNCS_OFFSET = (220, 0)

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
# previous regexes (kept)
RE_FUNC_DECL = re.compile(r'^\s*export\s+function\s+([A-Za-z0-9_$]+)\s*\(|^\s*function\s+([A-Za-z0-9_$]+)\s*\(', re.M)
RE_FUNC_EXPR  = re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*\(.*?\)\s*=>', re.M)
RE_VAR        = re.compile(r'^\s*(?:export\s+)?(const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(.+?);?\s*$', re.M)

# imports (structured)
RE_IMPORT_FULL = re.compile(
    r'^\s*import\s+(?P<clause>.+?)\s+from\s+[\'"](?P<spec>.+?)[\'"]\s*;?\s*$',
    re.M
)
RE_IMPORT_SIDE = re.compile(r'^\s*import\s+[\'"](?P<spec>.+?)[\'"]\s*;?\s*$', re.M)

# exports
RE_EXPORT_FUNC    = re.compile(r'^\s*export\s+function\s+([A-Za-z_$][\w$]*)\s*\(', re.M)
RE_EXPORT_VAR     = re.compile(r'^\s*export\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=', re.M)
RE_EXPORT_NAMED   = re.compile(r'^\s*export\s*{\s*([^}]+)\s*}\s*;?\s*$', re.M)
RE_EXPORT_DEFAULT = re.compile(r'^\s*export\s+default\s+([A-Za-z_$][\w$]*)\b', re.M)

def rough_top_level(lines: str):
    depth = 0
    for ln in lines.splitlines():
        open_count = ln.count('{')
        close_count = ln.count('}')
        yield ln, depth == 0
        depth += open_count - close_count

def infer_type(init_expr: str) -> str:
    s = init_expr.strip()
    s = re.sub(r'//.*$', '', s).strip()
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S).strip()

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
    m = re.match(r'^new\s+([A-Za-z0-9_$\.]+)\s*\(', s)
    if m: return m.group(1)
    m = re.match(r'^([A-Za-z0-9_$\.]+)\s*\(', s)
    if m: return f"{m.group(1)}"
    m = re.match(r'^([A-Za-z0-9_$\.]+)(?:\W|$)', s)
    if m: return m.group(1)
    return "unknown"

# ---------- NEW: structured imports / exports / usage ----------
def parse_imports(text: str):
    """
    Returns list of dicts:
      {"kind": "default"|"named"|"ns",
       "local": <localName or None>,
       "exported": <exportedName or None>,   # for named/default
       "members": [<exportedName>...] or None, # for named only (if multiple)
       "spec": "./path"}
    """
    imports = []

    # side-effect imports -> we skip for edges (no bindings)
    for m in RE_IMPORT_SIDE.finditer(text):
        # keep if you want file->file edges for side effects:
        imports.append({"kind": "side", "local": None, "exported": None, "members": None, "spec": m.group("spec")})

    for m in RE_IMPORT_FULL.finditer(text):
        clause = m.group("clause").strip()
        spec   = m.group("spec")

        # namespace: import * as ns from '...'
        m_ns = re.match(r'^\*\s+as\s+([A-Za-z_$][\w$]*)$', clause)
        if m_ns:
            imports.append({"kind": "ns", "local": m_ns.group(1), "exported": None, "members": None, "spec": spec})
            continue

        # default + maybe named: import foo, { a as b, c } from '...'
        m_def_named = re.match(r'^([A-Za-z_$][\w$]*)\s*,\s*{\s*([^}]+)\s*}$', clause)
        if m_def_named:
            default_local = m_def_named.group(1)
            named_block   = m_def_named.group(2)
            imports.append({"kind": "default", "local": default_local, "exported": "default", "members": None, "spec": spec})
            named = []
            for part in named_block.split(','):
                part = part.strip()
                if not part: continue
                if ' as ' in part:
                    exp, loc = [x.strip() for x in part.split(' as ', 1)]
                else:
                    exp, loc = part, part
                imports.append({"kind": "named", "local": loc, "exported": exp, "members": None, "spec": spec})
            continue

        # named only: import { a as b, c } from '...'
        m_named = re.match(r'^{\s*([^}]+)\s*}$', clause)
        if m_named:
            named_block = m_named.group(1)
            for part in named_block.split(','):
                part = part.strip()
                if not part: continue
                if ' as ' in part:
                    exp, loc = [x.strip() for x in part.split(' as ', 1)]
                else:
                    exp, loc = part, part
                imports.append({"kind": "named", "local": loc, "exported": exp, "members": None, "spec": spec})
            continue

        # default only: import Foo from '...'
        m_def = re.match(r'^([A-Za-z_$][\w$]*)$', clause)
        if m_def:
            imports.append({"kind": "default", "local": m_def.group(1), "exported": "default", "members": None, "spec": spec})
            continue

        # fallback: leave it as a raw entry
        imports.append({"kind": "unknown", "local": None, "exported": None, "members": None, "spec": spec})

    return imports

def parse_exports(text: str):
    """
    Returns a map of exported name -> local symbol name (when we can tell).
    For default exports we map 'default' -> localName when it’s `export default localName`.
    """
    exp = {}

    for m in RE_EXPORT_FUNC.finditer(text):
        name = m.group(1)
        exp[name] = name

    for m in RE_EXPORT_VAR.finditer(text):
        name = m.group(1)
        exp[name] = name

    for m in RE_EXPORT_NAMED.finditer(text):
        block = m.group(1)
        for part in block.split(','):
            part = part.strip()
            if not part: continue
            if ' as ' in part:
                local, exported = [x.strip() for x in part.split(' as ', 1)]
            else:
                local = exported = part
            exp[exported] = local

    # default export bound to an identifier
    for m in RE_EXPORT_DEFAULT.finditer(text):
        local = m.group(1)
        exp["default"] = local

    return exp

def build_usage_text(text: str):
    # strip import and export lines to reduce false positives in usage scans
    t = RE_IMPORT_FULL.sub('', text)
    t = RE_IMPORT_SIDE.sub('', t)
    t = RE_EXPORT_NAMED.sub('', t)
    t = RE_EXPORT_DEFAULT.sub('', t)
    # leave function/var exports — they still show real usage if referenced below
    return t

# -------------------------
# Parse a single JS/TS file
# -------------------------
def parse_js(file_path: Path):
    text = file_path.read_text(encoding="utf-8", errors="ignore")

    imports = parse_imports(text)
    exports = parse_exports(text)
    usage_text = build_usage_text(text)

    # functions
    fn_names = []
    for m in RE_FUNC_DECL.finditer(text):
        name = m.group(1) or m.group(2)
        if name: fn_names.append(name)
    for m in RE_FUNC_EXPR.finditer(text):
        name = m.group(1)
        if name: fn_names.append(name)

    # top-level vars
    top_vars = {}
    for ln, is_top in rough_top_level(text):
        if not is_top: continue
        m = RE_VAR.match(ln)
        if m:
            _, name, init = m.group(1), m.group(2), m.group(3)
            top_vars[name] = infer_type(init)

    return {
        "imports": imports,
        "exports": exports,       # exportedName -> localName
        "usage_text": usage_text, # code minus import/export boilerplate
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
    id_map = {}
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
    id_map = {}
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
# Main
# -------------------------
def main():
    src_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SRC_ROOT.resolve()
    if not src_root.exists():
        print(f"[!] Source root not found: {src_root}")
        sys.exit(1)

    js_exts = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}
    files = sorted([p for p in src_root.rglob("*") if p.is_file() and p.suffix in js_exts])

    files_data = {}
    for p in files:
        try:
            files_data[p] = parse_js(p)
        except Exception as e:
            print(f"[warn] Failed to parse {p}: {e}")

    # positions
    file_positions = {}
    row = col = 0
    for p in files:
        x = col * X_GAP
        y = row * Y_GAP
        file_positions[p] = (x, y)
        col += 1
        if col >= COLS:
            col = 0
            row += 1

    # build cells
    xml_cells = []
    file_box_ids = {}
    var_ids = {}
    fn_ids = {}

    for p in files:
        rel = p.relative_to(src_root)
        x, y = file_positions[p]
        fid, fxml = build_file_box(str(rel), str(rel), x, y, FILE_W, FILE_H)
        file_box_ids[p] = fid
        xml_cells.append(fxml)

        data = files_data.get(p, {"vars": {}, "functions": [], "imports": [], "exports": {}, "usage_text": ""})

        # vars
        vx, vy = x + VARS_OFFSET[0], y + VARS_OFFSET[1]
        vmap, vcells = build_var_cells(data.get("vars", {}), str(rel), vx, vy, CELL_W, CELL_H, STACK_VGAP)
        var_ids[p] = vmap
        xml_cells.extend(vcells)

        # functions
        fx, fy = x + FUNCS_OFFSET[0], y + FUNCS_OFFSET[1]
        fmap, fcells = build_function_cells(data.get("functions", []), str(rel), fx, fy, CELL_W, CELL_H, STACK_VGAP)
        fn_ids[p] = fmap
        xml_cells.extend(fcells)

    # path keys for quick resolution
    path_key_map = {}
    for p in files:
        rel = p.relative_to(src_root)
        noext = str(rel.with_suffix(""))
        path_key_map[noext] = p
        path_key_map[str(rel)] = p

    # helper to resolve import spec -> target file
    def resolve_spec(importing_file: Path, spec: str):
        if spec.startswith("."):
            base = (importing_file.parent / spec).resolve()
            candidates = [
                base,
                base.with_suffix(".js"), base.with_suffix(".mjs"), base.with_suffix(".cjs"),
                base.with_suffix(".jsx"), base.with_suffix(".ts"), base.with_suffix(".tsx"),
                base / "index.js", base / "index.ts", base / "index.jsx", base / "index.tsx",
            ]
            for c in candidates:
                if c in files:
                    return c
                try:
                    relc = c.resolve().relative_to(src_root)
                    key_noext = str(relc.with_suffix(""))
                    if key_noext in path_key_map:
                        return path_key_map[key_noext]
                except Exception:
                    pass
        # external module: ignore
        return None

    # Export map cache: path -> {exported -> local}
    export_map = {p: files_data[p].get("exports", {}) for p in files}

    # edge dedup
    seen_edges = set()
    edges = []

    # Build a quick lookup: for a given path and local symbol name, get its cell id (var or fn)
    def symbol_cell_id(path: Path, local_name: str):
        # function?
        fid = fn_ids.get(path, {}).get(local_name)
        if fid: return fid
        # var? (may be multiple duplicate cells if same var captured twice; we take first)
        vids = var_ids.get(path, {}).get(local_name)
        if vids: return vids[0]
        return None

    for p in files:
        pdata = files_data.get(p, {})
        usage = pdata.get("usage_text", "")
        for imp in pdata.get("imports", []):
            tgt_path = resolve_spec(p, imp.get("spec", ""))
            if not tgt_path or tgt_path not in file_box_ids:
                continue

            # Decide if the import is used in this file (cheap heuristic)
            kind = imp.get("kind")
            src_sym_id = None
            dst_sym_id = None

            if kind == "named":
                local = imp["local"]
                exported = imp["exported"]
                # used?
                if not re.search(rf'\b{re.escape(local)}\b', usage):
                    continue
                # source: exported symbol in target file -> resolve to local name there
                exp_local = export_map.get(tgt_path, {}).get(exported)
                if exp_local:
                    src_sym_id = symbol_cell_id(tgt_path, exp_local)
                # dest: local binding (var/func cell if we created one)
                dst_sym_id = symbol_cell_id(p, local)

            elif kind == "default":
                local = imp["local"]
                if not re.search(rf'\b{re.escape(local)}\b', usage):
                    continue
                exp_local = export_map.get(tgt_path, {}).get("default")
                if exp_local:
                    src_sym_id = symbol_cell_id(tgt_path, exp_local)
                dst_sym_id = symbol_cell_id(p, local)

            elif kind == "ns":
                ns = imp["local"]
                # Find ns.member usages; collect unique member names
                members = set(m.group(1) for m in re.finditer(rf'\b{re.escape(ns)}\.([A-Za-z_$][\w$]*)', usage))
                if not members:
                    # no specific member usage found — optionally connect file->file
                    src_id = file_box_ids[tgt_path]
                    dst_id = file_box_ids[p]
                    key = (src_id, dst_id)
                    if key not in seen_edges:
                        seen_edges.add(key)
                        edges.append(build_edge(src_id, dst_id, curved=True))
                    continue
                for member in members:
                    exp_local = export_map.get(tgt_path, {}).get(member)
                    src_sym_id = symbol_cell_id(tgt_path, exp_local) if exp_local else None
                    dst_sym_id = None  # namespace import doesn’t create a local symbol per member
                    # prefer symbol->file if we found the member, else file->file
                    src_id = src_sym_id or file_box_ids[tgt_path]
                    dst_id = file_box_ids[p]
                    key = (src_id, dst_id)
                    if key not in seen_edges:
                        seen_edges.add(key)
                        edges.append(build_edge(src_id, dst_id, curved=True))
                continue  # done with this import

            else:
                # side-effect / unknown: make a file->file edge
                src_id = file_box_ids[tgt_path]
                dst_id = file_box_ids[p]
                key = (src_id, dst_id)
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append(build_edge(src_id, dst_id, curved=True))
                continue

            # Fallbacks and emit
            src_id = src_sym_id or file_box_ids[tgt_path]
            dst_id = dst_sym_id or file_box_ids[p]
            key = (src_id, dst_id)
            if key not in seen_edges:
                seen_edges.add(key)
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