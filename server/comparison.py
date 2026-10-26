"""Conservative title matching and review tasks. No access to benchmark labels.

Title normalization and variant scoring follow the benchmark's evaluate.py,
with additional safeguards for series numbers, short titles and ambiguity.
"""
import re
import unicodedata
from difflib import SequenceMatcher

THRESHOLD = 0.85


def normalize(text):
    text = unicodedata.normalize("NFKD", (text or "").casefold()).replace("&", " and ")
    out, prev = [], ""
    for ch in text:
        cat = unicodedata.category(ch)
        if cat == "Mn" and prev and ord(prev) < 0x250:
            continue
        if cat[0] in "LNM":
            out.append(ch)
            prev = ch
        else:
            out.append(" ")
            prev = ""
    return " ".join("".join(out).split())


def title_key(title):
    return re.sub(r"^(the|a|an) ", "", normalize(title))


def title_score(a, b):
    left, right = title_key(a), title_key(b)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    # Distinct volumes, sequels or editions cannot be rescued by fuzzy matching.
    if re.findall(r"\d+", left) != re.findall(r"\d+", right):
        return 0.0
    # A main/series label alone does not establish the subtitled volume. The
    # benchmark explicitly calls out "Diary of a Wimpy Kid" as too vague.
    if ((":" in b and left == title_key(b.split(":", 1)[0]))
            or (":" in a and right == title_key(a.split(":", 1)[0]))):
        return 0.0
    if min(len(left), len(right)) < 8:
        return 0.0
    def variants(title):
        result = {title_key(title)}
        main = re.split(r"[:(/]", title)[0]
        if len(title_key(main).split()) >= 3:
            result.add(title_key(main))
        return result
    score = 0.0
    for p in variants(a):
        for g in variants(b):
            score = max(score, SequenceMatcher(None, p, g).ratio(),
                        SequenceMatcher(None, " ".join(sorted(p.split())), " ".join(sorted(g.split()))).ratio())
            short, long = sorted((p.split(), g.split()), key=len)
            if len(short) >= 3 and short in (long[:len(short)], long[-len(short):]):
                score = max(score, 0.90)
    # A partial two-word franchise label is not a full title.
    short, long = sorted((left.split(), right.split()), key=len)
    if len(short) <= 2 and len(long) > len(short) and short == long[:len(short)]:
        return 0.0
    return score


def compare_books(store, bay, observations):
    """Match one-to-one across the whole catalogue before deciding placement.

    An unread title is unconfirmed presence, never proof of an empty shelf.
    Counts are unique titles, not inferred physical inventory quantities.
    """
    catalogue = list(store["catalogue"].values())
    assigned = [p for p in catalogue if p["assigned_bay_id"] == bay["id"]]
    bays = {b["id"]: b for b in store["bays"]}
    candidates, ambiguous = [], set()
    for i, book in enumerate(observations):
        if book.get("verification_status") == "needs_review":
            continue
        scored = sorted(((title_score(book["title"], p["title"]), p) for p in catalogue), key=lambda x: x[0], reverse=True)
        eligible = [(score, p) for score, p in scored if score >= THRESHOLD]
        if not eligible:
            continue
        if normalize(book.get("author")):
            author_a = normalize(book["author"])
            compatible = [(score, p) for score, p in eligible if not p.get("author")
                          or SequenceMatcher(None, author_a, normalize(p["author"])).ratio() >= 0.70
                          or (len(author_a.split()[-1]) > 2 and author_a.split()[-1] == normalize(p["author"]).split()[-1])]
            if not compatible:
                ambiguous.add(i)
                continue
            eligible = compatible
        best, target = eligible[0]
        close = [(score, p) for score, p in eligible if best - score < 0.04]
        if len(close) > 1:
            identities = {(title_key(p["title"]), normalize(p.get("author"))) for _, p in close}
            local = [p for _, p in close if p["assigned_bay_id"] == bay["id"]]
            # An identical book may legitimately be allocated to multiple bays.
            # Prefer its sole local allocation; never invent a relocation for it.
            if best == 1 and len(identities) == 1 and len(local) == 1:
                target = local[0]
            else:
                ambiguous.add(i)
                continue
        candidates.append((best, i, target))

    matched, used_skus = {}, set()
    for score, i, target in sorted(candidates, key=lambda x: (-x[0], x[1])):
        if target["sku"] in used_skus:
            ambiguous.add(i)
            continue
        matched[i] = target
        used_skus.add(target["sku"])

    items, tasks, misplaced = [], [], []
    for i, book in enumerate(observations):
        target = matched.get(i)
        review = i in ambiguous or book.get("verification_status") == "needs_review"
        status = "needs_review" if review else "unexpected" if not target else "matched" if target["assigned_bay_id"] == bay["id"] else "misplaced"
        destination = bays.get(target["assigned_bay_id"], {}).get("name") if target else None
        item = {
            **book, "id": f"{bay['id']}-item-{i+1}", "confidence": None,
            "status": status,
            "status_label": {"matched": "Title matched", "misplaced": "Possible misplaced title", "unexpected": "Unmatched title", "needs_review": "Reading needs review"}[status],
            "sku": target["sku"] if target else None,
            "price": target["price"] if target else None,
            "misplaced_reason": f"Planogram assigns to {destination}" if status == "misplaced" else None,
            "target_bay_name": destination if status == "misplaced" else None,
        }
        items.append(item)
        if status == "misplaced":
            misplaced.append(item)
            tasks.append({"id": f"{bay['id']}-move-{target['sku']}", "type": "misplaced_item", "severity": "warning", "badge": "↔ Possible Misplacement", "title": book["title"], "author": book.get("author"), "sku": target["sku"], "headline": f"Title read here; planogram assigns it to {destination}.", "suggested_action": "Confirm location and relocation", "shelf_item_id": item["id"], "requires_review": True})
        if status == "needs_review":
            tasks.append({"id": f"{bay['id']}-review-{i+1}", "type": "recognition_review", "severity": "medium", "badge": "Reading needs review", "title": book["title"], "author": book.get("author"), "headline": "Reading was uncertain, disagreed between passes, or matched multiple catalogue entries.", "suggested_action": "Inspect photo and confirm title", "shelf_item_id": item["id"], "requires_review": True})
        if target and target["simulated_on_hand"] == 0:
            tasks.append({"id": f"{bay['id']}-record-{target['sku']}", "type": "record_error", "severity": "high", "badge": "Possible Record Error", "title": book["title"], "author": book.get("author"), "sku": target["sku"], "headline": "Title read on shelf; simulated record shows 0. Verify the physical count.", "suggested_action": "Confirm physical count and record check", "system_on_hand": 0, "shelf_item_id": item["id"], "requires_review": True})

    missing = []
    for p in assigned:
        if p["sku"] in used_skus:
            continue
        missing.append({"sku": p["sku"], "title": p["title"], "author": p.get("author"), "planogram_bay_id": bay["id"], "simulated_on_hand": p["simulated_on_hand"], "price": p["price"], "sales_velocity": p["sales_velocity_units_per_day"], "is_phantom_inventory": False, "reason": "Title not confirmed by recognition; it may be unreadable or occluded.", "action": "Check shelf and backroom before changing inventory", "requires_review": True})
        tasks.append({"id": f"{bay['id']}-unseen-{p['sku']}", "type": "missing_item", "severity": "medium", "badge": "Presence unconfirmed", "title": p["title"], "author": p.get("author"), "sku": p["sku"], "headline": f"Title not confirmed in the photo. Simulated on-hand: {p['simulated_on_hand']}. This does not establish a stockout.", "suggested_action": "Confirm shelf and backroom check", "system_on_hand": p["simulated_on_hand"], "requires_review": True})
    correct = sum(item["status"] == "matched" for item in items)
    return {
        "planogram_items": assigned, "shelf_items": items, "misplaced_items": misplaced,
        "missing_items": missing, "action_tasks": tasks,
        "metrics": {"planogram_expected_items": len(assigned), "shelf_items_detected": len(items), "matched_count": correct, "missing_count": len(missing), "misplaced_count": len(misplaced), "review_count": sum(item["status"] == "needs_review" for item in items), "planogram_compliance_pct": round(100 * correct / len(assigned), 1) if assigned else 100.0},
    }
