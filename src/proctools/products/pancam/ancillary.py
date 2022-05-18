from typing import Union

import numpy as np
from pds4_tools.extern.cached_property import threaded_cached_property

from ..adapters import KeyTable, MultiData
from ..dataproduct import DataProduct
from . import PANCAM_META_MAP
from .mixins import MatchCameraMixin


class Ancillary(MatchCameraMixin, DataProduct, abstract=True):
    _META_MAP = PANCAM_META_MAP


class RadFlatPrm(Ancillary, type_name="rad-flat-prm"):
    """PAN-CAL-126"""

    @threaded_cached_property
    def data(self) -> Union[np.ndarray, MultiData]:
        if self.sl is not None:
            if self.meta.camera == "HRC":
                return self.sl["DATA"].data
            else:
                return MultiData(self.sl, "DATA_{:02d}")
        else:
            return None  # TODO: data blanks from Template defs


class RadSsrPrm(Ancillary, type_name="rad-ssr-prm"):
    """PAN-CAL-127"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.sl is not None:
            self.data = KeyTable(self.sl["TABLE"], key_field="filter")
        else:
            self.data = None  # TODO: data blank from Template def


class RadColPrm(Ancillary, type_name="rad-col-prm"):
    """PAN-CAL-129"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # FIXME: change adapter once product has been properly defined...
        if self.sl is not None:
            self.wb = KeyTable(self.sl["TABLE_WHITE_BALANCE"], key_field="filter")
        else:
            self.wb = None  # TODO: data blank from Template def
