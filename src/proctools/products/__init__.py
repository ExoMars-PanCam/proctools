from .dataproduct import DataProduct
from .depot import ProductDepot
from .util import BayerSlice, get_md5sum

# Register subclasses automatically for now.
# Can revisit if we ever need to support multiple instruments
from . import pancam
