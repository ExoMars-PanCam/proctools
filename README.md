# ProcTools
Common tools for creating PDS4 data product processing software.

## Project status
ProcTools is under active development and is presently in the alpha stage. 

## Features
### CLI framework
- Based on Typer
- Standardised logging with fallbacks and bootstrap buffering
- Integrated and extensible OS exit code support
- Runner-function providing unified CLI behaviour
### Data product read-in and wrappers
- Based on pds4_tools
- DataProduct data model
  - Convenient access to label metadata and payload data
  - Representation of a projects product types facilitated by subclassing (a subset of proposed products for ExoMars PanCam are currently bundled with the project for reference)
- Filesystem based loading and management of products via ProductDepot
