import logging
import enum
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Union
from xml.parsers.expat import ExpatError

from . import DataProduct


class ProductDepot:
    """DataProduct directory loader, product type organiser and usage status tracker.

    Loaded products are grouped by type, and retrieval of products from the depot can
    be constrained by type, usage status or a supplied filter.

    The depot keeps ProductDepot.Status usage records for all loaded products. A
    product's status is automatically updated when it is selected for retrieval, but
    clients can also manually update a given product's status, e.g. to reflect
    successful or failed processing. A summary of the usage statuses of the depot's
    products can be generated, e.g. for logging purposes.

    Attributes:
        types: A list of the types of products that have been loaded into in the depot.
        Status: Enum used to mark the usage status of products in the depot.
    """

    class Status(enum.Enum):
        loaded = enum.auto()
        retrieved = enum.auto()
        processed = enum.auto()
        failed = enum.auto()
        rejected = enum.auto()

        def __str__(self):
            return self.name

    def __init__(self):
        self._log = logging.getLogger(__name__)
        self._products: Dict[str, List[DataProduct]] = defaultdict(list)
        self._usage: Dict[str, Dict[str, ProductDepot.Status]] = defaultdict(dict)

    @property
    def types(self) -> List[str]:
        return list(self._products.keys())

    def load(
        self,
        directory: Union[Path, List[Path]],
        recursive: bool = True,
    ) -> int:
        """Load all valid PDS4 products from one or more directories.

        A product is considered valid if its label declares a type - via
        `msn:product_type_name` - which is supported by a registered `DataProduct`
        subclass.

        If a product is found to be identical to one already loaded into the depot, it
        will be rejected. A given product type's notion of equality can be overridden by
        its `DataProduct` subclass, but it is generally assumed to at least involve a
        LID comparison.

        Args:
            directory: Path or list of paths to directories in which to search for
                products. Symbolic links are followed.
            recursive: Search for products recursively.

        Returns:
            The number of products successfully loaded from `directory`.
        """
        if not isinstance(directory, Sequence):
            directory = [directory]
        num_loaded = 0
        products = self._products
        usage = self._usage
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
                    type_ in products
                    and product in products[type_]  # assume DP sub impl sensible eq
                ):
                    self._log.warning(f"'{product.meta.lid}' already loaded; ignoring")
                    continue
                products[type_].append(product)
                usage[type_][product.meta.lid] = self.Status.loaded
                num_loaded += 1
        for type_ in products:
            products[type_].sort()
        return num_loaded

    def retrieve(
        self,
        type_: Optional[str] = None,
        filter_: Optional[Callable[[DataProduct], bool]] = None,
        usage_status: Optional[Union[Status, Sequence[Optional[Status]]]] = None,
    ) -> Union[List[DataProduct], Dict[str, List[DataProduct]]]:
        """Retrieve products from the depot, optionally by type, usage status or filtered.

        Returned products with usage Status.loaded will automatically have this updated
        to Status.retrieved.

        Args:
            type_: Restrict the retrieval to products of a given type name.
            filter_: Only consider products for which filter_(product) is True.
            usage_status: Only consider products with a given Usage status or statuses.

        Returns:
            A sorted list of retrieved products if `type_` is given, else a dictionary
            mapping the name of each loaded type to its list of products.

        Raises:
            KeyError: If the depot has never been loaded with products of `type_`.
            TypeError: In the event that `usage_status` is not a member of Status
                (or a Sequence thereof).
        """
        if type_ is not None:
            self._ensure_loaded(type_)
        if usage_status is not None:
            if not isinstance(usage_status, Sequence):
                usage_status = [usage_status]
            for _us in usage_status:
                self._ensure_valid(_us)
        selection = defaultdict(list)
        for prod_type in [type_] if type_ is not None else self.types:
            for prod in self._products[prod_type]:
                prod_lid = prod.meta.lid
                prod_status = self._usage[prod_type][prod_lid]
                if usage_status is not None and prod_status not in usage_status:
                    continue
                if filter_ is not None and not filter_(prod):
                    continue
                if prod_status == self.Status.loaded:
                    self._usage[prod_type][prod_lid] = self.Status.retrieved
                selection[prod_type].append(prod)
        return selection if type_ is None else selection[type_]

    def match(self, type_: str, product: DataProduct) -> Optional[DataProduct]:
        """Find and return a product of `type_` which is a match for `product`.

        Search order and matching criteria are dictated by the class associated with
        `type_`; see `DataProduct` for more information.

        Matched products with usage Status.loaded will automatically have this updated
        to Status.retrieved.

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
        for candidate in self._products[type_]:
            if candidate.matches(product):
                lid = candidate.meta.lid
                if self._usage[type_][lid] == self.Status.loaded:
                    self._usage[type_][lid] = self.Status.retrieved
                return candidate
        return None

    def mark(self, product: DataProduct, usage_status: Status) -> bool:
        """Assign a `usage_status` to a `product`.

        Args:
            product: The DataProduct instance which should be marked.
            usage_status: The usage Status which should be assigned to `product`.

        Returns:
            True if `product` is found and marked, else False.

        Raises:
            KeyError: If the depot has never been loaded with products of `product.type`.
            TypeError: In the event that `usage_status` is not a member of Status.
        """
        type_ = product.type
        self._ensure_loaded(type_)
        lid = product.meta.lid
        if lid not in self._usage[type_]:
            return False
        self._ensure_valid(usage_status)
        self._usage[type_][lid] = usage_status
        return True

    def release(self, product: DataProduct) -> bool:
        """Remove direct references to `product` from the depot.

        Note that while this method - intended to allow clients to manage space
        complexity - deletes the depot's reference to the `product` object itself, its
        associated usage status is still preserved (as this is an indirect reference
        mapped by LID).

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
            self._products[type_].remove(product)
        except ValueError:
            return False
        return True

    def count(
        self,
        type_: str,
        usage_status: Optional[Status] = None,
        ignore_released: bool = False,
    ) -> int:
        """Return the number of products in the depot of a given type and usage status.

        Args:
            type_: The product type to count instances of.
            usage_status: Only count products of a given Status.
            ignore_released: Don't count products that have been released from the depot.

        Returns:
            The number of `type_` products matching the `usage_status`.

        Raises:
            KeyError: If the depot has never been loaded with products of `type_`.
            TypeError: In the event that `usage_status` is not a member of Status.
        """
        self._ensure_loaded(type_)
        prods = self._products[type_]
        usage = self._usage[type_]
        if usage_status is None:
            return len(prods) if ignore_released else len(usage)
        self._ensure_valid(usage_status)
        if ignore_released:
            return len([p for p in prods if usage[p.meta.lid] == usage_status])
        return len([s for s in usage.values() if s == usage_status])

    def usage_summary(
        self, type_: Optional[str] = None
    ) -> Union[Dict[Status, Sequence[str]], Dict[str, Dict[Status, Sequence[str]]]]:
        """Return a summary of the usage statuses of the depot's products.

        Args:
            type_: Restrict the summary to products of a given type name.

        Returns:
            A dictionary mapping usage statuses to product LIDs if `type_` is given,
            else a dictionary mapping the name of each loaded type to its status map.

        Raises:
            KeyError: If the depot has never been loaded with products of `type_`.
        """
        if type_ is not None:
            self._ensure_loaded(type_)
        summary = defaultdict(lambda: defaultdict(list))
        for prod_type in [type_] if type_ is not None else self.types:
            for prod_lid, prod_status in self._usage[prod_type].items():
                summary[prod_type][prod_status].append(prod_lid)
        return summary if type_ is None else summary[type_]  # type: ignore

    def _ensure_loaded(self, type_: str):
        if type_ not in self._products:
            raise KeyError(
                f"Depot has not been loaded with any products of type '{type_}'"
            )

    def _ensure_valid(self, usage_status: any):
        if not isinstance(usage_status, ProductDepot.Status):
            raise TypeError(
                f"usage status '{usage_status}' is not a member of ProductDepot.Status"
            )
