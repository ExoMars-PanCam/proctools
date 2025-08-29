from pathlib import Path
from typing import Union

import numpy as np
from pds4_tools.reader.general_objects import StructureList
from pds4_tools.reader.table_objects import TableStructure


class MultiData:
    """
    Provide access to a list's given structure's data via index key notation.

    This "wrapper" class provides two shortcuts when accessing items in a
    PDS4 StructureList.

    First, you can provide a format string which will be used to modify the
    dict key you provide.

    Secondly, the __getitem__ method (used for array indexing) returns the
    "data" member of the found Structure within the structure list, not the
    Structure itself.

    For example, the following are equivalent:

        # Given "structures", a StructureList object
        for i in range(10):
            print(structures[f"DATA_{i:02d}"].data)

    or

        m = MultiData(structures, fmt="DATA_{:02d})
        for i in range(10):
            print(m[i])

    """

    def __init__(self, structures: StructureList, fmt: str = "{}"):
        self.sl = structures
        self.fmt = fmt

    def __getitem__(self, struct):
        return self.sl[self.fmt.format(struct)].data


class KeyTable:
    """
    Select row(s) of a table based on the value of a key field.
    """

    def __init__(self, table: TableStructure, key_field: str):
        self.ts = table
        self.key_field = key_field

    def __getitem__(self, key: Union[int, str]):
        # This is using numpy, which looks a bit odd on first glance,
        # since it's filtering dict-like objects. This approach
        # is much faster than a list comprehension for large
        # arrays, and only a little slower for small ones.
        match = self.ts[np.where(self.ts[self.key_field] == key)]

        if len(match) == 0:
            table_id = (
                self.ts.meta_data["local_identifier"]
                if self.ts.meta_data is not None
                else "<UNKNOWN>"
            )
            filename = (
                Path(self.ts.parent_filename).name
                if self.ts.parent_filename is not None
                else "<UNKNOWN>"
            )
            lid = getattr(
                self.ts.full_label.find(".//pds:logical_identifier"),
                "text",
                "<UNKNOWN>",
            )
            raise KeyError(
                f"key '{key}' not found in"
                f" field '{self.key_field}' of"
                f" table '{table_id}' in"
                f" file '{filename}' of"
                f" product '{lid}'"
            )
        return match
