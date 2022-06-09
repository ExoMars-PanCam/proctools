from pathlib import Path
import pytest
import json


class Dataset:
    def __init__(self, path: Path, stats: dict) -> None:
        self.path = path
        self.stats = stats


def _parse_stats(path):
    with open(path) as f:
        try:
            stats: dict = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Error parsing '{path}': {e}")
    stats["num_prod"] = 0
    for type_, prods in stats["types"].items():
        if not isinstance(prods, int):
            pytest.fail(
                f"Error parsing '{path}': expected an integer for entry"
                f" '/types/{type_}'; got {repr(prods)} ({type(prods)})."
            )
        stats["num_prod"] += prods
    return stats


@pytest.fixture(scope="session")
def datasets() -> dict:
    sets = {}
    base_dir = Path(__file__).resolve().parent / "datasets"
    for ds in base_dir.iterdir():
        if not ds.is_dir():
            continue
        stats_path = ds / "stats.json"
        if not stats_path.is_file():
            pytest.fail(
                f"Missing stats.json file for dataset '{ds.name}' in '{base_dir}'"
            )
        stats = _parse_stats(stats_path)
        sets[ds.name] = Dataset(ds, stats)
    return sets


# @pytest.fixture(scope="session")
# def dataset_path():
#     return Path(__file__).resolve().parent / "dataset"


# @pytest.fixture(scope="session")
# def dataset_stats(dataset_path):
#     # TODO: guard exists and do pytest.fail() if not?
#     with open(dataset_path / "stats.json") as f:
#         stats = json.load(f)
#     stats["num_prod"] = 0
#     for _type, prods in stats["types"].items():
#         for prod, num in prods.items():
#             stats["num_prod"] += num
#     return stats
