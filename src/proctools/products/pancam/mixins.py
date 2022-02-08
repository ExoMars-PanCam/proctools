class MatchCameraMixin:
    """Allow `DataProduct`s to evaluate applicability based on `psa:Sub-Instrument`."""

    def matches(self, other: "MatchCameraMixin") -> bool:
        return self.meta.camera == other.meta.camera  # type: ignore

