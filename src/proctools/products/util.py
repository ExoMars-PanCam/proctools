import hashlib
from pathlib import Path

import numpy as np


class BayerSlice:
    """The `BayerSlice` class carries `slice` attributes targeting individual Bayer
    channels for a given pattern and (subframe) origin offset.

    Attributes:
        r: `slice` identifying red channel pixels
        g1: `slice` identifying first green channel pixels
        g2: `slice` identifying second green channel pixels
        b: `slice` identifying blue channel pixels
        pattern: effective pattern given the offset (upper case)
    """

    def __init__(self, pattern: str, y_off: int = 0, x_off: int = 0) -> None:
        """
        Args:
            pattern: one of "RGGB", "BGGR", "GRBG", or "GBRG"; arrangement of the
                colour channels
            y_off: optional y-axis (lines) subframe offset to account for
            x_off: optional x-axis (samples) subframe offset to account for
        """
        pattern = pattern.upper()
        if not sorted(pattern) == ["B", "G", "G", "R"]:
            raise ValueError(f"Invalid bayer pattern: '{pattern}'")

        # A slice is Python's data structure for representing the
        # start:stop:step notation used in array subscripts. We're
        # going to create 2-d slices for R, G1, G2 and B per the
        # specified pattern, taking any specified offset into account.
        self.r: slice = None
        self.g1: slice = None
        self.g2: slice = None
        self.b: slice = None

        # This is the order of pixels within a 2x2 block
        # as specified by the pattern. e.g. for GRBG, we'd
        # have:
        #        GR
        #        BG
        #
        # loc_order is specified in row-major order - i.e.
        # the "y" position within the pattern is the first
        # item in each tuple.
        loc_order = ((0, 0), (0, 1), (1, 0), (1, 1))

        # These are symbolic constants within for the tuple
        # X and Y coordinates, to save confusion below/
        y = 0
        x = 1

        # Used to store the modified pattern.
        reordered = [""] * 4

        # This is used in constructing the attribute name
        # above (r, g1, g2, b)
        g_count = 1
        for i, c in enumerate(pattern):
            # This is the position within the 2x2 block
            # that the colour inhabits once we've allowed
            # for x/y offsets.
            loc = (
                (loc_order[i][y] + y_off) % 2,
                (loc_order[i][x] + x_off) % 2,
            )

            # We have separate attributes for the two green pixels, so
            # keep track of which one we're on.
            attr_name = c.lower()
            if attr_name == "g":
                attr_name = f"g{g_count}"
                g_count += 1

            # Set the appropriate attribute (r, g1, g2, b) with a tuple
            # giving the 2d slicing structure we've derived.
            #
            # np.s_[..] is a tricky function which generates the needed
            # slice from the more familiar start:stop:step notation.
            self.__setattr__(attr_name, (np.s_[loc[y]::2], np.s_[loc[x]::2]))

            # Now, given the possibly modified location we've
            # calculated, store the colour name in the appropriate
            # position in reordered. When we join reordered back together,
            # this will give us the modified pattern that would apply if the
            # offsets were zero.
            reordered[loc_order.index(loc)] = c

        # And finally store the resulting pattern.
        self.pattern: str = "".join(reordered)


def get_md5sum(path: Path, buffer: int = 128 * 1024):
    """
    Generate the md5 hash for a file in chunks, providing a low memory footprint
    """
    md5 = hashlib.md5()
    with open(path, "rb", buffering=0) as f:
        while True:
            data = f.read(buffer)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()
