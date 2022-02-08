from passthrough.extensions.pt.datetime import PDSDatetime


class SortStartTimeMixin:
    """Allow `DataProduct`s to be sorted by `pds:start_date_time`."""

    def __lt__(self, other: "SortStartTimeMixin") -> bool:
        return (
            PDSDatetime(self.meta.start).datetime  # type: ignore
            < PDSDatetime(other.meta.start).datetime  # type: ignore
        )
