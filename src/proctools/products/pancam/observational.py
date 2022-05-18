import numpy as np
from pds4_tools.extern.cached_property import threaded_cached_property

from ..dataproduct import DataProduct
from ..mixins import SortStartTimeMixin
from . import PANCAM_META_MAP
from .mixins import MatchCameraMixin


class Observational(MatchCameraMixin, SortStartTimeMixin, DataProduct, abstract=True):
    _META_MAP = PANCAM_META_MAP


class Observation(Observational, type_name="observation"):
    """PAN-PP-200"""

    @threaded_cached_property
    def data(self) -> np.ndarray:
        if self.sl is not None:
            return self.sl["SCIENCE_IMAGE_DATA"].data
        else:
            return None  # TODO: data blanks from Template def


class SpecRad(Observational, type_name="spec-rad"):
    """PAN-PP-220"""

    @threaded_cached_property
    def data(self) -> np.ndarray:
        if self.sl is not None:
            return self.sl["DATA"].data
        else:
            return None  # TODO: data blanks from Template defs

    @threaded_cached_property
    def dq(self) -> np.ndarray:
        if self.sl is not None:
            return self.sl["QUALITY"].data
        else:
            return None  # TODO: data blanks from Template defs

    @threaded_cached_property
    def err(self) -> np.ndarray:
        if self.sl is not None:
            return self.sl["UNCERTAINTY"].data
        else:
            return None  # TODO: data blanks from Template defs


class AppCol(Observational, type_name="app-col"):
    """PAN-PP-221"""

    @threaded_cached_property
    def data(self) -> np.ndarray:
        if self.sl is not None:
            return self.sl["DATA"].data
        else:
            return None  # TODO: data blanks from Template defs

    @threaded_cached_property
    def dq(self) -> np.ndarray:
        if self.sl is not None:
            return self.sl["QUALITY"].data
        else:
            return None  # TODO: data blanks from Template defs

    @threaded_cached_property
    def err(self) -> np.ndarray:
        if self.sl is not None:
            return self.sl["UNCERTAINTY"].data
        else:
            return None  # TODO: data blanks from Template defs