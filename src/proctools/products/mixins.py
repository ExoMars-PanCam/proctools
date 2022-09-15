

class SortStartTimeMixin:
    """Allow `DataProduct`s to be sorted by `pds:start_date_time`."""

    def __lt__(self, other: "SortStartTimeMixin") -> bool:
        return (
            self.meta.start.datetime  # type: ignore
            < other.meta.start.datetime  # type: ignore
        )
