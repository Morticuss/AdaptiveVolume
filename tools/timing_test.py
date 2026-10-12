import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adaptive_volume.diagnostics import run_comparison

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', type=int, required=True)
    parser.add_argument('--delay', type=int, default=50)
    args = parser.parse_args()
    print(json.dumps(run_comparison(args.device, args.delay), indent=2))
