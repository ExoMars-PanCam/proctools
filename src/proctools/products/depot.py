import logging
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union
from xml.parsers.expat import ExpatError

from . import DataProduct


class ProductDepot:
    """DataProduct directory loader, product type organiser and usage tracker.

    Loaded products are grouped by type, and a record is kept of which products have
    been previously retrieved (used).

    Attributes:
        types: A list of the types of products that have been loaded into in the depot.
    """

    def __init__(self):
        self._log = logging.getLogger(__name__)
        self._products: Dict[str, List[DataProduct]] = defaultdict(list)
        self._used: Dict[str, List[bool]] = defaultdict(list)

    @property
    def types(self) -> List[str]:
        return list(self._products.keys())

    def load(
        self,
        directory: Union[Path, List[Path]],
        recursive: bool = True,
        reject_duplicates: bool = True,
    ) -> int:
        """Load all valid PDS4 products from one or more directories.

        A product is considered valid if its label declares an `msn:product_type_name`
        supported by a registered `DataProduct` subclass.

        Args:
            directory: Path or list of paths to directories in which to search for
                products. Symbolic links are followed.
            recursive: Search for products recursively.
            reject_duplicates: Omit products that are already in the depot.

        Returns:
            The number of successfully loaded products across all types.
        """
        if not isinstance(directory, list):
            directory = [directory]
        num_loaded = 0
        products = self._products
        used = self._used
        for dir_ in directory:
            self._log.debug(f"Loading products from '{dir_.name}'")
            glob = dir_.expanduser().rglob if recursive else dir_.expanduser().glob
            for path in glob("*.xml"):
                try:
                    product = DataProduct.from_file(path)
                except (TypeError, ExpatError) as e:
                    self._log.warning(f"{e}; ignoring")
                    continue
                type_ = product.type
                if (
                    reject_duplicates
                    and type_ in products
                    and product in products[type_]
                ):
                    self._log.warning(f"'{product.meta.lid}' already loaded; ignoring")
                    continue
                products[type_].append(product)
                used[type_].append(False)
                num_loaded += 1
        for type_ in products:
            # keep products sorted by their type's defined order (e.g., acq. time)
            # co-sort the maps to preserve correspondence across multiple loads
            products[type_], used[type_] = (  # type: ignore
                list(t)
                for t in zip(
                    *sorted(
                        zip(products[type_], used[type_]),
                        key=lambda v: v[0],
                    )
                )
            )
        return num_loaded

    def retrieve(
        self,
        type_: Optional[str] = None,
        filter_: Optional[Callable[[DataProduct], bool]] = None,
        mark_used: bool = True,
        unused: bool = True,
        used: bool = True,
    ) -> Union[List[DataProduct], Dict[str, List[DataProduct]]]:
        """Return all products in the depot, optionally of a given type or usage status.

        Args:
            type_: Restrict the retrieval to products of a given type.
            filter_: Only consider products for which filter_(product) is True.
            mark_used: Record retrieved products as used.
            unused: Consider previously unused products for retrieval.
            used: Consider previously used products for retrieval.

        Returns:
            A sorted list of retrieved products if `type_` is given, else a dictionary
            mapping the name of each loaded type to its list of products.

        Raises:
            KeyError: If the depot has never been loaded with products of `type_`.
            ValueError: If both `unused` and `used` are False (no products to retrieve).
        """
        if not unused and not used:
            raise ValueError("Cannot simultaneously omit both unused and used products")
        if type_ is not None:
            self._ensure_loaded(type_)
        selection = defaultdict(list)
        for prod_type in [type_] if type_ is not None else self.types:
            for prod_idx, prod_used in enumerate(self._used[prod_type]):
                if (not prod_used and not unused) or (prod_used and not used):
                    continue
                prod = self._products[prod_type][prod_idx]
                if filter_ is not None and not filter_(prod):
                    continue
                selection[prod_type].append(prod)
                if not prod_used and mark_used:
                    self._used[prod_type][prod_idx] = True
        return selection if type_ is None else selection[type_]

    def count(self, type_: str, unused: bool = True, used: bool = True) -> int:
        """Return the number of products in the depot of a given type and usage status.

        Args:
            type_: Product type to count instances of.
            unused: Count products marked as unused.
            used: Count products marked as used.

        Returns:
            The number of `type_` products matching the usage criterium.

        Raises:
            KeyError: If the depot has never been loaded with products of `type_`.
            ValueError: If both `unused` and `used` are False (no products to count).
        """
        self._ensure_loaded(type_)
        if not unused and not used:
            raise ValueError("Cannot simultaneously omit both unused and used products")
        if unused and used:
            return len(self._used[type_])
        return self._used[type_].count(used)  # left w/XOR, so !used implies unused

    def next(self, type_: str) -> Optional[DataProduct]:
        """Return the next unused product belonging to `type_`, and record it as used.

        Retrieval order is dictated by the class associated with `type_`; see
        `DataProduct` for more information.

        Args:
            type_: Product type to retrieve.

        Returns:
            The next unused product of `type_` if one remains, else None.

        Raises:
            KeyError: If the depot has never been loaded with products of `type_`.
        """
        self._ensure_loaded(type_)
        try:
            idx = self._used[type_].index(False)
        except ValueError:
            return None
        self._used[type_][idx] = True
        return self._products[type_][idx]

    def match(self, type_: str, product: DataProduct) -> Optional[DataProduct]:
        """Find and return a product of `type_` which is a match for `product`.

        Search order and matching criteria are dictated by the class associated with
        `type_`; see `DataProduct` for more information.

        If a match is found, it will be marked as used, however, the usage status of
        prospective matches is not considered (i.e., repeat calls will yield the same
        match).

        Args:
            type_: Product type to consider when searching for a match.
            product: Target product to present to prospective matches.

        Returns:
            The first instance of `type_` that matches `product` if one exists, else
            None.

        Raises:
            KeyError: If the depot has never been loaded with products of `type_`.
        """
        self._ensure_loaded(type_)
        for idx, candidate in enumerate(self._products[type_]):
            if candidate.matches(product):
                break
        else:
            return None
        self._used[type_][idx] = True
        return candidate

    def release(self, product: DataProduct) -> bool:
        """Remove (any references to) `product` from the depot.

        Args:
            product: The `DataProduct` instance which should be released.

        Returns:
            True if `product` is found and released, else False.

        Raises:
            KeyError: If the depot has never been loaded with products of `product.type`.
        """
        type_ = product.type
        self._ensure_loaded(type_)
        try:
            idx = self._products[type_].index(product)
        except ValueError:
            return False
        self._products[type_].pop(idx)
        self._used[type_].pop(idx)
        return True

    def _ensure_loaded(self, type_: str):
        if type_ not in self._products:
            raise KeyError(
                f"Depot has not been loaded with any products of type '{type_}'"
            )
