from passthrough.extensions.exm.lid import ExoMarsLID
from passthrough.extensions.pt.vid import VID

from ..meta import MetaElement as M, TimeParser, UnitParser
from ..dataproduct import DataProduct

# TODO: use double from panb? Yes
degrees = UnitParser(float, "angle", "deg")
meters = UnitParser(float, "length", "m")
nanometers = UnitParser(float, "length", "nm")
seconds = UnitParser(float, "time", "s")

time = TimeParser()

PANCAM_META_MAP = DataProduct._META_MAP.extend(
    {
        "Identification_Area": {
            "logical_identifier": M("lid", ExoMarsLID.from_string, ns="pds"),
            "version_id": M("vid", ns="pds"),
        },
        "Acquisition_Identification": {
            "acquisition_type_description": M("acq_desc", ns="emrsp_rm_pan"),
            "acquisition_type_id": M("acq_id", ns="emrsp_rm_pan"),
            "acquisition_type_name": M("acq_name", ns="emrsp_rm_pan"),
            "acquisition_sequence_image_number": M(
                "seq_img_num", int, ns="emrsp_rm_pan"
            ),
            "acquisition_sequence_number": M("seq_num", int, ns="emrsp_rm_pan"),
            "sol_id": M("sol_id", ns="emrsp_rm_pan"),
        },
        "Sampling": {
            "sample_bits": M(("bit_depth", "sample_bits"), int, ns="img"),
        },
        "Sub-Instrument": {
            "identifier": M(("camera", "sub_instrument"), ns="psa"),
        },
        "Experiment_Cycle": {
            "ec_number": M("ec_num", ns="emrsp_rm"),
            "ec_phase": M("ec_phase", ns="emrsp_rm"),
        },
        "Exposure": {
            "exposure_duration": M("exposure_duration", seconds, ns="img"),
        },
        "Optical_Filter": {
            "filter_number": M(("filter", "filter_num"), int, ns="img"),
            "bandwidth": M("filter_bw", nanometers, ns="img"),
            "center_filter_wavelength": M("filter_cwl", nanometers, ns="img"),
            "filter_id": M("filter_id", ns="img"),
            "filter_name": M("filter_name", ns="img"),
        },
        "Focus": {
            "best_focus_distance": M("focus_dist", meters, ns="img"),
            "focus_position": M("focus_pos", int, ns="img"),
        },
        "Mission": {
            "mars_sol": M("mars_sol", ns="emrsp_rm"),
            "local_mean_solar_time_start": M("start_lmst", time, ns="emrsp_rm"),
            "local_true_solar_time_start": M("start_ltst", time, ns="emrsp_rm"),
            "local_mean_solar_time_stop": M("stop_lmst", time, ns="emrsp_rm"),
            "local_true_solar_time_stop": M("stop_ltst", time, ns="emrsp_rm"),
            "vertical_survey_number": M("vs_num", ns="emrsp_rm"),
        },
        "Mission_Product": {
            "operational_vid": M("ovid", VID, ns="emrsp_rm"),
        },
        "Instrument_Information": {
            "instrument_version_number": M("model", ns="img_surface"),
        },
        "Articulation_Device_Parameters[geom:device_name='Mast PTU']": {
            "Device_Angle": {
                "Device_Angle_Index[geom:index_name='pan']": {
                    "index_value_angle": M("pan", degrees, ns="geom"),
                },
                "Device_Angle_Index[geom:index_name='tilt']": {
                    "index_value_angle": M("tilt", degrees, ns="geom"),
                },
            },
        },
        "Motion_Counter_Index[geom:index_id='MAST/PTU']": {
            "index_value_number": M("rmc_ptu", ns="geom"),
        },
        "Subframe": {
            "first_line": M("subframe_y", ns="img"),
            "first_sample": M("subframe_x", ns="img"),
        },
    },
    overload=True,
)

PANCAM_MOSAIC_META_MAP = DataProduct._META_MAP.extend(
    {
        "Identification_Area": {
            "logical_identifier": M("lid", ExoMarsLID.from_string, ns="pds"),
            "version_id": M("vid", ns="pds"),
        },
        "Experiment_Cycle": {
            "ec_number": M("ec_num", ns="emrsp_rm"),
            "ec_phase": M("ec_phase", ns="emrsp_rm"),
        },
        "Mission": {
            "mars_sol": M("mars_sol", ns="emrsp_rm"),
            "local_mean_solar_time_start": M("start_lmst", time, ns="emrsp_rm"),
            "local_true_solar_time_start": M("start_ltst", time, ns="emrsp_rm"),
            "local_mean_solar_time_stop": M("stop_lmst", time, ns="emrsp_rm"),
            "local_true_solar_time_stop": M("stop_ltst", time, ns="emrsp_rm"),
            "vertical_survey_number": M("vs_num", ns="emrsp_rm"),
        },
        "Mission_Product": {
            "operational_vid": M("ovid", VID, ns="emrsp_rm"),
        },
        "Cylindrical": {
            "pixel_scale_x": M("pixel_scale_x", float, ns="cart"),
            "pixel_scale_y": M("pixel_scale_y", float, ns="cart"),
            "maximum_elevation": M("maximum_elevation", float, ns="cart"),
            "minimum_elevation": M("minimum_elevation", float, ns="cart"),
            "start_azimuth": M("start_azimuth", float, ns="cart"),
            "stop_azimuth": M("stop_azimuth", float, ns="cart"),
            "zero_elevation_line": M("zero_elevation_line", float, ns="cart"),
        },
        "Special_Constants": {
            "missing_constant": M("missing_constant", float, ns="pds"),
            "invalid_constant": M("invalid_constant", float, ns="pds"),
        },
    },
    overload=True,
)
