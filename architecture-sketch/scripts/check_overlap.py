#!/usr/bin/env python3
"""
Checks a .drawio file for two kinds of layout problems:

1. Overlap: vertex cells whose bounding boxes overlap unintentionally
   (a system boundary containing its own components is fine and ignored;
   any other overlap is a bug).
2. Edge-crossing: an edge (call/connection) whose path — following its
   explicit waypoints if it has any, otherwise approximated as a straight
   line between source and target centers — passes through the bounding
   box of some *other* component (not its own source or target). System
   boundary cells (id starting with "sys", per this skill's id convention)
   are never treated as crossing-obstacles, since edges are expected to
   cross a boundary's outline when a call goes in or out of that system.

   NOTE: without explicit waypoints, this is only an approximation —
   draw.io's real auto-router does NOT draw a straight line between two
   components, so a "clean" straight-line check can still render with the
   actual connector cutting through a neighboring shape. Any edge whose
   source and target don't share the same x or y should get explicit
   waypoints (see SKILL.md) rather than relying on this fallback.

Usage: python3 check_overlap.py path/to/file.drawio

Exit code 0 = no problems, 1 = problems found (or file failed to parse).
"""
import sys
import xml.etree.ElementTree as ET


def get_boxes(tree):
    boxes = {}
    for cell in tree.iter("mxCell"):
        if cell.get("vertex") != "1":
            continue
        geom = cell.find("mxGeometry")
        if geom is None:
            continue
        try:
            x = float(geom.get("x", 0))
            y = float(geom.get("y", 0))
            w = float(geom.get("width", 0))
            h = float(geom.get("height", 0))
        except (TypeError, ValueError):
            continue
        cid = cell.get("id")
        boxes[cid] = {
            "id": cid,
            "label": cell.get("value") or "",
            "x": x, "y": y, "w": w, "h": h,
        }
    return boxes


def get_edges(tree):
    edges = []
    for cell in tree.iter("mxCell"):
        if cell.get("edge") != "1":
            continue
        src, tgt = cell.get("source"), cell.get("target")
        geom = cell.find("mxGeometry")
        points = []
        source_point = target_point = None
        if geom is not None:
            points_container = geom.find("Array[@as='points']")
            if points_container is not None:
                for pt in points_container.findall("mxPoint"):
                    try:
                        points.append((float(pt.get("x")), float(pt.get("y"))))
                    except (TypeError, ValueError):
                        pass
            for pt in geom.findall("mxPoint"):
                try:
                    xy = (float(pt.get("x")), float(pt.get("y")))
                except (TypeError, ValueError):
                    continue
                if pt.get("as") == "sourcePoint":
                    source_point = xy
                elif pt.get("as") == "targetPoint":
                    target_point = xy
        if not src and source_point is None:
            continue
        if not tgt and target_point is None:
            continue
        edges.append({
            "id": cell.get("id"),
            "label": cell.get("value") or "",
            "source": src, "target": tgt,
            "source_point": source_point, "target_point": target_point,
            "waypoints": points,
        })
    return edges


def overlaps(a, b):
    ax1, ay1, ax2, ay2 = a["x"], a["y"], a["x"] + a["w"], a["y"] + a["h"]
    bx1, by1, bx2, by2 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def contains(a, b):
    """True if box a fully contains box b."""
    return (a["x"] <= b["x"] and a["y"] <= b["y"]
            and a["x"] + a["w"] >= b["x"] + b["w"]
            and a["y"] + a["h"] >= b["y"] + b["h"])


def center(box):
    return (box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)


def _orientation(p, q, r):
    val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
    if abs(val) < 1e-9:
        return 0
    return 1 if val > 0 else 2


def _on_segment(p, q, r):
    return (min(p[0], r[0]) <= q[0] <= max(p[0], r[0])
            and min(p[1], r[1]) <= q[1] <= max(p[1], r[1]))


def seg_seg_intersect(p1, p2, p3, p4):
    o1, o2 = _orientation(p1, p2, p3), _orientation(p1, p2, p4)
    o3, o4 = _orientation(p3, p4, p1), _orientation(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(p1, p3, p2):
        return True
    if o2 == 0 and _on_segment(p1, p4, p2):
        return True
    if o3 == 0 and _on_segment(p3, p1, p4):
        return True
    if o4 == 0 and _on_segment(p3, p2, p4):
        return True
    return False


def point_in_rect(p, rect):
    x1, y1, x2, y2 = rect
    return x1 <= p[0] <= x2 and y1 <= p[1] <= y2


def seg_crosses_box(p1, p2, box):
    x1, y1, x2, y2 = box["x"], box["y"], box["x"] + box["w"], box["y"] + box["h"]
    if max(p1[0], p2[0]) < x1 or min(p1[0], p2[0]) > x2:
        if not (min(p1[1], p2[1]) <= y1 <= max(p1[1], p2[1])
                or min(p1[1], p2[1]) <= y2 <= max(p1[1], p2[1])):
            pass
    rect_edges = [
        ((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)),
        ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1)),
    ]
    for a, b in rect_edges:
        if seg_seg_intersect(p1, p2, a, b):
            return True
    if point_in_rect(p1, (x1, y1, x2, y2)) and point_in_rect(p2, (x1, y1, x2, y2)):
        return True
    return False


def check_overlaps(boxes):
    problems = []
    items = list(boxes.values())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if not overlaps(a, b):
                continue
            if contains(a, b) or contains(b, a):
                continue  # intentional: boundary containing its children
            problems.append(("overlap", a, b))
    return problems


def check_edge_crossings(boxes, edges):
    problems = []
    for edge in edges:
        src_box, tgt_box = boxes.get(edge["source"]), boxes.get(edge["target"])
        if edge["source"] and not src_box:
            continue
        if edge["target"] and not tgt_box:
            continue
        p_start = center(src_box) if src_box else edge["source_point"]
        p_end = center(tgt_box) if tgt_box else edge["target_point"]
        if p_start is None or p_end is None:
            continue
        excluded_ids = {b for b in (edge["source"], edge["target"]) if b}
        path = [p_start] + edge["waypoints"] + [p_end]
        for k in range(len(path) - 1):
            p1, p2 = path[k], path[k + 1]
            for cid, box in boxes.items():
                if cid in excluded_ids:
                    continue
                if cid.lower().startswith("sys"):
                    continue  # system boundaries: crossing the outline is expected
                if seg_crosses_box(p1, p2, box):
                    problems.append(("crossing", edge, box))
    return problems


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 check_overlap.py path/to/file.drawio")
        sys.exit(2)

    path = sys.argv[1]
    tree = ET.parse(path)
    boxes = get_boxes(tree)
    edges = get_edges(tree)

    overlap_problems = check_overlaps(boxes)
    crossing_problems = check_edge_crossings(boxes, edges)

    if not overlap_problems and not crossing_problems:
        print(f"OK: no unintentional overlaps or edge crossings "
              f"({len(boxes)} components, {len(edges)} edges).")
        sys.exit(0)

    if overlap_problems:
        print(f"FOUND {len(overlap_problems)} overlapping pair(s):")
        for _, a, b in overlap_problems:
            print(f"  - '{a['label']}' ({a['id']}) overlaps '{b['label']}' ({b['id']})")

    if crossing_problems:
        print(f"FOUND {len(crossing_problems)} edge-crossing problem(s):")
        for _, edge, box in crossing_problems:
            label = edge["label"] or edge["id"]
            print(f"  - edge '{label}' ({edge['source']} -> {edge['target']}) "
                  f"crosses through '{box['label']}' ({box['id']})")

    sys.exit(1)


if __name__ == "__main__":
    main()

