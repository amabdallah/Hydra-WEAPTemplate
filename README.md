WEAPImport
=============

An *EXPERIMENTAL* app to import a WEAP project into Hydra. This will:
1) Create node & link types consistent with WEAP objects and
2) Import the schematic data from the selected WEAP project.

This uses:
pypxlib (https://github.com/mherrmann/pypxlib), the Python bindings to pxlib, to read the WEAP Paradox database files.
pyshp (https://github.com/GeospatialPython/pyshp) to read the WEAP node shapefile.
