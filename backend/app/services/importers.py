"""Data importer placeholders for V1.

The first production importer pass should create stations/lines from OSM and
OpenRailwayMap, import stops from cr-12306-train-info, then build
train_route_segments through spatial matching.
"""


SUPPORTED_SOURCES = ("openstreetmap", "openrailwaymap", "cr-12306-train-info")
