import logging
from pathlib import Path
from typing import List, Optional
from xml.parsers.expat import ExpatError

from . import DataProduct


class ProductLoader:
    """PDS4 product loader and manager.

    This class keeps track of whether a loaded product has been requested (used). A
    report of unused products can be produced via `log_unused()`.
    """

    def __init__(self):
        self._initialised = False
        self._log = logging.getLogger(__name__)
        self._product_map = {}
        self._usage_map = {}

    def load_products(self, directory: Path, recursive: bool = True) -> None:
        """Load all valid PDS4 products from a given directory.

        A product is considered valid if it defines a product type and that type matches
        one supported by a `DataProduct` subclass.

        Args:
            directory: Path to a directory in which to search for products.
            recursive: Search recursively in `directory`.

        """
        search = directory.rglob if recursive else directory.glob
        for path in search("*.xml"):
            try:
                dp = DataProduct.from_file(path)
            except (TypeError, ExpatError) as e:
                self._log.warning(f"{e}; ignoring")
            else:
                if dp.type not in self._product_map:
                    self._product_map[dp.type] = []
                self._product_map[dp.type].append(dp)
        for products in self._product_map.values():
            products.sort()  # ensure self.next works in sorting order
        for type_, products in self._product_map.items():
            self._usage_map[type_] = [False] * len(products)
        self._initialised = True

    def all(self, type_: str):
        """Retrieve all loaded products of `type_`.

        Args:
            type_: Product type to retrieve all instances of (regardless of whether
                they have been previously retrieved or not).

        Returns:
            All loaded products of `type_`.

        Raises:
            RuntimeError: If `self.load_products` has not been called
            KeyError: If no `type_` products have been loaded.
        """
        self._ensure_valid_type(type_)
        self._usage_map[type_][:] = [True] * len(self._usage_map[type_])
        return self._product_map[type_]

    def next(self, type_: str) -> Optional[DataProduct]:
        """Retrieve the next unused product of type `type_`.

        Products are retrieved in their sorted order (i.e. how their type's class would
        naturally sort them).

        Args:
            type_: Product type to retrieve next unused instance of.

        Returns:
            The next unused data product or None if none remain.
        Raises:
            RuntimeError: If `self.load_products` has not been called.
            KeyError: If no `type_` products have been loaded.
        """
        self._ensure_valid_type(type_)
        self._ensure_initialised()
        try:
            idx = self._usage_map[type_].index(False)
        except ValueError:
            return None
        self._usage_map[type_][idx] = True
        return self._product_map[type_][idx]

    def find_applicable(
        self, type_: str, product: DataProduct
    ) -> Optional[DataProduct]:
        """Find the first candidate product of type `type_` applicable to `product`.

        Candidates are searched in their sorted order (i.e. how their type's class would
        naturally sort them).

        Note:
            `type_` candidates' `.is_applicable()` must be compatible with `product`.

        Args:
            type_: Product type to search for.
            product: Target product to present to candidates.

        Returns:
            The matching data product or None if no applicable product of `type_` was
            found.
        Raises:
            RuntimeError: If `self.load_products` has not been called.
            KeyError: If no `type_` products have been loaded.
        """
        self._ensure_initialised()
        self._ensure_valid_type(type_)
        for idx, candidate in enumerate(self._product_map[type_]):
            if candidate.is_applicable(product):
                break
        else:
            return None
        self._usage_map[type_][idx] = True
        return self._product_map[type_][idx]

    def find_all_applicable(
        self, type_: str, product: DataProduct
    ) -> Optional[List[DataProduct]]:
        raise NotImplementedError

    def log_unused(self, warning: bool = True) -> None:
        """Produce a log record for each unused loaded product.

        Args:
            warning: If True, issue warnings, else issue info-level log records.
        """
        log = self._log.warning if warning else self._log.info
        self._ensure_initialised()
        for type_, usage in self._usage_map.items():
            for idx, used in enumerate(usage):
                if used:
                    continue
                product_lid = self._product_map[type_][idx].meta.lid
                log(f"Product loaded but never used: {product_lid}")

    def _ensure_initialised(self) -> None:
        if not self._initialised:
            raise RuntimeError("No products have been loaded")

    def _ensure_valid_type(self, type_: str) -> None:
        if type_ not in self._product_map:
            raise KeyError(f"No products of type '{type_}' have been loaded")
