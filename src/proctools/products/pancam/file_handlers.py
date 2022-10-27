import hashlib
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from lxml import etree
from passthrough.exc import PTTemplateError
from passthrough.extensions.file import FileHandler, DataObject


class Array2DImageDO(DataObject, classes="Array_2D_Image"):
    def __init__(self, t_elem: etree._Element, nsmap: Dict[str, str]):
        super().__init__(t_elem, nsmap)
        self._shape = tuple(
            int(
                self._t_elem.find(
                    f"./pds:Axis_Array[pds:axis_name = '{a}']/pds:elements",
                    namespaces=self._nsmap,
                ).text
            )
            for a in ("Line", "Sample")
        )
        arr_dtype = self._t_elem.find(
            "./pds:Element_Array/pds:data_type", namespaces=self._nsmap
        ).text.strip()
        self._dtype = {
            "IEEE754MSBSingle": ">f4",
            "UnsignedMSB4": ">u4",
        }[arr_dtype]
        self.data: np.ndarray = np.zeros(self._shape, self._dtype)

    @property
    def size(self) -> int:
        return self.data.size * self.data.itemsize

    @property
    def serialized(self) -> bytes:
        if self.data.shape != self._shape or self.data.dtype.str != self._dtype:
            raise RuntimeError(
                f"Array does not match template specs: {self.data.shape}"
                f" {self.data.dtype.str} (array) VS {self._shape} {self._dtype}"
            )
        return self.data.tobytes()


class EncodedImageDO(DataObject, classes="Encoded_Image"):
    def __init__(self, t_elem: etree._Element, nsmap: Dict[str, str]):
        super().__init__(t_elem, nsmap)
        self._size: Optional[int] = None
        self.data: Optional[np.ndarray] = None
        self.encoding = t_elem.find("pds:encoding_standard_id", namespaces=nsmap).text
        if self.encoding.upper() != "PNG":
            raise RuntimeError(f"Encoding '{self.encoding}' is currently not supported")

    @property
    def size(self) -> int:
        if self._size is None:
            raise RuntimeError("Size requested before serialization")
        return self._size

    @property
    def serialized(self) -> bytes:
        if self.data is None:
            raise RuntimeError("Data array has not been initialised")
        import imageio

        # TODO: use origin DQ to determine white/black point
        img = (self.data / self.data.max()) * 255
        img = img.clip(min=0, max=255)
        ser = imageio.imwrite(imageio.RETURN_BYTES, img.astype(np.uint8), "png")
        self._size = len(ser)
        return ser


class PanCamFH(FileHandler):
    """
    ToDo:
    - describe usage (pre-populate pds:file_name in template)
    """

    def __init__(self, t_elem: etree._Element, nsmap: Dict[str, str]):
        self._written = False
        self._fa = t_elem
        self._nsmap = nsmap
        file_name = self._fa.find("pds:File/pds:file_name", namespaces=nsmap).text
        self._name: str = file_name.strip() if file_name is not None else ""
        if not self._name:
            raise PTTemplateError(
                f"pds:File/pds:file_name must be pre-populated", self._fa
            )
        self._size: Optional[int] = None
        self._md5: Optional[str] = None
        self._datetime: Optional[str] = None
        self._data_objects: Dict[str, DataObject] = {}
        for child in self._fa.iterchildren():
            if child.tag.endswith("File"):
                continue
            do = DataObject.from_elem(child, nsmap)
            self._data_objects[do.local_id] = do

    def __getitem__(self, local_id: str) -> DataObject:
        return self._data_objects[local_id]

    @property
    def creation_date_time(self):
        self._check_written()
        return self._datetime

    @property
    def file_name(self):
        return self._name

    @property
    def file_size(self):
        self._check_written()
        return self._size

    @property
    def md5_checksum(self):
        self._check_written()
        return self._md5

    @property
    def t_elem(self):
        return self._fa

    def write(self, out_dir: Path):
        md5 = hashlib.md5()
        size = 0
        with open(out_dir / self._name, "wb") as f:
            for do in self._data_objects.values():
                do.offset = size
                ab = do.serialized
                f.write(ab)
                md5.update(ab)
                size += do.size
        self._datetime = self._fa.xpath("pt:datetime.now()")
        self._size = size
        self._md5 = md5.hexdigest()
        self._written = True

    def _check_written(self):
        if not self._written:
            raise RuntimeError(f"Access attempted before file write")