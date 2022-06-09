import operator
import sys

import pytest

from proctools.products import ProductDepot, DataProduct

"""
TODO:
  - Test that depot does not trigger DataProduct lazy loading (can mock DataProduct to 
    notify on access).
  - Consider refactoring all `*_invalid_usage_status` into single test which targets 
    methods which employ `_ensure_valid`.
  - Likewise, consider the same for `_ensure_loaded`.
  - Prune local dataset payload files and add to repo
"""


@pytest.fixture(scope="session")
def dataset(datasets):
    return datasets["depot"]


@pytest.fixture(scope="function")
def loaded_depot(dataset):
    d = ProductDepot()
    d.load(dataset.path, recursive=True)
    return d


def test_types(loaded_depot, dataset):
    # GIVEN a loaded depot
    # THEN all encountered product types should be reported
    assert set(loaded_depot.types) == set(dataset.stats["types"].keys())


class TestLoad:
    """
    Note: verification of `load`'s return value (i.e., number of products that were
    loaded) is performed when testing `count` further down.
    """

    @pytest.mark.parametrize(
        "recurse,relation", [(True, operator.eq), (False, operator.lt)]
    )
    def test_load_recursivity(self, dataset, recurse, relation):
        d = ProductDepot()
        # GIVEN products located in a nested directory structure
        nested_dir = dataset.path
        # WHEN the depot is loaded in {,non-}recursive mode
        num_loaded = d.load(nested_dir, recursive=recurse)
        # THEN products from subdirectories should{, not} be loaded
        assert relation(num_loaded, dataset.stats["num_prod"])

    def test_load_multiple(self, dataset):
        d = ProductDepot()
        # GIVEN products located in multiple directories
        dir_1 = dataset.path
        dir_2 = dataset.path / "cdp"  # OK so long as not loading dir_1 recursively
        # WHEN the depot is loaded with both directories
        num_loaded = d.load([dir_1, dir_2], recursive=False)
        # THEN products from all directories should be present
        assert num_loaded == dataset.stats["num_prod"]

    def test_load_consecutive(self, dataset):
        d = ProductDepot()
        # GIVEN products located in separate directories
        dir_1 = dataset.path
        dir_2 = dataset.path / "cdp"  # OK so long as not loading dir_1 recursively
        # WHEN the depot is loaded with each directory consecutively
        num_loaded = d.load(dir_1, recursive=False)
        num_loaded += d.load(dir_2, recursive=False)
        # THEN existing products should be retained between loads
        assert num_loaded == dataset.stats["num_prod"]

    def test_load_rejects_duplicates(self, caplog, dataset):
        d = ProductDepot()
        # GIVEN a depot loaded from a directory
        d.load(dataset.path)
        # WHEN the depot is again instructed to load from the same directory
        # THEN no products should be loaded
        assert d.load(dataset.path) == 0
        # AND a warning should be emitted for each duplicate encountered
        num_dupes = len(
            [rec for rec in caplog.records if "already loaded; ignoring" in rec.message]
        )
        assert num_dupes == dataset.stats["num_prod"]

    def test_load_ignores_invalid(self, caplog, dataset):
        """
        FIXME: log matching is fragile (also matches dupes). Not a major issue, but it
        could complicate debugging if the dataset is poisoned."""
        d = ProductDepot()
        # GIVEN a directory containing invalid product(s)
        # WHEN loading the directory into the depot
        num_loaded = d.load(dataset.path)
        # THEN the invalid product(s) should not be loaded
        assert num_loaded == dataset.stats["num_prod"]
        # AND a warning should be emitted for each invalid encountered
        num_invalid = len(
            [rec for rec in caplog.records if "; ignoring" in rec.message]
        )
        assert num_invalid == dataset.stats["num_invalid"]

    def test_load_follows_symlinks(self, tmp_path, dataset):
        """
        TODO: 'dir is symlink' scenario covered explicitly, but 'subdir is symlink' and
        'file is symlink' scenarios are not. Should verify equivalence or extend
        coverage.
        """
        d = ProductDepot()
        # GIVEN a directory which is a symlink
        sym_dir = tmp_path / "sym"
        sym_dir.symlink_to(dataset.path, target_is_directory=True)
        # WHEN loading the directory into the depot
        num_loaded = d.load(sym_dir)
        # THEN the symlink is resolved and products in the target loaded
        assert num_loaded == dataset.stats["num_prod"]

    def test_load_assigns_usage_status(self, dataset):
        """
        FIXME: don't like relying on `usage_summary` before its tests, but this case
        fits better here as it concerns the behaviour of `load`.
        """
        # GIVEN an empty depot
        d = ProductDepot()
        # WHEN products are loaded
        d.load(dataset.path)
        # THEN their usage status should be set to Status.loaded
        for type_summary in d.usage_summary().values():
            assert set(type_summary) == {
                ProductDepot.Status.loaded,
            }


class TestRetrieve:
    def test_retrieve_all(self, loaded_depot, dataset):
        # GIVEN a loaded depot
        # WHEN an unconstrained (default) retrieve is performed
        retrieved = loaded_depot.retrieve()
        # THEN a dict of product types is returned
        assert isinstance(retrieved, dict)
        # AND this dict contains all loaded types
        assert set(retrieved.keys()) == set(dataset.stats["types"].keys())
        # AND each type in this dict maps to a list of the corresponding products
        for type_, prods in retrieved.items():
            assert isinstance(prods, list)
            assert len(prods) == dataset.stats["types"][type_]

    # @pytest.mark.parametrize("type_,num_expected", dataset.stats["types"].items())
    def test_retrieve_by_type(self, loaded_depot, dataset):  # , type_, num_expected):
        # GIVEN a loaded depot
        for type_, num_expected in dataset.stats["types"].items():
            # WHEN products of a given type are retrieved
            retrieved = loaded_depot.retrieve(type_=type_)
            # THEN a list of the corresponding products is returned
            assert isinstance(retrieved, list)
            assert len(retrieved) == num_expected

    def test_retrieve_by_invalid_type(self, loaded_depot):
        # GIVEN a loaded depot
        # WHEN attempting to retrieve products of a type which does not match a loaded
        # product
        # THEN a KeyError should be raised
        with pytest.raises(KeyError):
            loaded_depot.retrieve(type_="invalid_type")

    def test_retrieve_with_filter(self, loaded_depot):
        """
        FIXME: don't like hardcoding of cam and type. Kluged with fail-guards for now to
        prevent a silent pass in the event that all products of that cam are removed
        from the dataset.
        """
        # GIVEN a loaded depot (where we have ensured, for the purposes of this test,
        # that a type which works with our filter is present...)
        type_ = "observation"
        cam = "WACL"
        if type_ not in loaded_depot.types:
            pytest.fail(
                f"Test requires products of type '{type_}', but none are present in the"
                " provided dataset."
            )
        # WHEN products of a given type are retrieved, filtered by a callable
        def cam_filter(prod):
            # (THEN the filter is provided with a DataProduct instance)
            assert isinstance(prod, DataProduct)
            return prod.meta.camera == cam

        filtered = loaded_depot.retrieve(type_=type_, filter_=cam_filter)
        # THEN the set of retrieved products should be equivalent to a reference set
        # created by manually applying the same filter to an unconstrained retrieve.
        reference = {
            prod.meta.lid
            for prod in loaded_depot.retrieve(type_=type_)
            if cam_filter(prod)
        }
        if len(reference) == 0:
            pytest.fail(
                f"Test requires products of type '{type_}' and cam '{cam}', but none"
                " are present in the provided dataset."
            )
        assert {prod.meta.lid for prod in filtered} == reference

    def test_retrieve_assigns_usage_status(self, loaded_depot):
        """
        FIXME: don't like relying on `usage_summary` before its tests, but same rationale as for `load` above.
        """
        # (A) GIVEN a depot containing products which have not yet been retrieved
        # (i.e., their usage status is Status.loaded)
        # (A) WHEN products are retrieved
        retrieved = loaded_depot.retrieve()
        # (A) THEN their usage status should be set to Status.retrieved
        for type_summary in loaded_depot.usage_summary().values():
            assert set(type_summary) == {
                ProductDepot.Status.retrieved,
            }
        # (B) GIVEN a depot containing products with statuses other than Status.loaded
        # (mark a product of any type as Status.processed)
        type_ = loaded_depot.types[0]
        loaded_depot.mark(retrieved[type_][0], ProductDepot.Status.processed)
        # (B) WHEN such products are retrieved
        _ = loaded_depot.retrieve(type_)
        # (B) THEN their usage status should be retained
        assert ProductDepot.Status.processed in loaded_depot.usage_summary(type_)

    def test_retrieve_by_usage_status(self, loaded_depot, dataset):
        """
        FIXME: don't like relying on `mark` and `usage_summary` before their tests.
        """
        # (A) GIVEN a loaded depot containing multiple products of a given type
        testable_types = [t for t, n in dataset.stats["types"].items() if n > 1]
        type_ = testable_types[0]
        # (A) WHEN products are retrieved by a usage status not held by any product
        processed = loaded_depot.retrieve(
            type_, usage_status=ProductDepot.Status.processed
        )
        # (A) THEN no products should be returned
        assert len(processed) == 0

        # (B) GIVEN products with mixed usage statuses
        # (mark one product of type_ as Status.processed)
        processed_product = loaded_depot.retrieve(type_)[0]
        loaded_depot.mark(processed_product, ProductDepot.Status.processed)
        # (B) WHEN products are retrieved by a given usage status
        processed = loaded_depot.retrieve(
            type_, usage_status=ProductDepot.Status.processed
        )
        # (B) THEN only product(s) of that status should be returned
        assert len(processed) == 1
        assert processed[0] is processed_product

        # (C) WHEN products are retrieved by multiple usage statuses
        statuses = [ProductDepot.Status.retrieved, ProductDepot.Status.processed]
        retrieved_lids = [
            prod.meta.lid
            for prod in loaded_depot.retrieve(type_, usage_status=statuses)
        ]
        # (C) THEN all products matching one of those statuses should be returned
        reference_lids = [
            lid
            for status, lids in loaded_depot.usage_summary(type_).items()
            for lid in lids
            if status in statuses
        ]
        assert len(retrieved_lids) == len(reference_lids)
        assert set(retrieved_lids) == set(reference_lids)

    def test_retrieve_by_invalid_usage_status(self, loaded_depot):
        # GIVEN a loaded depot
        # WHEN attempting to retrieve products by an invalid usage status
        # THEN a TypeError should be raised
        with pytest.raises(TypeError):
            _ = loaded_depot.retrieve(usage_status="invalid_usage_status")


class TestMatch:
    """TODO: add list of lids of matches to stats.json and parametrise on these?"""

    match_type = "rad-flat-prm"
    target_type = "observation"

    def test_match(self, loaded_depot):
        # GIVEN a depot loaded with products of two types, A and B, where A is a
        # general match for B, and assuming the presence of a specific matching A for
        # any present B. (here: we have loaded flats for HRC and both WACs.)
        # WHEN requesting a match of type A for an instance of type B
        target = loaded_depot.retrieve(self.target_type)[0]
        matched = loaded_depot.match(self.match_type, target)
        # THEN a product of type A should be returned
        assert matched is not None
        assert matched.type == self.match_type
        # AND the returned instance should confirm that it is a specific match
        assert matched.matches(target)

    def test_match_missing(self, loaded_depot):
        # GIVEN a depot loaded with products of two types, A and B, where A is a
        # general match for B.
        # WHEN no specific match of type A exists (here: we have released it)
        target = loaded_depot.retrieve(self.target_type)[0]
        candidates = loaded_depot.retrieve(self.match_type)
        for candidate in candidates:
            assert loaded_depot.release(candidate)
        # THEN requesting a match of type A for an instance of type B should yield None
        matched = loaded_depot.match(self.match_type, target)
        assert matched is None

    def test_match_invalid_type(self, loaded_depot):
        # GIVEN a depot loaded with products of type B, but not with products of type A
        # WHEN requesting a match of (the invalid) type A for an instance of type B
        # THEN a KeyError should be raised
        target = loaded_depot.retrieve(self.target_type)[0]
        with pytest.raises(KeyError):
            matched = loaded_depot.match("invalid_type", target)

    def test_match_assigns_usage_status(self, loaded_depot):
        target = loaded_depot.retrieve(self.target_type)[0]
        matched = loaded_depot.match(self.match_type, target)
        lids_of_retrieved = loaded_depot.usage_summary(self.match_type).get(
            ProductDepot.Status.retrieved
        )
        assert lids_of_retrieved is not None
        assert lids_of_retrieved == [matched.meta.lid]


class TestMark:
    @pytest.mark.parametrize("status", ProductDepot.Status)
    def test_mark_assigns_usage_status(self, status, loaded_depot):
        # GIVEN a loaded depot
        # WHEN a given product is marked with a usage status
        # THEN a success should be reported
        type_ = loaded_depot.types[0]
        target = loaded_depot.retrieve(type_)[0]
        assert loaded_depot.mark(target, status) == True
        # AND the product's new usage status should take effect (here: via summary)
        lids_of_status = loaded_depot.usage_summary(type_).get(status)
        assert lids_of_status is not None
        assert target.meta.lid in lids_of_status

    def test_mark_invalid_usage_status(self, loaded_depot):
        # GIVEN a loaded depot
        # WHEN attempting to mark a product with an invalid usage status
        # THEN a TypeError should be raised
        type_ = loaded_depot.types[0]
        target = loaded_depot.retrieve(type_)[0]
        with pytest.raises(TypeError):
            loaded_depot.mark(target, "invalid_usage_status")

    def test_mark_released_product(self, loaded_depot):
        # GIVEN a loaded depot
        # WHEN attempting to mark a product released from the depot with a usage status
        # THEN a success should be reported
        type_ = loaded_depot.types[0]
        target = loaded_depot.retrieve(type_)[0]
        loaded_depot.release(target)
        assert loaded_depot.mark(target, ProductDepot.Status.processed) == True

    def test_mark_foreign_product(self, loaded_depot):
        # GIVEN a loaded depot
        # WHEN attempting to mark a product of a valid type but which has never been
        # loaded into the depot (here: simulated via a mocked LID...)
        # THEN a failure should be reported
        type_ = loaded_depot.types[0]
        target = loaded_depot.retrieve(type_)[0]
        loaded_depot.release(target)
        target.meta.lid = "foreign_lid"
        assert loaded_depot.mark(target, ProductDepot.Status.processed) == False


class TestRelease:
    def test_release(self, loaded_depot):
        """FIXME: relative refcount check does not guarantee absence, just a drop."""
        # GIVEN a loaded depot
        type_ = loaded_depot.types[0]
        count = loaded_depot.count(type_)
        target = loaded_depot.retrieve(type_)[0]
        refcount = sys.getrefcount(target)
        # (A) WHEN requesting the release of a product present in the depot
        # (A) THEN a success should be reported
        assert loaded_depot.release(target) == True
        # (A) AND the product should not be part of any retrieves
        assert target not in loaded_depot.retrieve(type_)
        # (A) AND the depot should drop direct references to the product
        assert sys.getrefcount(target) == refcount - 1

        # (B) WHEN requesting the release of a product no longer present in the depot
        # (B) THEN a failure should be reported
        assert loaded_depot.release(target) == False

        # (C) WHEN requesting the release of a product with an invalid type
        # (C) THEN a KeyError should be raised
        target.type = "invalid_type"
        with pytest.raises(KeyError):
            loaded_depot.release(target)


class TestCount:
    # @pytest.mark.parametrize("type_,num_expected", dataset.stats["types"].items())
    def test_count_by_type(self, loaded_depot, dataset):  # , type_, num_expected):
        # GIVEN a loaded depot
        for type_, num_expected in dataset.stats["types"].items():
            # WHEN requesting a count of products of a given type
            num_counted = loaded_depot.count(type_)
            # THEN and integer should be returned
            assert isinstance(num_counted, int)
            # AND only products of the given type should be counted
            assert num_counted == num_expected

    def test_count_invalid_type(self, loaded_depot):
        # GIVEN a loaded depot
        # WHEN requesting a count of products of a type not present in the depot
        # THEN a KeyError should be raised
        with pytest.raises(KeyError):
            num_counted = loaded_depot.count("invalid_type")

    def test_count_by_usage_status(self, loaded_depot, dataset):
        # GIVEN a loaded depot containing products of different usage statuses
        type_ = loaded_depot.types[0]
        mark = loaded_depot.retrieve(type_)[0]
        assert loaded_depot.mark(mark, ProductDepot.Status.processed)
        # WHEN requesting a count constrained to a given usage status
        # THEN only products of that usage status should be counted
        assert (
            loaded_depot.count(type_, usage_status=ProductDepot.Status.retrieved)
            == dataset.stats["types"][type_] - 1
        )

    def test_count_ignore_released(self, loaded_depot, dataset):
        # GIVEN a loaded depot where products have been released
        type_ = loaded_depot.types[0]
        release = loaded_depot.retrieve(type_)[0]
        assert loaded_depot.release(release)
        # WHEN requesting a count of products in the depot
        # THEN released products should not be counted
        assert (
            loaded_depot.count(type_, ignore_released=True)
            == dataset.stats["types"][type_] - 1
        )


class TestUsageSummary:
    def _assert_well_formed_status_dict(self, statuses: dict, num_expected) -> None:
        # GIVEN a dict of usage statuses and an expected number of mapped products
        assert isinstance(statuses, dict)
        num_lids = 0
        # THEN Status enum values should map to lists of product LIDs
        for status, lids in statuses.items():
            assert status in ProductDepot.Status
            assert isinstance(lids, list)
            # AND the LIDs should be unique strings
            assert all([isinstance(lid, str) for lid in lids])
            assert len(set(lids)) == len(lids)
            num_lids += len(lids)
        # AND the number of LIDs mapped across the statuses agree with expectations
        assert num_lids == num_expected

    def test_usage_summary_all(self, loaded_depot, dataset):
        # GIVEN a loaded depot
        # WHEN an unconstrained (default) usage summary is requested
        summary = loaded_depot.usage_summary()
        # THEN a dict of product types is returned
        assert isinstance(summary, dict)
        # AND all loaded types from the source dataset are present
        assert set(summary.keys()) == set(dataset.stats["types"].keys())
        # AND each type maps to a well-formed dict of usage statuses (cont'd in helper)
        for type_, statuses in summary.items():
            self._assert_well_formed_status_dict(
                statuses, dataset.stats["types"][type_]
            )

    # @pytest.mark.parametrize("type_,num_expected", dataset.stats["types"].items())
    def test_usage_summary_by_type(
        self, loaded_depot, dataset
    ):  # , type_, num_expected):
        # GIVEN a depot loaded with an expected number of products of a target type
        for type_, num_expected in dataset.stats["types"].items():
            # WHEN a usage summary is requested for the type
            statuses = loaded_depot.usage_summary(type_)
            # THEN a well-formed dict of statuses is returned (cont'd in helper)
            self._assert_well_formed_status_dict(statuses, num_expected)
