from ..dataproduct import DataProduct

PANCAM_META_MAP = {
    **DataProduct._META_MAP,
    "acq_desc": ".//emrsp_rm_pan:Acquisition_Identification/emrsp_rm_pan:acquisition_type_description",
    "acq_id": (
        ".//emrsp_rm_pan:Acquisition_Identification/emrsp_rm_pan:acquisition_type_id"
    ),
    "acq_name": (
        ".//emrsp_rm_pan:Acquisition_Identification/emrsp_rm_pan:acquisition_type_name"
    ),
    "camera": ".//psa:Sub-Instrument/psa:identifier",  # alias
    "ec_num": ".//emrsp_rm:Experiment_Cycle/emrsp_rm:ec_number",
    "ec_phase": ".//emrsp_rm:Experiment_Cycle/emrsp_rm:ec_phase",
    "exposure_duration": ".//img:Exposure/img:exposure_duration",
    "filter": ".//img:Optical_Filter/img:filter_number",  # alias
    "filter_num": ".//img:Optical_Filter/img:filter_number",
    "filter_bw": ".//img:Optical_Filter/img:bandwidth",
    "filter_cwl": ".//img:Optical_Filter/img:center_filter_wavelength",
    "filter_id": ".//img:Optical_Filter/img:filter_id",
    "filter_name": ".//img:Optical_Filter/img:filter_name",
    "mars_sol": ".//emrsp_rm:Mission/emrsp_rm:mars_sol",
    "model": (
        ".//img_surface:Instrument_Information/img_surface:instrument_version_number"
    ),
    "pan": (
        ".//geom:Articulation_Device_Parameters[geom:device_name='Mast"
        " PTU']/geom:Device_Angle/geom:Device_Angle_Index[geom:index_name='tilt']/geom:index_value_angle"
    ),
    "rmc_ptu": (
        ".//geom:Motion_Counter_Index[geom:index_id='MAST/PTU']/geom:index_value_number"
    ),
    "seq_img_num": ".//emrsp_rm_pan:Acquisition_Identification/emrsp_rm_pan:acquisition_sequence_image_number",
    "seq_num": ".//emrsp_rm_pan:Acquisition_Identification/emrsp_rm_pan:acquisition_sequence_number",
    "sol_id": ".//emrsp_rm_pan:Acquisition_Identification/emrsp_rm_pan:sol_id",
    "sub_instrument": ".//psa:Sub-Instrument/psa:identifier",
    "subframe_y": ".//img:Subframe/img:first_line",
    "subframe_x": ".//img:Subframe/img:first_sample",
    "start_lmst": ".//emrsp_rm:Mission/emrsp_rm:local_mean_solar_time_start",
    "start_ltst": ".//emrsp_rm:Mission/emrsp_rm:local_true_solar_time_start",
    "stop_lmst": ".//emrsp_rm:Mission/emrsp_rm:local_mean_solar_time_stop",
    "stop_ltst": ".//emrsp_rm:Mission/emrsp_rm:local_true_solar_time_stop",
    "tilt": (
        ".//geom:Articulation_Device_Parameters[geom:device_name='Mast"
        " PTU']/geom:Device_Angle/geom:Device_Angle_Index[geom:index_name='tilt']/geom:index_value_angle"
    ),
    "vs_num": ".//emrsp_rm:Mission/emrsp_rm:vertical_survey_number",
    "ovid": ".//emrsp_rm:Mission_Product/emrsp_rm:operational_vid",
}

del DataProduct

from .ancillary import RadColPrm, RadFlatPrm, RadSsrPrm
from .observational import AppCol, Observation, SpecRad
