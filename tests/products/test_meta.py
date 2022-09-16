from lxml import etree
import pytest

from proctools.products.meta import LabelMeta, MetaElement, MetaMap, UnitParser


# @pytest.fixture(
#     scope="class",
#     params=[
#         ("km", 1e3),
#         ("m", 1e0),
#         ("cm", 1e-2),
#         ("mm", 1e-3),
#         ("micrometer", 1e-6),
#         ("nm", 1e-9),
#     ],
# )
# def units_of_length(request):
#     return request.params

units_of_length = (
    ("km", 1e3),
    ("m", 1e0),
    ("cm", 1e-2),
    ("mm", 1e-3),
    ("micrometer", 1e-6),
    ("nm", 1e-9),
)


# @pytest.fixture(
#     scope="class",
#     params=[
#         ("julian day", 86_400),
#         ("hr", 3600),
#         ("min", 60),
#         ("s", 1),
#         ("ms", 1e-3),
#         ("microseconds", 1e-6),
#         ("ns", 1e-9),
#     ],
# )
# def units_of_time(request):
#     return request.params

units_of_time = (
    ("julian day", 86_400),
    ("hr", 3600),
    ("min", 60),
    ("s", 1),
    ("ms", 1e-3),
    ("microseconds", 1e-6),
    ("ns", 1e-9),
)


class TestUnitParser:
    def test_attributes(self):
        up = UnitParser(float, "length", "m")
        assert up.type is float
        assert up.domain == "length"
        assert up.unit == "m"

    def test_memoization(self):
        up_len_m = UnitParser(float, "length", "m")
        assert up_len_m is UnitParser(float, "length", "m")
        assert up_len_m is not UnitParser(int, "length", "m")
        assert up_len_m is not UnitParser(float, "length", "mm")
        up_time_s = UnitParser(float, "time", "s")
        assert up_time_s is UnitParser(float, "time", "s")
        assert up_time_s is not UnitParser(int, "time", "s")
        assert up_time_s is not UnitParser(float, "time", "ms")

    @pytest.mark.parametrize("unit_in, factor_in", units_of_length)
    @pytest.mark.parametrize("unit_out, factor_out", units_of_length)
    def test_parse_domain_length(self, unit_in, factor_in, unit_out, factor_out):
        elem = etree.Element("foo", {"{http://foo.ns}unit": unit_in}, nsmap=None)
        elem.text = "42.13"
        parser = UnitParser(float, "length", unit_out)
        parsed = parser(elem)
        assert isinstance(parsed, parser.type)
        assert parsed == pytest.approx(42.13 * factor_in / factor_out)

    @pytest.mark.parametrize("unit_in, factor_in", units_of_time)
    @pytest.mark.parametrize("unit_out, factor_out", units_of_time)
    def test_parse_domain_time(self, unit_in, factor_in, unit_out, factor_out):
        elem = etree.Element("foo", {"{http://foo.ns}unit": unit_in}, nsmap=None)
        elem.text = "42.13"
        parser = UnitParser(float, "time", unit_out)
        parsed = parser(elem)
        assert isinstance(parsed, parser.type)
        assert parsed == pytest.approx(42.13 * factor_in / factor_out)

    def test_invalid_input(self):
        elem = etree.Element("foo")
        elem.text = "invalid"
        with pytest.raises(ValueError, match="invalid literal"):
            UnitParser(int, "length", "m")(elem)

    def test_invalid_domain(self):
        with pytest.raises(ValueError, match="Invalid domain"):
            UnitParser(int, "invalid", "m")

    def test_invalid_unit(self):
        with pytest.raises(ValueError, match="Invalid unit"):
            UnitParser(int, "length", "invalid")


class TestMetaElement:
    @pytest.mark.parametrize(
        "p, T", ((str, str), (int, int), ((lambda s: s, str), str))
    )
    def test_type(self, p, T):
        m = MetaElement("foo", parser=p)
        assert m._type is T

    @pytest.mark.parametrize(
        "text, type_", (("bar", str), ("42", int), ("13.37", float))
    )
    def test_parser_implicit(self, text, type_):
        elem = etree.Element("foo")
        elem.text = text
        m = MetaElement("m", parser=type_)
        parsed = m.parse(elem)
        assert isinstance(parsed, type_)
        assert parsed == type_(text)

    def test_parser_explicit(self):
        def int_func(s):
            return int(s)

        float_func = lambda s: float(s)

        for ref, p in (("42", (int_func, int)), ("13.37", (float_func, float))):
            elem = etree.Element("foo")
            elem.text = ref
            m = MetaElement("m", parser=p)
            assert m._type is p[1]
            parsed = m.parse(elem)
            assert isinstance(parsed, p[1])
            assert parsed == p[1](ref)

    @pytest.mark.parametrize(
        "text, unit, parser",
        (
            ("42", "s", UnitParser(float, "time", "s")),
            ("13.37", "m", UnitParser(float, "length", "m")),
        ),
    )
    def test_parser_ElementParser(self, text, unit, parser):
        elem = etree.Element("foo", {"{http://foo.ns}unit": unit}, nsmap=None)
        elem.text = text
        m = MetaElement("m", parser=parser)
        print(m._type)
        print(parser.type)
        assert m._type is parser.type
        parsed = m.parse(elem)
        assert isinstance(parsed, parser.type)
        assert parsed == parser.type(text)

    def test_parser_underspecified(self):
        with pytest.raises(TypeError):
            MetaElement("m", parser=lambda s: s)

        def func(s):
            return int(s)

        with pytest.raises(TypeError):
            MetaElement("m", parser=func)

    def test_moniker(self):
        moniker = "foo"
        m = MetaElement(moniker)
        assert m.monikers == (moniker,)

    @pytest.mark.parametrize(
        "monikers", (("foo",), ("foo", "bar"), ("foo", "bar", "baz"))
    )
    @pytest.mark.parametrize("type_", (tuple, list))
    def test_monikers(self, monikers, type_):
        monikers = type_(monikers)
        m = MetaElement(monikers)
        assert m.monikers == tuple(monikers)

    def test_monikers_rejects_dupes(self):
        with pytest.raises(ValueError):
            m = MetaElement(("foo", "foo"))

    @pytest.mark.parametrize("reject", (1, ("foo", 2)))
    def test_monikers_rejects_non_strings(self, reject):
        with pytest.raises(TypeError):
            m = MetaElement(reject)

    def test_path_is_sequence(self):
        segments = ["one", "two"]
        m1 = MetaElement("m", path=segments)
        assert isinstance(m1.path, str)
        assert all(c in m1.path for c in segments)
        assert m1.path.endswith(segments[-1])
        m2 = MetaElement("m")
        m2.path = segments
        assert m2.path == m1.path

    def test_path_is_string(self):
        # Accept string-paths via init...
        path = ".//pds:one/pds:two"
        m = MetaElement("m", path=path)
        assert m.path == path
        # ...and via property setter
        m = MetaElement("m")
        m.path = path
        assert m.path == path
        # Reject string paths and prefix used together
        with pytest.raises(TypeError):
            m = MetaElement("m", ns="foo", path=path)

    @pytest.mark.parametrize("reject", (1, ("one", 2)))
    def test_path_rejects_non_strings(self, reject):
        with pytest.raises(TypeError):
            m = MetaElement("m", path=reject)

    def test_prefix(self):
        pre = "pds"
        pre_delim = f"{pre}:"
        segments = ("one", "two", "three")
        m1 = MetaElement("m", ns=pre, path=segments)
        assert m1.path.count(pre_delim) == len(segments)
        m2 = MetaElement("m", ns=pre_delim, path=segments)
        assert m1.prefix == m2.prefix == pre_delim
        # assert all(f"{m1.prefix}{seg}" in m1.path for seg in segments)
        assert f"/{pre_delim}".join(segments) in m1.path
        with pytest.raises(TypeError):
            m = MetaElement("m", ns=1)


class TestMetaMap:
    @staticmethod
    def _gen_path_dict(paths):
        map_ = {}
        for path in paths:
            d = map_
            segs = path.split("/")
            idx_last = len(segs) - 1
            for i, seg in enumerate(segs):
                if i == idx_last:
                    d[seg] = MetaElement(path)
                    break
                if seg not in d:
                    d[seg] = {}
                d = d[seg]
        return map_

    def test_init_and_interface(self):
        paths = ("a1/b1", "a1/b2", "a1/b3/c1", "a2")
        d = self._gen_path_dict(paths)
        mm = MetaMap(d)
        assert len(mm) == len(paths)
        for moniker, meta in mm.items():
            assert moniker in paths
            assert isinstance(meta, MetaElement)
        for moniker in paths:
            assert moniker in mm
            assert moniker in mm[moniker].monikers
            assert mm[moniker].path.endswith(moniker)

    def test_rejects_bad_path_maps(self):
        m = MetaElement("m")
        d = {"p1": m, "p2": m}
        with pytest.raises(RuntimeError):
            mm = MetaMap(d)
        d = {"p": "invalid_leaf"}
        with pytest.raises(TypeError):
            mm = MetaMap(d)

    def test_extend(self):
        p1 = ("a3", "a1/b3/c2")
        p2 = ("a1/b1", "a1/b2", "a1/b3/c1", "a2")
        d1 = self._gen_path_dict(p1)
        d2 = self._gen_path_dict(p2)
        mm1 = MetaMap(d1)
        mm2 = mm1.extend(d2)
        for moniker in (*p1, *p2):
            assert moniker in mm2
        with pytest.raises(RuntimeError):
            mm2.extend(d1)

        d3 = {"a3": MetaElement(("a3", "a4"))}
        mm3 = mm2.extend(d3, overload=True)
        assert mm3["a4"].path.endswith("a3")

        d3["a3"] = MetaElement("a3")
        with pytest.raises(ValueError):
            mm3.extend(d3, overload=True)


class TestLabelMeta:
    def test_elem_lookup(self):
        from passthrough.extensions.pt.datetime import PDSDatetime

        xml = """<?xml version="1.0" standalone="no"?>
        <root xmlns:nsFoo="http://foo.ns" xmlns:nsBar="http://bar.ns">
            <nsFoo:a1>1337</nsFoo:a1>
            <nsBar:a2>
                <nsBar:b1>text</nsBar:b1>
                <nsBar:b2>2021-09-21T08:31:56.7671Z</nsBar:b2>
            </nsBar:a2>
        </root>
        """
        lbl = etree.fromstring(xml)
        nsmap = lbl.nsmap
        xpath = etree.XPathEvaluator(
            lbl, namespaces=nsmap, regexp=False, smart_strings=False
        )
        path_map = {
            "nsFoo:a1": MetaElement("a1", int),
            "a2": {
                "b1": MetaElement("b1", ns="nsBar"),
                "b2": MetaElement("b2", PDSDatetime, ns="nsBar"),
            },
        }
        mm = MetaMap(path_map)

        lm = LabelMeta(xpath, mm)
        for moniker, meta in mm.items():
            assert hasattr(lm, moniker)
            assert moniker in lm
            assert isinstance(lm[moniker], str)
            assert isinstance(getattr(lm, moniker), meta.type)

        with pytest.raises(TypeError):
            lm["a1"] = 42  # int is not str
        with pytest.raises(TypeError):
            lm.a1 = 42.5  # float is not int

        lm.a1 = 42
        assert lm.a1 == 42
        assert lm["a1"] == "42"
        lm["a1"] = "44"
        assert lm.a1 == 44
        assert lm["a1"] == "44"

        lm.b1 = "foo"
        assert lm.b1 == "foo"

        dt = lm.b2
        dt.add_delta(10, unit="s")
        lm.b2 = dt
        assert lm["b2"] == str(dt)

        b1a = xpath(mm["b1"].path)[0]
        b1b = etree.Element(f"{{{nsmap['nsBar']}}}b1", attrib={}, nsmap=nsmap)
        b1b.text = "bar"
        b1a.addnext(b1b)
        b1s = lm.b1
        assert isinstance(b1s, list)
        assert len(b1s) == 2
        with pytest.raises(RuntimeError):
            lm.b1 = "bar"  # multiple assignment not currently supported
