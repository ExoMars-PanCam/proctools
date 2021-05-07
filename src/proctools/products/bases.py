import logging
from pathlib import Path
from typing import ClassVar, Dict, Optional, Union

import numpy as np
import pds4_tools
from lxml import etree
from passthrough import Template
from passthrough.extensions.pt.datetime import PDSDatetime
from pds4_tools.reader.general_objects import StructureList
from pds4_tools.reader.label_objects import Label
from pds4_tools.reader.table_objects import TableStructure


class LabelMeta:
    """Single-layer XML element lookup based on path monikers.

    Takes an XML tree and a moniker->(x)path mapping (i.e. nickname and path pairs for
    elements). Monikers can be accessed as attributes of this class, which will
    dynamically return the associated element's text. Index key notation can be used to
    retrieve the element itself for a moniker instead of the text.

    TODO:
        - See if it's worth caching attributes when DataProduct is initialised via
          pds4_tools (i.e. when the product can be considered read-only). Likely not.

    Attributes:
        All monikers provided at initialisation (see __init__ for details).
    """

    def __init__(
        self,
        label: Union[Label, etree._ElementTree],
        attrs: Dict[str, str],
        nsmap: Dict[str, str] = None,
    ):
        """Expose text of `label` elements given by `attrs` as attributes.

        Args:
            label: XML context document.
            attrs: moniker->(x)path mapping; the former are exposed as attributes on the
                class.
            nsmap: Namespace mapping to use when resolving moniker paths in `label`.
        """
        self._kwargs = {"namespaces": nsmap}
        if isinstance(label, Label):
            self._kwargs["unmodified"] = True
        self._label = label
        self._attrs = attrs

    def __getitem__(self, moniker: str):
        path = self._path_for(moniker)
        try:
            return self._attr_for(path)
        except AttributeError:
            return None

    def __getattr__(self, moniker: str):
        return self._attr_for(self._path_for(moniker)).text

    def __setattr__(self, key: str, value: str):
        if key.startswith("_"):
            return super().__setattr__(key, value)
        path = self._path_for(key)
        self._attr_for(path).text = value

    def _path_for(self, moniker: str):
        path = self._attrs.get(moniker, None)
        if path is None:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{moniker}'"
            )
        return path

    def _attr_for(self, path: str):
        attr = self._label.find(path, **self._kwargs)
        if attr is None:
            raise AttributeError(
                f"Label '{self._label}' has no PDS4 attribute '{path}'"
            )
        return attr


class DataProduct:
    """Provide a consistent interface to PDS4 product labels.

    This is a base class which should not be instantiated directly. Subclasses
    aligned to product types (as in type templates) extend the base interface based on
    their requirements. Mixins are used to provide feature-based shared functionality.

    Attributes:
        filename Optional: The name of the file the product was loaded from.
        label: The XML document tree (lxml or builtin xml).
        meta: `LabelMeta` object for convenient access to the text of `label` elements
            exposed by `_META_MAP`.
        sl Optional: `label`'s structure list, if loaded via `pds4_tools`.
        template: `label`'s template handler, if loaded via `passthrough`.
    """

    _supported_types: ClassVar[dict] = {}
    type: ClassVar[str] = None
    _META_MAP = {
        "lid": ".//pds:Identification_Area/pds:logical_identifier",
        "start": ".//pds:Time_Coordinates/pds:start_date_time",
        "stop": ".//pds:Time_Coordinates/pds:stop_date_time",
        "type": ".//msn:Mission_Information/msn:product_type_name",
        "sub_instrument": ".//psa:Sub-Instrument/psa:identifier",
        "camera": ".//psa:Sub-Instrument/psa:identifier",  # sanity alias
        "filter": ".//img:Optical_Filter/img:filter_number",
        # TODO: subframe params, temperature, ++ (maybe in sublasses)
        "exposure_duration": ".//img:Exposure/img:exposure_duration",
        "model": ".//img_surface:Instrument_Information/img_surface:instrument_version_number",
    }

    def __init__(self, init: Union[StructureList, Template], filename: str = None):
        """Wrap a PDS4 product for convenient access.

        Args:
            init: PDS4 product as loaded from `pds4_tools` or `passthrough`
            filename: Optional name of the file used to load the product.
        """
        if isinstance(init, StructureList):
            self.template = None
            self.sl = init
            self.label = self.sl.label
        elif isinstance(init, Template):
            self.sl = None
            self.template = init
            self.label = self.template.label
        else:
            raise ValueError(
                f"`init` must be in the form of a StructureList or Template"
            )
        self.filename = filename
        self.meta = LabelMeta(
            self.label, self._META_MAP, (self.template.nsmap if self.template else None)
        )
        self._log = logging.getLogger(self.__class__.__module__)

    def __init_subclass__(cls, type_name=None, **kwargs):
        if type_name is None:
            raise TypeError(
                f"{cls.__name__} does not specify the required class parameter"
                " 'type_name' (its associated PDS4 product type name/mnemonic)"
            )
        super().__init_subclass__(**kwargs)
        cls.type = type_name
        cls._supported_types[type_name] = cls

    def __lt__(self, other):
        return self.meta.lid < other.meta.lid

    def is_applicable(self, other: "DataProduct"):
        return NotImplemented

    @classmethod
    def from_file(cls, path: Path, type_: Optional[str] = None):
        """Find and instantiate the correct DataProduct subclass from `path`

        The subclass is determined by the loaded product's type name
        (`//msn:Mission_Information/msn:product_type_name`).

        Args:
            path: Location of the product to be loaded (via `pds4_tools`).
            type_: Optional product type override (overrides any defined in by the
                loaded product).

        Raises:
            TypeError: If no expected type is set and the loaded product does not define
             a type, or if its defined type does not match that of any registered
             subclass.
        """
        st = pds4_tools.read(str(path), lazy_load=True, quiet=True)
        st.label.default_root = "unmodified"  # allow e.g. `pds:` prefixes to work...
        if "msn" not in st.label.get_namespace_map().values():
            raise TypeError(f"Product loaded from {path.name} does not define a type")
        type_ = type_ or st.label.find(cls._META_MAP["type"]).text
        product = cls._supported_types.get(type_, None)
        if product is None:
            raise TypeError(
                f"Product '{type_}' loaded from {path} does not match any known type"
            )
        return product(st, path.name)


class ObservationalMixin:
    """Allow `DataProduct`s to be sorted by `pds:start_date_time`."""

    def __lt__(self, other: "ObservationalMixin"):
        return (
            PDSDatetime(self.meta.start).datetime
            < PDSDatetime(other.meta.start).datetime
        )


class ApplicableCameraMixin:
    """Allow `DataProduct`s to evaluate applicability based on `psa:Sub-Instrument`."""

    def is_applicable(self, other: "ApplicableCameraMixin"):
        return other.meta.camera == self.meta.camera


class MultiData:
    """Provide access to a list's given structure's data via index key notation."""

    def __init__(self, structures: StructureList, fmt: str = "{}"):
        self.sl = structures
        self.fmt = fmt

    def __getitem__(self, struct):
        return self.sl[self.fmt.format(struct)].data


class KeyTable:
    """Select row(s) of a table based on the value of a key field."""

    def __init__(self, table: TableStructure, key_field: str):
        self.ts = table
        self.key_field = key_field

    def __getitem__(self, key: Union[int, str]):
        # select record(s) by value of key field (e.g. "filter" field is 4)
        return self.ts[np.where(self.ts[self.key_field] == key)]
