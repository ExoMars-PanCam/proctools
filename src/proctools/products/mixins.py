from passthrough.extensions.pt.datetime import PDSDatetime


class ObservationalMixin:
    """Allow `DataProduct`s to be sorted by `pds:start_date_time`."""

    def __lt__(self, other: "ObservationalMixin"):
        return (
            PDSDatetime(self.meta.start).datetime
            < PDSDatetime(other.meta.start).datetime
        )


class ApplicableCameraMixin:
    """Allow `DataProduct`s to evaluate applicability based on `psa:Sub-Instrument`."""

    def is_applicable(self, other: "ApplicableCameraMixin"):
        return other.meta.camera == self.meta.camera
