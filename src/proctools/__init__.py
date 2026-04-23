"""Common tools for (ExoMars) data product processing software.
"""

# Bring in some metadata from the package.
import importlib.metadata as importlib_metadata # type: ignore

# Copy it into module-level variables.
_dist_meta = importlib_metadata.metadata("proctools")
__author__ = _dist_meta["Author"]
__description__ = _dist_meta["Summary"]
__project__ = _dist_meta["Name"]
__url__ = next(
    item.replace("Repository, ", "", 1)
        for item in _dist_meta.get_all("Project-URL")
            if item.startswith("Repository, ")
)
__version__ = _dist_meta["Version"]
del _dist_meta, importlib_metadata
