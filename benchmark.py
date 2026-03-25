import timeit

setup = """
keys = [{'MASTERNAME': 'table1'}, {'mastername': 'table2'}, {'MASTERNAME': 'table1'}, {'mastername': 'table3'}] * 1000
"""

stmt1 = """
modified_tables = list(
    set(
        [
            str(k.get("MASTERNAME", k.get("mastername", "")))
            for k in keys
            if k.get("MASTERNAME") or k.get("mastername")
        ]
    )
)
"""

stmt2 = """
modified_tables = list(
    {
        str(k.get("MASTERNAME", k.get("mastername", "")))
        for k in keys
        if k.get("MASTERNAME") or k.get("mastername")
    }
)
"""

n = 1000
time1 = timeit.timeit(stmt1, setup=setup, number=n)
time2 = timeit.timeit(stmt2, setup=setup, number=n)

print(f"Baseline (List -> Set -> List): {time1:.4f} seconds for {n} iterations")
print(f"Optimized (Set Comprehension -> List): {time2:.4f} seconds for {n} iterations")
print(f"Improvement: {(time1 - time2) / time1 * 100:.2f}% faster")
