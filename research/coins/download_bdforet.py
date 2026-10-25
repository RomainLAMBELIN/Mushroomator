"""BD Forêt V2 for the other départements (FORMATION_VEGETALE only); the archive is deleted after extraction."""
import concurrent.futures as cf, json, sys, time
from pathlib import Path
ROOT = Path(sys.argv[1]); sys.path.insert(0, str(ROOT))
from mushroomator.sources import bdforet  # noqa: E402

todo = json.loads(Path(sys.argv[2]).read_text())
raw = ROOT / "data/raw/bdforet"

def one(dept):
    for attempt in range(3):
        try:
            shp = bdforet.fetch(dept, raw)
            arc = raw / f"D{dept}.7z"
            if arc.exists():
                arc.unlink()
            return dept, "ok", shp.stat().st_size
        except Exception as e:
            last = e
            time.sleep(10 * (attempt + 1))
    return dept, f"échec {last}", 0

t0 = time.time()
with cf.ThreadPoolExecutor(3) as pool:
    for i, (dept, status, size) in enumerate(pool.map(one, todo), 1):
        print(f"{i}/{len(todo)} D{dept} {status} {size / 1e6:.0f} Mo {time.time() - t0:.0f} s", flush=True)
