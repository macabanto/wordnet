#!/usr/bin/env python3
# force_reflow.py — force-directed layout for an existing draw.io diagram

import sys, math, random
from pathlib import Path
import xml.etree.ElementTree as ET

# ---- knobs (tweak to taste) -----------------------------------------
ITERATIONS     = 1200      # simulation steps
DT             = 0.02      # timestep
DAMPING        = 0.85      # velocity damping per step
CENTER_PULL    = 0.002     # weak gravity toward the center
K_REPULSE      = 12000.0   # node–node repulsion strength
K_SPRING       = 0.02      # edge spring stiffness
EDGE_BASE_LEN  = 220.0     # preferred spring length baseline
EDGE_EXTRA_PAD = 0.6       # extra length factor by node sizes
COLLISION_PUSH = 0.5       # min push when rectangles overlap
BORDER_MARGIN  = 40.0      # keep everything inside a loose frame
SEED           = 42

# which vertex cells count as nodes
def is_file(cell):   return cell.get('vertex') == '1' and 'shape=parallelogram' in (cell.get('style') or '')
def is_func(cell):   return cell.get('vertex') == '1' and 'shape=step'          in (cell.get('style') or '')
def is_var(cell):    return cell.get('vertex') == '1' and cell.get('style','').startswith('rounded=0')

def is_edge(cell):   return cell.get('edge') == '1'

def geom(cell):
    return cell.find('./mxGeometry')

def get_rect(cell):
    g = geom(cell)
    x = float(g.get('x') or 0.0)
    y = float(g.get('y') or 0.0)
    w = float(g.get('width') or 0.0)
    h = float(g.get('height') or 0.0)
    return x, y, w, h

def set_xy(cell, x, y):
    g = geom(cell)
    g.set('x', str(x))
    g.set('y', str(y))

# ---- core ------------------------------------------------------------
def run(input_path: Path, output_path: Path):
    random.seed(SEED)
    tree = ET.parse(str(input_path))
    root = tree.getroot()
    cells_parent = root.find('.//root')
    if cells_parent is None:
        print('[!] could not find <root>')
        sys.exit(1)
    all_cells = list(cells_parent.findall('./mxCell'))
    nodes = {}
    edges = []

    # collect nodes (files + vars + funcs)
    for c in all_cells:
        if is_file(c) or is_func(c) or is_var(c):
            x, y, w, h = get_rect(c)
            # treat mxGeometry x,y as top-left; use center for forces
            cx, cy = x + w/2.0, y + h/2.0
            nodes[c.get('id')] = {
                'cell': c,
                'w': w, 'h': h,
                'x': cx, 'y': cy,
                'vx': 0.0, 'vy': 0.0,
                # mass could vary by type; keep 1.0 for simplicity
                'm': 1.0
            }

    if not nodes:
        print('[!] no nodes found (need parallelograms/steps/boxes)')
        sys.exit(1)

    # collect edges where both endpoints are our nodes
    for c in all_cells:
        if not is_edge(c): continue
        s = c.get('source'); t = c.get('target')
        if s in nodes and t in nodes:
            edges.append((s, t))

    # compute initial frame / center
    xs = [v['x'] for v in nodes.values()]
    ys = [v['y'] for v in nodes.values()]
    cx0 = sum(xs)/len(xs)
    cy0 = sum(ys)/len(ys)

    # helpers
    def spring_len(a, b):
        # base length plus a bit for sizes
        return EDGE_BASE_LEN + EDGE_EXTRA_PAD * 0.5 * (max(a['w'], a['h']) + max(b['w'], b['h']))

    # simulation
    for step in range(ITERATIONS):
        # repulsion (all-pairs; O(n^2) is fine for modest diagrams)
        ids = list(nodes.keys())
        for i in range(len(ids)):
            A = nodes[ids[i]]
            for j in range(i+1, len(ids)):
                B = nodes[ids[j]]
                dx = A['x'] - B['x']
                dy = A['y'] - B['y']
                d2 = dx*dx + dy*dy
                if d2 < 1e-6:
                    # jitter to break symmetry
                    dx = (random.random()-0.5)*1e-3
                    dy = (random.random()-0.5)*1e-3
                    d2 = dx*dx + dy*dy
                d = math.sqrt(d2)
                # Coulomb-like repulsion
                f = K_REPULSE / d2
                fx = f * dx / d
                fy = f * dy / d
                A['vx'] += fx * DT / A['m']
                A['vy'] += fy * DT / A['m']
                B['vx'] -= fx * DT / B['m']
                B['vy'] -= fy * DT / B['m']

        # springs (edges)
        for s, t in edges:
            A = nodes[s]; B = nodes[t]
            dx = B['x'] - A['x']
            dy = B['y'] - A['y']
            d = math.hypot(dx, dy) or 1e-6
            L = spring_len(A, B)
            # Hooke's law toward preferred length
            f = K_SPRING * (d - L)
            fx = f * dx / d
            fy = f * dy / d
            # apply opposite forces
            A['vx'] +=  fx * DT / A['m']
            A['vy'] +=  fy * DT / A['m']
            B['vx'] -=  fx * DT / B['m']
            B['vy'] -=  fy * DT / B['m']

        # soft pull to center
        for N in nodes.values():
            N['vx'] += -CENTER_PULL * (N['x'] - cx0)
            N['vy'] += -CENTER_PULL * (N['y'] - cy0)

        # integrate + damping
        for N in nodes.values():
            N['x'] += N['vx'] * DT
            N['y'] += N['vy'] * DT
            N['vx'] *= DAMPING
            N['vy'] *= DAMPING

        # rectangular collision / overlap push (cheap)
        idlist = list(nodes.keys())
        for i in range(len(idlist)):
            A = nodes[idlist[i]]
            for j in range(i+1, len(idlist)):
                B = nodes[idlist[j]]
                # axis-aligned boxes with small padding
                ax0, ay0 = A['x'] - A['w']/2, A['y'] - A['h']/2
                ax1, ay1 = A['x'] + A['w']/2, A['y'] + A['h']/2
                bx0, by0 = B['x'] - B['w']/2, B['y'] - B['h']/2
                bx1, by1 = B['x'] + B['w']/2, B['y'] + B['h']/2

                pad = 14.0  # visual margin between boxes
                if not (ax1 + pad < bx0 or bx1 + pad < ax0 or ay1 + pad < by0 or by1 + pad < ay0):
                    # overlap: push along the smaller penetration axis
                    dx = (ax1 - bx0) if A['x'] < B['x'] else (bx1 - ax0)
                    dy = (ay1 - by0) if A['y'] < B['y'] else (by1 - ay0)
                    if abs(dx) < abs(dy):
                        push = max(abs(dx), COLLISION_PUSH)
                        if A['x'] < B['x']:
                            A['x'] -= push/2; B['x'] += push/2
                        else:
                            A['x'] += push/2; B['x'] -= push/2
                    else:
                        push = max(abs(dy), COLLISION_PUSH)
                        if A['y'] < B['y']:
                            A['y'] -= push/2; B['y'] += push/2
                        else:
                            A['y'] += push/2; B['y'] -= push/2

        # gentle border box to keep things in view
        # compute bounds from current nodes
        xs = [v['x'] for v in nodes.values()]
        ys = [v['y'] for v in nodes.values()]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        w = (maxx - minx) + 2*BORDER_MARGIN
        h = (maxy - miny) + 2*BORDER_MARGIN
        cx = (maxx + minx)/2
        cy = (maxy + miny)/2
        for N in nodes.values():
            # light rubber band to a loose frame
            if N['x'] < cx - w/2:  N['x'] += (cx - w/2 - N['x']) * 0.1
            if N['x'] > cx + w/2:  N['x'] -= (N['x'] - (cx + w/2)) * 0.1
            if N['y'] < cy - h/2:  N['y'] += (cy - h/2 - N['y']) * 0.1
            if N['y'] > cy + h/2:  N['y'] -= (N['y'] - (cy + h/2)) * 0.1

    # write back top-left coords
    for N in nodes.values():
        x = N['x'] - N['w']/2
        y = N['y'] - N['h']/2
        set_xy(N['cell'], x, y)

    tree.write(output_path, encoding='utf-8', xml_declaration=False)
    print(f"[ok] Force reflow → {output_path} (nodes: {len(nodes)}, edges: {len(edges)})")

# ---- cli -------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 force_reflow.py <input.drawio> [output.drawio]")
        sys.exit(1)
    inp = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else inp
    run(inp, out)