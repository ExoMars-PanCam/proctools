import datetime
from abc import ABCMeta, abstractmethod, abstractproperty
from collections.abc import Mapping
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import numpy as np
from lxml import etree


T = TypeVar("T")


class ElementParser(Generic[T], metaclass=ABCMeta):
    @abstractproperty
    def type(self) -> Type[T]:
        ...

    @abstractmethod
    def __call__(self, elem: etree._Element) -> T:
        ...

    @staticmethod
    def _strip_attrs_ns(attrib: etree._Attrib) -> Dict[str, str]:
        attrs = {}
        for k, v in attrib.items():
            if k.startswith("{"):
                k = k[k.index("}") + 1 :]
            attrs[k] = v
        return attrs


class TimeParser(ElementParser):
    def __call__(self, elem: etree._Element) -> datetime.time:
        time_string = elem.text.strip()
        try:
            return datetime.datetime.strptime(elem.text.strip(), "%H:%M:%S.%f").time()
        except ValueError as e:
            raise ValueError(f"Invalid time string '{time_string}': {e}") from None

    @property
    def type(self):
        return datetime.time


class UnitParser(ElementParser):
    _instances: Dict[Tuple[Type, str, str], "UnitParser"] = {}
    _units: Dict[str, Dict[str, Union[int, float]]] = {
        "angle": {
            "arcsec": 1 / 3600,
            "arcmin": 1 / 60,
            "deg": 1,
            "hr": 15,
            "mrad": (180 / np.pi) * 1e-3,
            "rad": 180 / np.pi,
        },
        "length": {
            "km": 1e3,
            "m": 1,
            "cm": 1e-2,
            "mm": 1e-3,
            "micrometer": 1e-6,
            "nm": 1e-9,
        },
        "time": {
            "julian day": 86_400,
            "hr": 3600,
            "min": 60,
            "s": 1,
            "ms": 1e-3,
            "microseconds": 1e-6,
            "ns": 1e-9,
        },
    }

    def __new__(cls, type_: Type, domain: str, to_unit: str):
        config = (type_, domain, to_unit)
        if config not in cls._instances:
            super_new = super().__new__
            if super_new is object.__new__:
                cls._instances[config] = super_new(cls)
            else:
                cls._instances[config] = super_new(cls, *config)
        return cls._instances[config]

    def __init__(self, type_: Type, domain: str, to_unit: str):
        if domain not in self._units:
            raise ValueError(
                f"Invalid domain '{domain}'; expected one of"
                f" {tuple(self._units.keys())}"
            )
        if to_unit not in self._units[domain]:
            raise ValueError(
                f"Invalid unit '{to_unit}'; expected one of"
                f" {tuple(self._units[domain].keys())}"
            )
        self._type = type_
        self._domain = domain
        self._unit = to_unit
        self._factors = self._units[domain]

    @property
    def type(self):
        return self._type

    @property
    def domain(self):
        return self._domain

    @property
    def unit(self):
        return self._unit

    def __call__(self, elem: etree._Element):
        val = self._type(elem.text)
        unit_in = self._strip_attrs_ns(elem.attrib).get("unit", None)
        if unit_in is not None:
            val *= self._factors[unit_in] / self._factors[self._unit]
        return val


class MetaElement(Generic[T]):
    def __init__(
        self,
        monikers: Union[str, Sequence[str]],
        parser: Union[
            ElementParser[T], Callable[[str], T], Tuple[Callable[[str], T], Type[T]]
        ] = str,
        ns: Optional[str] = None,
        path: Optional[Union[str, Sequence[str]]] = None,
    ):
        if isinstance(parser, Tuple):
            self._parser = parser[0]
            self._type: Type[T] = parser[1]
        else:
            self._parser = parser
            self._type: Type[T] = self._infer_type(parser)
        if isinstance(monikers, str):
            monikers = (monikers,)
        elif isinstance(monikers, Sequence) and all(
            (isinstance(m, str) for m in monikers)
        ):
            monikers = tuple(monikers)
            if len(monikers) > len(set(monikers)):
                raise ValueError(f"Duplicate monikers provided: {monikers}")
        else:
            raise TypeError(
                f"Monikers must be a string or sequence thereof; got {monikers}"
                f" ({type(monikers)})"
            )
        self.monikers = monikers
        self.prefix = self._sanitize_prefix(ns)
        self._path = None
        if path is not None:
            self.path = path

    @property
    def path(self):
        if self._path is None:
            raise RuntimeError("Meta element has not been assigned a path.")
        return self._path

    @path.setter
    def path(self, path: Union[str, Sequence[str]]):
        if isinstance(path, str):
            if self.prefix:
                raise TypeError(
                    f"Only segmented paths can be used when an NS prefix has been"
                    f" specified"
                )
            self._path = path
        elif isinstance(path, Sequence) and all((isinstance(seg, str) for seg in path)):
            self._path = self._assemble(path)
        else:
            raise TypeError(f"Expected string or sequence thereof; got {type(path)}")

    def parse(self, elem: etree._Element) -> Optional[T]:
        if isinstance(self._parser, ElementParser):
            return self._parser(elem)
        return (
            None if elem.text is None else self._parser(elem.text)
        )  # FIXME: .strip()?

    @property
    def type(self) -> Type[T]:
        return self._type

    def _assemble(self, path_segments: Sequence[str]) -> str:
        return f".//{self.prefix}{f'/{self.prefix}'.join(path_segments)}"

    @staticmethod
    def _sanitize_prefix(pre: Optional[str]) -> str:
        if pre is None:
            return ""
        if not isinstance(pre, str):
            raise TypeError(f"NS prefix must be a string; got {type(pre)}")
        if not pre.endswith(":"):
            return f"{pre}:"
        return pre

    def _infer_type(self, obj: Union[ElementParser, Callable[[str], T]]) -> Type[T]:
        if isinstance(obj, ElementParser):
            return obj.type
        if isinstance(obj, type):
            return obj
        self_ = getattr(obj, "__self__", None)
        if self_ is None:
            raise TypeError(
                f"Unable to infer target type for parser '{obj}' ({type(obj)}); please"
                " specify via alternate argument format (see init)"
            )
        if isinstance(self_, type):
            return self_
        return self_.__class__


class MetaMap(Mapping):
    def __init__(self, paths_to_elems: Dict[str, Any]) -> None:
        self._attrs: Dict[str, MetaElement] = {}
        self._extract_elems(paths_to_elems, self._attrs)

    def __getitem__(self, moniker: str) -> MetaElement:
        return self._attrs.__getitem__(moniker)

    def __setitem__(self, moniker: str, attr: MetaElement):
        if not isinstance(attr, MetaElement):
            raise TypeError(f"Expected MetaElement instance, got {type(attr)}")
        self._attrs.__setitem__(moniker, attr)

    def __iter__(self):
        return iter(self._attrs)

    def __len__(self):
        return len(self._attrs)

    def extend(self, updates: dict, overload: bool = False) -> "MetaMap":
        """Create a new MetaMap as the union of self and `updates`.

        Conflicting element monikers (i.e., keys) will raise KeyErrors unless `overload`
        is True.


        """
        new = self.__class__(updates)
        for moniker in self:
            if moniker in new:
                orig, ext = self[moniker], new[moniker]
                if not overload:
                    raise RuntimeError(
                        f"Moniker conflict encountered for '{moniker}'."
                        f" Original: {orig._type} @ '{orig.path}';"
                        f" Conflict: {ext._type} @ '{ext.path}'"
                    )
                if not all((m in ext.monikers for m in orig.monikers)):
                    raise ValueError(
                        f"Illegal moniker overload for '{moniker}': the extending"
                        " MetaElement does not cover all of the original's monikers:"
                        f" Original: {orig.monikers} ({orig._type} @ '{orig.path}');"
                        f" Extending: {ext.monikers} ({ext._type} @ '{ext.path}')"
                    )
            else:
                new[moniker] = self[moniker]
        return new

    @staticmethod
    def _extract_elems(
        v: Union[dict, MetaElement],
        dest: Dict[str, MetaElement],
        path: Optional[List[str]] = None,
    ):
        if path is None:
            path = []
        if isinstance(v, dict):
            for k, vv in v.items():
                MetaMap._extract_elems(vv, dest, path + [str(k)])
        elif isinstance(v, MetaElement):
            v.path = path
            for moniker in v.monikers:
                if moniker in dest:
                    raise RuntimeError(
                        f"Multiple MetaElements claim the moniker '{moniker}':"
                        f" '{v.path}' vs '{dest[moniker].path}'"
                    )
                dest[moniker] = v
        else:
            raise TypeError(f"Invalid leaf node type encountered: '{type(v)}'")


class LabelMeta:
    """Single-layer XML element lookup based on path monikers.

    Takes an XPath evaluator for a label, together with a moniker->MetaElement mapping
    for elements of interest. Allows two forms of access:

    Subscript notation. Label elements can be retrieved by their moniker (e.g.,
    `label_meta["moniker"]`), which will evaluate the corresponding MetaElement's
    xpath and return any element objects found. Assignment via subscript notation is not
    supported.

    Attributes. The provided monikers are presented as attributes of this class (e.g.,
    `label_meta.moniker`). When reading a moniker attribute, it's value will be resolved
    as the text property of any element objects found, cast to the type specified by the
    corresponding MetaElement. When setting a moniker attribute, the value must be an
    instance of the aforementioned type; assignment will fail if multiple label elements
    exist at a given moniker's MetaElement's xpath.

    Attributes:
        All monikers provided at initialisation (see __init__ for details).
    """

    def __init__(
        self,
        xpath: Union[etree.XPathDocumentEvaluator, etree.XPathElementEvaluator],
        meta_map: MetaMap,
    ):
        """Expose a label's elements by their monikers.

        Args:
            xpath: lxml XPath evaluator instance (i.e., bound to an XML label).
            meta_map: moniker->MetaElement mapping; keys are exposed as attributes on
                this class.
        """
        self._xpath = xpath
        self._map = meta_map

    def __contains__(self, moniker: str) -> bool:
        return moniker in self._map

    def __getitem__(self, moniker: str) -> str:
        res = self._get(moniker, cast=False)
        if isinstance(res, List):
            return res[0]  # FIXME: questionable strategy?
        return res

    def __setitem__(self, moniker: str, val: str):
        if not isinstance(val, str):
            raise TypeError(
                f"Subscript assignment only supported for strings; got '{type(val)}'"
            )
        self._set(moniker, val, cast=False)

    def __getattr__(self, moniker: str) -> Any:
        return self._get(moniker, cast=True)

    def __setattr__(self, moniker: str, val: Any) -> None:
        if moniker.startswith("_"):
            return super().__setattr__(moniker, val)
        self._set(moniker, val, cast=True)
        # meta = self._resolve(moniker)
        # if not isinstance(val, meta._type):
        #     raise TypeError(
        #         f"Meta element '{moniker}' should be of type {meta._type}; got"
        #         f" {type(val)}"
        #     )
        # elems = self._retrieve(meta.path)
        # if len(elems) > 1:
        #     raise TypeError(
        #         f"Multiple assignment not supported (label contains {len(elems)}"
        #         f" elements at '{meta.path}')"
        #     )
        # elems[0].text = str(val)

    def _get(self, m: str, cast: bool) -> Any:
        meta = self._resolve(m)
        vals = [
            (meta.parse(elem) if cast else elem.text)
            for elem in self._retrieve(meta.path)
        ]
        return vals if len(vals) > 1 else vals[0]

    def _set(self, m: str, val: Any, cast: bool):
        meta = self._resolve(m)
        if cast and not isinstance(val, meta._type):
            raise TypeError(
                f"Meta element '{m}' should be of type {meta._type}; got {type(val)}"
            )
        elems = self._retrieve(meta.path)
        if len(elems) > 1:
            raise RuntimeError(
                f"Multiple assignment not supported (label contains {len(elems)}"
                f" elements at '{meta.path}')"
            )
        elems[0].text = str(val) if cast else val

    def _resolve(self, moniker: str) -> MetaElement:
        meta = self._map.get(moniker, None)
        if meta is None:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{moniker}'"
            )
        return meta

    def _retrieve(self, path: str) -> List[etree._Element]:
        elems = self._xpath(path)
        if not elems:
            raise AttributeError(f"Label has no element '{path}'")
        return elems
