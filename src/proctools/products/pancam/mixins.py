from pathlib import Path

from passthrough import Template
from passthrough.label_tools import add_default_ns
from passthrough.exc import PTTemplateError

from .file_handlers import PanCamFH


class MatchCameraMixin:
    """Allow `DataProduct`s to evaluate applicability based on `psa:Sub-Instrument`."""

    def matches(self, other: "MatchCameraMixin") -> bool:
        return self.meta.camera == other.meta.camera  # type: ignore


class BrowseMixin:
    def generate_browse(self, template_path: Path, source_key: str) -> Template:
        browse_template = Template(template_path, {source_key: self.label})
        fas = browse_template.label.xpath(
            "*[starts-with(name(), 'File_Area_')]", namespaces=self.nsmap
        )
        if len(fas) != 1:
            raise PTTemplateError(
                f"Browse template '{template_path.name}': expected 1 File_Area_*;"
                f" found {len(fas)}"
            )
        browse_fh = PanCamFH(fas[0], self.nsmap)
        browse_template.register_file_handler(browse_fh)
        # FIXME: brittle way to handle data binding
        browse_fh["DATA"].data = self.data
        return browse_template
