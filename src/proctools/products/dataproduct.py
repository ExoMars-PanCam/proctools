import logging
from pathlib import Path
from typing import ClassVar, Optional, Union

import pds4_tools
from lxml import etree
from passthrough import Template
from passthrough.label_tools import add_default_ns, labellike_to_etree
from passthrough.extensions.pt.datetime import PDSDatetime
from pds4_tools.reader.general_objects import StructureList

from .meta import LabelMeta, MetaElement, MetaMap


class DataProduct:
    """Provide a consistent interface to PDS4 product labels.

    This is a base class which should not be instantiated directly. Subclasses
    aligned to product types (as in type templates) extend the base interface based on
    their requirements. Mixins are used to provide feature-based shared functionality.

    Args:
        init: PDS4 product as presented by `pds4_tools` or `passthrough`
        path: Optional path of the file the product was loaded from.

    Attributes:
        filename: The name of the file the product was loaded from.
        label: The XML document tree (lxml or builtin xml).
        meta: `LabelMeta` object exposing those elements of `label` that have been
            declared in this (sub)class' `_META_MAP`.
        sl: `label`'s structure list, if loaded via `pds4_tools`.
        template: `label`'s template handler, if loaded via `passthrough`.
    """

    _supported_types: ClassVar[dict] = {}
    _META_MAP: ClassVar[MetaMap] = MetaMap(
        {
            "Identification_Area": {
                "logical_identifier": MetaElement("lid", ns="pds"),
                "version_id": MetaElement("vid", ns="pds"),
            },
            "Time_Coordinates": {
                "start_date_time": MetaElement(
                    ("start", "start_utc"), PDSDatetime, ns="pds"
                ),
                "stop_date_time": MetaElement(
                    ("stop", "stop_utc"), PDSDatetime, ns="pds"
                ),
            },
            "Mission_Information": {
                "product_type_name": MetaElement("type", ns="msn"),
            },
        }
    )
    type: ClassVar[str] = None

    def __init__(
        self, init: Union[StructureList, Template], path: Optional[Path] = None
    ):
        self.path = path
        if isinstance(init, StructureList):
            self.template = None
            self.sl = init
            self.label = labellike_to_etree(self.sl.label)
            self.nsmap = add_default_ns(self.label.getroot().nsmap)
            self.filename = getattr(self.path, "name", None)
        elif isinstance(init, Template):
            self.sl = None
            self.template = init
            self.label = self.template.label
            self.nsmap = self.template.nsmap
            self.filename = None
        else:
            raise TypeError(f"`init` must take the form of a StructureList or Template")
        self.xpath = etree.XPathEvaluator(
            self.label, namespaces=self.nsmap, regexp=False, smart_strings=False
        )
        self.meta = LabelMeta(self.xpath, self._META_MAP)
        self._log = logging.getLogger(self.__class__.__module__)

    def __init_subclass__(cls, type_name=None, abstract=False, **kwargs):
        super().__init_subclass__(**kwargs)
        if abstract:
            return
        elif type_name is None:
            raise TypeError(
                f"{cls.__name__} does not specify the required class parameter"
                " 'type_name' (its associated PDS4 product type name/mnemonic)"
            )
        cls.type = type_name
        cls._supported_types[type_name] = cls

    def __eq__(self, other: "DataProduct") -> bool:
        return self.meta.lid == other.meta.lid

    def __lt__(self, other: "DataProduct") -> bool:
        return self.meta.lid < other.meta.lid

    def matches(self, other: "DataProduct") -> bool:
        return NotImplemented

    @classmethod
    def from_file(cls, path: Path) -> "DataProduct":
        """Find and instantiate the correct DataProduct subclass from `path`.

        The subclass is determined by the loaded product's type name
        (`//msn:Mission_Information/msn:product_type_name`).

        Args:
            path: Location of the product to be loaded (via `pds4_tools`).

        Returns:
            An object of the subclass applicable to the product at `path`.

        Raises:
            TypeError: If the loaded product does not declare a type, or if its declared
                type does not match that of a registered subclass.
        """
        sl = pds4_tools.read(str(path), lazy_load=True, quiet=True)
        sl.label.default_root = "unmodified"  # allow e.g. `pds:` prefixes to work
        # FIXME: exm-centric; what's a generalised alternative?
        if "msn" not in sl.label.get_namespace_map().values():
            ptype = None
        else:
            ptype = sl.label.find(cls._META_MAP["type"].path)
        if ptype is not None:
            ptype = ptype.text
        else:
            raise TypeError(f"Product loaded from {path.name} does not declare a type")
        if ptype not in cls._supported_types:
            raise TypeError(
                f"Product '{ptype}' loaded from {path} does not match any known type"
            )
        return cls._supported_types[ptype](sl, path)
