import os
import django
import time
import sys
import tracemalloc

# Set up Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import DependencySnapshot

def measure_memory_without_iterator(cap):
    tracemalloc.start()
    count = 0
    # Create the list explicitly to simulate what happens during iteration without iterator
    # Note: querysets are evaluated when iterated over and cache results in memory
    docs = []
    for row in DependencySnapshot.objects.all()[:cap]:
        count += 1
        docs.append(str(row)) # Keep something in memory to simulate doc creation

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return current, peak, docs

def measure_memory_with_iterator(cap):
    tracemalloc.start()
    count = 0
    docs = []
    for row in DependencySnapshot.objects.all()[:cap].iterator(chunk_size=1000):
        count += 1
        docs.append(str(row)) # Keep something in memory to simulate doc creation

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return current, peak, docs

if __name__ == "__main__":
    cap = 10000

    # Measure memory
    _, peak_without, _ = measure_memory_without_iterator(cap)
    _, peak_with, _ = measure_memory_with_iterator(cap)

    print(f"Memory Peak Without iterator: {peak_without / 1024 / 1024:.4f} MB")
    print(f"Memory Peak With iterator: {peak_with / 1024 / 1024:.4f} MB")
