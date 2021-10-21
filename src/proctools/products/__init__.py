from .adapters import KeyTable, MultiData
from .dataproduct import DataProduct
from .mixins import ApplicableCameraMixin, ObservationalMixin
from .loader import ProductLoader as _Loader
from .util import get_md5sum

loader = _Loader()
