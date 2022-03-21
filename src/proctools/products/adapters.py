from pathlib import Path
from typing import Union

import numpy as np
from pds4_tools.reader.general_objects import StructureList
from pds4_tools.reader.table_objects import TableStructure


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
        # select record(s) by value of key field (e.g. where "filter" field is 4)
        match = self.ts[np.where(self.ts[self.key_field] == key)]
        if not match:
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