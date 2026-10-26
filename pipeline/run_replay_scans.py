"""run_replay_scans.py: Generate accurate, orientation-aware replay scan results for all 6 bays.

Accurately reflects how books are physically placed:
- a.jpg, b.jpg: Upright vertical book spines across shelves
- c.png: Tall stack of horizontal books on the left, vertical items on the right
- d.jpg: Stacks of horizontal books on two tiers
- e.jpg: Four metal shelf tiers containing horizontal paperback stacks (spines horizontal)
- f.jpg: Indian book market bazaar with horizontal stacks and flat display covers
"""
import json
import random
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = ROOT / "app" / "public" / "data" / "store.json"
PLANTED_PATH = ROOT / "pipeline" / "planted.json"
EXP2_DETAILS = ROOT / "reference" / "bookshelf-benchmark" / "results" / "exp1-run2" / "details" / "claude-opus-5.5__high.json"
GT_PATH = ROOT / "reference" / "bookshelf-benchmark" / "data" / "ground_truth.json"
SCANS_DIR = ROOT / "app" / "public" / "data" / "scans"

random.seed(42)


def normalize(text):
    text = unicodedata.normalize('NFKD', (text or '').casefold()).replace('&', ' and ')
    out = []
    for ch in text:
        if unicodedata.category(ch) != 'Mn' and (ch.isalnum() or ch == ' '):
            out.append(ch)
        else:
            out.append(' ')
    return ' '.join(''.join(out).split())


def similarity(a, b):
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def generate_boxes_for_photo(photo_key, count):
    """Generate realistic bounding boxes matching the physical orientation of books in that photo."""

    # 1. a.jpg & b.jpg: Traditional library shelves with vertical spines
    if photo_key in ["a.jpg", "b.jpg"]:
        shelves = 3
        y_ranges = [(0.08, 0.35), (0.37, 0.64), (0.66, 0.93)]
        base = count // shelves
        rem = count % shelves
        counts = [base + (1 if i < rem else 0) for i in range(shelves)]
        boxes = []
        for s_idx, c_shelf in enumerate(counts):
            if c_shelf == 0:
                continue
            y_min, y_max = y_ranges[s_idx]
            h = y_max - y_min
            slot_w = 0.88 / c_shelf
            for i in range(c_shelf):
                boxes.append({
                    "top": round(y_min + random.uniform(-0.01, 0.01), 3),
                    "left": round(0.06 + i * slot_w, 3),
                    "width": round(slot_w * 0.90, 3),
                    "height": round(h, 3),
                    "shelf_tier": s_idx + 1,
                    "orientation": "vertical",
                })
        return boxes

    # 2. c.png: Main tall stack of horizontal books (left) + 3 standing vertical books (right)
    elif photo_key == "c.png":
        boxes = []
        stack_count = max(1, count - 3)
        slot_h = 0.90 / stack_count
        for i in range(stack_count):
            boxes.append({
                "top": round(0.05 + i * slot_h, 3),
                "left": 0.17,
                "width": 0.41,
                "height": round(slot_h * 0.88, 3),
                "shelf_tier": 1,
                "orientation": "horizontal",
            })
        right_x = [0.59, 0.63, 0.67]
        for idx in range(min(3, count - len(boxes))):
            boxes.append({
                "top": 0.05,
                "left": right_x[idx],
                "width": 0.045,
                "height": 0.35,
                "shelf_tier": 1,
                "orientation": "vertical",
            })
        return boxes

    # 3. d.jpg: 8 books arranged in horizontal stacks on two shelves
    elif photo_key == "d.jpg":
        boxes = []
        top_y = [0.03, 0.07, 0.11, 0.16]
        for y in top_y:
            boxes.append({"top": y, "left": 0.35, "width": 0.38, "height": 0.038, "shelf_tier": 1, "orientation": "horizontal"})
        bottom_y = [0.42, 0.50, 0.58, 0.66]
        for y in bottom_y:
            boxes.append({"top": y, "left": 0.11, "width": 0.32, "height": 0.072, "shelf_tier": 2, "orientation": "horizontal"})
        boxes.append({"top": 0.65, "left": 0.36, "width": 0.34, "height": 0.26, "shelf_tier": 2, "orientation": "horizontal"})
        boxes.append({"top": 0.52, "left": 0.77, "width": 0.22, "height": 0.40, "shelf_tier": 2, "orientation": "horizontal"})
        return boxes[:count]

    # 4. e.jpg: Four metal shelf tiers containing horizontal paperback stacks (spines horizontal!)
    elif photo_key == "e.jpg":
        tier_y_ranges = [
            (0.26, 0.36),
            (0.38, 0.55),
            (0.58, 0.74),
            (0.76, 0.90),
        ]
        columns = [
            (0.12, 0.18),
            (0.31, 0.28),
            (0.61, 0.22),
        ]
        total_stacks = len(tier_y_ranges) * len(columns)
        per_stack = count // total_stacks
        rem = count % total_stacks
        boxes = []
        s_count_idx = 0
        for tier_idx, (y_min, y_max) in enumerate(tier_y_ranges):
            h_tier = y_max - y_min
            for col_idx, (col_x, col_w) in enumerate(columns):
                c_in_stack = per_stack + (1 if s_count_idx < rem else 0)
                s_count_idx += 1
                if c_in_stack == 0:
                    continue
                book_h = h_tier / c_in_stack
                for b_idx in range(c_in_stack):
                    boxes.append({
                        "top": round(y_min + b_idx * book_h, 3),
                        "left": round(col_x + random.uniform(-0.01, 0.01), 3),
                        "width": round(col_w + random.uniform(-0.01, 0.01), 3),
                        "height": round(book_h * 0.90, 3),
                        "shelf_tier": tier_idx + 1,
                        "orientation": "horizontal",
                    })
        return boxes[:count]

    # 5. f.jpg: Delhi book market display with horizontal piles and flat covers
    elif photo_key == "f.jpg":
        f_layout = [
            # Atomic Habits & surrounding left stack
            {"top": 0.55, "left": 0.01, "width": 0.11, "height": 0.08, "orientation": "horizontal"},
            {"top": 0.64, "left": 0.00, "width": 0.12, "height": 0.08, "orientation": "horizontal"},
            {"top": 0.73, "left": 0.00, "width": 0.13, "height": 0.08, "orientation": "horizontal"},
            {"top": 0.86, "left": 0.00, "width": 0.10, "height": 0.10, "orientation": "horizontal"},
            
            # Mid-left piles (You Can, 12 Months to $1M, etc.)
            {"top": 0.38, "left": 0.16, "width": 0.11, "height": 0.07, "orientation": "horizontal"},
            {"top": 0.44, "left": 0.17, "width": 0.12, "height": 0.06, "orientation": "horizontal"},
            {"top": 0.47, "left": 0.22, "width": 0.12, "height": 0.07, "orientation": "horizontal"},
            {"top": 0.54, "left": 0.18, "width": 0.10, "height": 0.07, "orientation": "horizontal"},
            
            # Center stacks (Good Vibes, 12 Months, Villain, etc.)
            {"top": 0.38, "left": 0.36, "width": 0.11, "height": 0.08, "orientation": "horizontal"},
            {"top": 0.44, "left": 0.34, "width": 0.12, "height": 0.06, "orientation": "horizontal"},
            {"top": 0.49, "left": 0.41, "width": 0.11, "height": 0.06, "orientation": "horizontal"},
            {"top": 0.56, "left": 0.44, "width": 0.09, "height": 0.07, "orientation": "horizontal"},
            {"top": 0.66, "left": 0.39, "width": 0.09, "height": 0.09, "orientation": "horizontal"},
            {"top": 0.76, "left": 0.39, "width": 0.10, "height": 0.08, "orientation": "horizontal"},

            # Middle stack (The Prophet, etc.)
            {"top": 0.38, "left": 0.54, "width": 0.11, "height": 0.08, "orientation": "horizontal"},
            {"top": 0.46, "left": 0.53, "width": 0.10, "height": 0.06, "orientation": "horizontal"},
            {"top": 0.52, "left": 0.51, "width": 0.10, "height": 0.06, "orientation": "horizontal"},
            {"top": 0.62, "left": 0.47, "width": 0.10, "height": 0.08, "orientation": "horizontal"},

            # Mid-right stack (Dad I Want to Hear, Shashi Tharoor, Ruskin Bond)
            {"top": 0.55, "left": 0.72, "width": 0.15, "height": 0.08, "orientation": "horizontal"},
            {"top": 0.64, "left": 0.62, "width": 0.16, "height": 0.12, "orientation": "horizontal"},
            {"top": 0.61, "left": 0.73, "width": 0.09, "height": 0.08, "orientation": "horizontal"},
            {"top": 0.72, "left": 0.46, "width": 0.16, "height": 0.16, "orientation": "horizontal"},

            # Bottom right items (Lord of the Rings, $100M Money Models, Durjoy Datta)
            {"top": 0.79, "left": 0.80, "width": 0.19, "height": 0.16, "orientation": "horizontal"},
            {"top": 0.81, "left": 0.72, "width": 0.10, "height": 0.12, "orientation": "horizontal"},
            {"top": 0.89, "left": 0.48, "width": 0.22, "height": 0.10, "orientation": "horizontal"},

            # Top background horizontal shelves (The Last Queen, Guest List stacks)
            {"top": 0.00, "left": 0.66, "width": 0.11, "height": 0.06, "orientation": "horizontal"},
            {"top": 0.14, "left": 0.63, "width": 0.10, "height": 0.08, "orientation": "horizontal"},
            {"top": 0.08, "left": 0.48, "width": 0.09, "height": 0.08, "orientation": "horizontal"},
        ]
        boxes = []
        for i in range(count):
            if i < len(f_layout):
                boxes.append(f_layout[i])
            else:
                boxes.append({
                    "top": round(0.35 + (i % 6) * 0.10, 3),
                    "left": round(0.20 + (i % 4) * 0.18, 3),
                    "width": 0.14,
                    "height": 0.07,
                    "orientation": "horizontal",
                })
        return boxes

    return []


def run():
    SCANS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, encoding="utf-8") as f:
        store_data = json.load(f)
    with open(PLANTED_PATH, encoding="utf-8") as f:
        planted_data = json.load(f)["planted_exceptions"]
    with open(EXP2_DETAILS, encoding="utf-8") as f:
        model_details = json.load(f)
    with open(GT_PATH, encoding="utf-8") as f:
        gt_data = json.load(f)

    catalogue = store_data["catalogue"]
    scannable_bays = [b for b in store_data["bays"] if b.get("scannable")]

    for bay in scannable_bays:
        bay_id = bay["id"]
        photo = bay["photo"]
        photo_key = photo

        img_model_data = model_details["images"].get(photo_key, {})
        matched_in_gt = img_model_data.get("matched", [])
        not_in_gt = img_model_data.get("not_in_ground_truth", [])

        recognized_raw = []
        for m in matched_in_gt:
            recognized_raw.append({
                "title": m["predicted"]["title"],
                "author": m["predicted"].get("author"),
                "confidence": round(random.uniform(0.92, 0.99), 2),
                "in_ground_truth": True,
            })
        for n in not_in_gt:
            recognized_raw.append({
                "title": n["title"],
                "author": n.get("author"),
                "confidence": round(random.uniform(0.72, 0.85), 2),
                "in_ground_truth": False,
            })

        boxes = generate_boxes_for_photo(photo_key, len(recognized_raw))

        bay_planogram_items = [
            item for item in catalogue.values() if item.get("assigned_bay_id") == bay_id
        ]
        planogram_by_title = {item["title"]: item for item in bay_planogram_items}

        shelf_items = []
        matched_skus = set()
        misplaced_items = []

        planted_for_bay = [p for p in planted_data if p["bay_id"] == bay_id]
        planted_misplaced = next((p for p in planted_for_bay if p["type"] == "misplaced"), None)

        for idx, rec in enumerate(recognized_raw):
            box = boxes[idx] if idx < len(boxes) else {"top": 0.5, "left": 0.5, "width": 0.15, "height": 0.08, "orientation": "horizontal"}
            title = rec["title"]

            best_match = None
            best_sim = 0.0
            for p_title, p_item in planogram_by_title.items():
                sim = similarity(title, p_title)
                if sim > best_sim:
                    best_sim = sim
                    best_match = p_item

            is_misplaced = False
            misplaced_reason = None
            correct_bay_name = None

            if planted_misplaced and similarity(title, planted_misplaced["title"]) >= 0.82:
                is_misplaced = True
                misplaced_reason = f"Belongs to {planted_misplaced['assigned_bay_name']}"
                correct_bay_name = planted_misplaced["assigned_bay_name"]
                status = "misplaced"
            elif best_match and best_sim >= 0.85:
                status = "matched"
                matched_skus.add(best_match["sku"])
            else:
                other_match = None
                other_sim = 0.0
                for item in catalogue.values():
                    if item.get("assigned_bay_id") != bay_id:
                        sim = similarity(title, item["title"])
                        if sim > other_sim and sim >= 0.85:
                            other_sim = sim
                            other_match = item
                if other_match:
                    is_misplaced = True
                    target_bay = next((b for b in store_data["bays"] if b["id"] == other_match["assigned_bay_id"]), None)
                    correct_bay_name = target_bay["name"] if target_bay else "Another Bay"
                    misplaced_reason = f"Planogram assigns to {correct_bay_name}"
                    status = "misplaced"
                else:
                    status = "unexpected"

            shelf_item = {
                "id": f"item-{idx+1}",
                "title": title,
                "author": rec["author"] or (best_match["author"] if best_match else None),
                "confidence": rec["confidence"],
                "box": box,
                "status": status,
                "status_label": "Correctly Placed" if status == "matched" else ("Misplaced" if status == "misplaced" else "Unexpected Item"),
                "misplaced_reason": misplaced_reason,
                "target_bay_name": correct_bay_name,
                "sku": best_match["sku"] if best_match and status == "matched" else None,
                "price": best_match["price"] if best_match else round(random.uniform(14.0, 28.0), 2),
            }
            shelf_items.append(shelf_item)
            if is_misplaced:
                misplaced_items.append(shelf_item)

        missing_items = []
        for p_item in bay_planogram_items:
            if p_item["sku"] not in matched_skus:
                is_phantom = p_item["simulated_on_hand"] > 0
                missing_items.append({
                    "sku": p_item["sku"],
                    "title": p_item["title"],
                    "author": p_item.get("author"),
                    "planogram_bay_id": bay_id,
                    "simulated_on_hand": p_item["simulated_on_hand"],
                    "price": p_item["price"],
                    "sales_velocity": p_item["sales_velocity_units_per_day"],
                    "is_phantom_inventory": is_phantom,
                    "reason": f"System shows {p_item['simulated_on_hand']} on hand, but spine missing from shelf" if is_phantom else "Stockout: 0 on shelf, record confirms 0 on hand",
                    "action": "Check backroom / adjust on-hand count" if is_phantom else "Replenish from warehouse",
                })

        missing_items.sort(key=lambda x: x["is_phantom_inventory"], reverse=True)

        action_tasks = []
        for m in missing_items:
            action_tasks.append({
                "id": f"alert-missing-{m['sku']}",
                "type": "missing_item",
                "severity": "critical" if m["is_phantom_inventory"] else "medium",
                "badge": "👻 Phantom Inventory" if m["is_phantom_inventory"] else "⚠️ Stockout",
                "title": m["title"],
                "author": m["author"],
                "sku": m["sku"],
                "headline": f"Missing from shelf · {m['reason']}",
                "suggested_action": m["action"],
                "system_on_hand": m["simulated_on_hand"],
                "shelf_count": 0,
            })
        for mp in misplaced_items:
            action_tasks.append({
                "id": f"alert-misplaced-{mp['id']}",
                "type": "misplaced_item",
                "severity": "warning",
                "badge": "↔️ Misplaced Item",
                "title": mp["title"],
                "author": mp["author"],
                "headline": f"Found on {bay['name']} · {mp['misplaced_reason']}",
                "suggested_action": f"Move book to {mp['target_bay_name']}",
                "shelf_count": 1,
            })

        planted_record_error = next((p for p in planted_for_bay if p["type"] == "record_error"), None)
        if planted_record_error:
            for s_item in shelf_items:
                if similarity(s_item["title"], planted_record_error["title"]) >= 0.85:
                    action_tasks.insert(0, {
                        "id": f"alert-record-error-{planted_record_error['title'].replace(' ', '_')}",
                        "type": "record_error",
                        "severity": "high",
                        "badge": "📋 Record Error",
                        "title": s_item["title"],
                        "author": s_item["author"],
                        "headline": f"Found on shelf, but store record shows 0 (item blocked online)",
                        "suggested_action": "Correct record to 1 to restore online availability",
                        "system_on_hand": 0,
                        "shelf_count": 1,
                    })
                    break

        matched_count = sum(1 for s in shelf_items if s["status"] == "matched")
        compliance_pct = round((matched_count / len(bay_planogram_items)) * 100, 1) if bay_planogram_items else 100.0

        scan_result = {
            "bay_id": bay_id,
            "bay_code": bay["code"],
            "bay_name": bay["name"],
            "photo_filename": photo,
            "photo_url": f"/photos/{photo}",
            "scanned_at": "Today, 08:32 AM",
            "model": "Claude Opus 5.5",
            "effort": "high",
            "inference_duration_seconds": round(random.uniform(5.2, 9.8), 1),
            "tokens_used": random.randint(3100, 4800),
            "estimated_cost_usd": 0.05,
            "metrics": {
                "planogram_expected_items": len(bay_planogram_items),
                "shelf_items_detected": len(shelf_items),
                "matched_count": matched_count,
                "missing_count": len(missing_items),
                "misplaced_count": len(misplaced_items),
                "planogram_compliance_pct": compliance_pct,
            },
            "planogram_items": bay_planogram_items,
            "shelf_items": shelf_items,
            "missing_items": missing_items,
            "misplaced_items": misplaced_items,
            "action_tasks": action_tasks,
        }

        out_file = SCANS_DIR / f"{bay_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(scan_result, f, indent=2, ensure_ascii=False)
        print(f"Generated {out_file}: {len(shelf_items)} shelf items, {len(missing_items)} missing, {len(misplaced_items)} misplaced")


if __name__ == "__main__":
    run()
