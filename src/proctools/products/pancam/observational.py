import numpy as np
from pds4_tools.extern.cached_property import threaded_cached_property

from passthrough.exc import PTTemplateError

from .file_handlers import PanCamFH
from ..dataproduct import DataProduct
from ..mixins import SortStartTimeMixin
from . import PANCAM_META_MAP, PANCAM_MOSAIC_META_MAP
from .mixins import BrowseMixin, MatchCameraMixin


class Observational(
    MatchCameraMixin, SortStartTimeMixin, BrowseMixin, DataProduct, abstract=True
):
    _META_MAP = PANCAM_META_MAP

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.sl is not None:
            self._data_source = self.sl
            return
        assert self.template is not None
        fas = self.label.xpath(
            "*[starts-with(name(), 'File_Area_')]", namespaces=self.template.nsmap
        )
        if len(fas) != 1:
            raise PTTemplateError(
                f"Expected 1 File_Area_* in template; found {len(fas)}"
            )
        self._data_source = PanCamFH(fas[0], self.nsmap)
        self.template.register_file_handler(self._data_source)


class Observation(Observational, type_name="observation"):
    """PAN-PP-200"""

    @threaded_cached_property
    def data(self) -> np.ndarray:
        return self._data_source["SCIENCE_IMAGE_DATA"].data


class SpecRad(Observational, type_name="spec-rad"):
    """PAN-PP-220"""

    @threaded_cached_property
    def data(self) -> np.ndarray:
        return self._data_source["DATA"].data

    @threaded_cached_property
    def dq(self) -> np.ndarray:
        return self._data_source["QUALITY"].data

    @threaded_cached_property
    def err(self) -> np.ndarray:
        return self._data_source["UNCERTAINTY"].data


class AppCol(Observational, type_name="app-col"):
    """PAN-PP-221"""

    @threaded_cached_property
    def data(self) -> np.ndarray:
        return self._data_source["DATA"].data

    @threaded_cached_property
    def dq(self) -> np.ndarray:
        return self._data_source["QUALITY"].data

    @threaded_cached_property
    def err(self) -> np.ndarray:
        return self._data_source["UNCERTAINTY"].data

class Mosaic(Observational, type_name="mosaic"):
    """PAN-PP-240"""
    _META_MAP = PANCAM_MOSAIC_META_MAP

    @threaded_cached_property
    def data(self) -> np.ndarray:
        return self._data_source["IMAGE_DATA"].data
