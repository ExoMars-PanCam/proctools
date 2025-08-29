"""ProcTools - Common tools for (ExoMars) data product processing software.

"""

# Bring in some metadata from the package.
try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

# Copy it into module-level variables.
_dist_meta = importlib_metadata.metadata("proctools")
__author__ = _dist_meta["Author-email"]
__description__ = _dist_meta["Summary"]
__project__ = _dist_meta["Name"]
__version__ = _dist_meta["Version"]
del _dist_meta

__all__ = [
    "__author__",
    "__version__",
]
