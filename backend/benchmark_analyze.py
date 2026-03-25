import time
import random
import uuid

def generate_data(num_raw, num_selected):
    raw_tr_data = []

    selected_trs = []

    for i in range(num_raw):
        is_parent = random.choice([True, False])
        if is_parent:
            trkorr = f"TR{i}"
            strkorr = ""
            if len(selected_trs) < num_selected:
                selected_trs.append(trkorr)
        else:
            trkorr = f"TR{i}"
            strkorr = f"TR{random.randint(0, num_raw)}"

        raw_tr_data.append({
            "TRKORR": trkorr,
            "STRKORR": strkorr,
            "objects": [{"OBJECT": "PROG", "OBJ_NAME": f"PROG{i}"}],
            "keys": []
        })

    return raw_tr_data, selected_trs

def run_old(raw_tr_data, selected_trs):
    tr_data = []
    for parent_tr_no in selected_trs:
        parent_obj = next(
            (
                tr
                for tr in raw_tr_data
                if (tr.get("TRKORR") or tr.get("trkorr")) == parent_tr_no
            ),
            None,
        )
        if not parent_obj:
            continue
        merged_objects = list(
            parent_obj.get("objects", parent_obj.get("OBJECTS", []))
        )
        merged_keys = list(
            parent_obj.get("keys", parent_obj.get("KEYS", []))
        )
        children = [
            tr
            for tr in raw_tr_data
            if (tr.get("STRKORR") or tr.get("strkorr")) == parent_tr_no
        ]
        for child in children:
            merged_objects.extend(
                child.get("objects", child.get("OBJECTS", []))
            )
            merged_keys.extend(child.get("keys", child.get("KEYS", [])))
        enriched_tr = dict(parent_obj)
        enriched_tr["objects"] = merged_objects
        enriched_tr["keys"] = merged_keys
        tr_data.append(enriched_tr)
    return tr_data

def run_new(raw_tr_data, selected_trs):
    tr_data = []
    tr_by_trkorr = {}
    children_by_strkorr = {}

    for tr in raw_tr_data:
        trkorr = tr.get("TRKORR") or tr.get("trkorr")
        if trkorr:
            tr_by_trkorr[trkorr] = tr

        strkorr = tr.get("STRKORR") or tr.get("strkorr")
        if strkorr:
            if strkorr not in children_by_strkorr:
                children_by_strkorr[strkorr] = []
            children_by_strkorr[strkorr].append(tr)

    for parent_tr_no in selected_trs:
        parent_obj = tr_by_trkorr.get(parent_tr_no)
        if not parent_obj:
            continue
        merged_objects = list(
            parent_obj.get("objects", parent_obj.get("OBJECTS", []))
        )
        merged_keys = list(
            parent_obj.get("keys", parent_obj.get("KEYS", []))
        )
        children = children_by_strkorr.get(parent_tr_no, [])
        for child in children:
            merged_objects.extend(
                child.get("objects", child.get("OBJECTS", []))
            )
            merged_keys.extend(child.get("keys", child.get("KEYS", [])))
        enriched_tr = dict(parent_obj)
        enriched_tr["objects"] = merged_objects
        enriched_tr["keys"] = merged_keys
        tr_data.append(enriched_tr)
    return tr_data


raw_tr_data, selected_trs = generate_data(50000, 1000)

start = time.time()
res1 = run_old(raw_tr_data, selected_trs)
old_time = time.time() - start

start = time.time()
res2 = run_new(raw_tr_data, selected_trs)
new_time = time.time() - start

assert len(res1) == len(res2)

print(f"Old time: {old_time:.4f}s")
print(f"New time: {new_time:.4f}s")
print(f"Speedup: {old_time / new_time:.2f}x")
