from __future__ import annotations

import argparse
import json
from pathlib import Path

from swmm_api import read_inp_file


def section_count(inp, name: str) -> int:
    section = getattr(inp, name, None)
    try:
        return len(section) if section is not None else 0
    except TypeError:
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a SWMM .inp using swmm_api.")
    parser.add_argument("inp")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    inp_path = Path(args.inp).resolve()
    model = read_inp_file(inp_path)
    summary = {
        "inp": str(inp_path),
        "junctions": section_count(model, "JUNCTIONS"),
        "outfalls": section_count(model, "OUTFALLS"),
        "conduits": section_count(model, "CONDUITS"),
        "subcatchments": section_count(model, "SUBCATCHMENTS"),
        "raingages": section_count(model, "RAINGAGES"),
        "timeseries": section_count(model, "TIMESERIES"),
        "classification": "SYNTHETIC_UDM_RESEARCH_MVP",
    }
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
