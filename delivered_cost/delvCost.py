# import raster_tools and modules
from raster_tools import Raster, surface, distance, open_vectors, creation, Vector
import os, time
import geopandas as gpd
import numpy as np
from dask.diagnostics import ProgressBar
from shapely.geometry import box, Point, Polygon
import osmnx as ox
import pandas
import numpy as np

import py3dep
import tempfile

# import elevation
import rioxarray

from qgis.core import QgsProcessingUtils


import warnings

# turn warnings off
warnings.filterwarnings("ignore")

# # specify paths to data layers default demo
# study_area_coords = None
# saw_coords = None
# lyr_roads_path = None
# lyr_barriers_path = None


# transportation speed
h_speed = {
    "residential": 25,
    "unclassified": 15,
    "tertiary": 35,
    "secondary": 45,
    "primary": 55,
    "trunk": 55,
    "motorway": 65,
}
# mtfcc_dic={'S1400':40,'S1200':56,'S1100':88}
temp_dir = QgsProcessingUtils.tempFolder()


def get_osm_data(
    sgeo,
    osm_dic={
        "highway": [
            "motorway",
            "trunk",
            "primary",
            "secondary",
            "tertiary",
            "unclassified",
            "residential",
        ]
    },
    out_crs=None,
):
    """
    downloads openstreetmaps data for a specified dictionary of layers and returns a geopandas dataframe

    sgeo: object, polygon bounding box used to extract data (WGS 84 - EPSG:4326)
    osm_dic: dictionary, dictionary of data types and resources
    out_crs: object, optional crs used to project geopandas dataframe to a differnt crs

    return: geopandas dataframe
    """
    out_gdf = ox.features_from_polygon(sgeo, osm_dic)
    if not out_crs is None:
        out_gdf = out_gdf.to_crs(out_crs)
    return out_gdf


def get_3dep_data(sgeo, res=30, out_crs=None):
    """
    Downloads 3dep data and returns a raster object.
    """
    from shapely.validation import explain_validity
    from shapely.geometry import Polygon

    if not isinstance(sgeo, Polygon):
        raise TypeError(f"Expected shapely Polygon, got {type(sgeo)}")
    if not sgeo.is_valid:
        raise ValueError(f"Invalid input geometry: {explain_validity(sgeo)}")

    try:
        # Convert to target CRS (EPSG:3857, meters)
        sgeo_3857 = gpd.GeoSeries([sgeo], crs=4326).to_crs(3857)[0]
        print(f"Reprojected area: {sgeo_3857.area} m²")

        # Validate after reprojection
        if not sgeo_3857.is_valid:
            print("Geometry invalid after reprojection:", explain_validity(sgeo_3857))
        if sgeo_3857.is_empty:
            raise ValueError("Geometry became empty after reprojection")

        out_rs = py3dep.get_dem(sgeo_3857, res, 3857).expand_dims({"band": 1})
    except Exception as e:
        raise RuntimeError(f"Failed to download DEM from py3dep: {e}") from e

    if out_crs is not None:
        out_rs = out_rs.rio.reproject(out_crs)

    return Raster(out_rs.chunk())


# def get_3dep_data(sgeo: Polygon, res=30, out_crs=None) -> Raster:
#     """
#     Downloads DEM data using the `elevation` module and returns a raster-tools Raster object.

#     Parameters:
#     - sgeo: shapely Polygon in EPSG:4326
#     - res: ignored, elevation only supports SRTM (~30m)
#     - out_crs: optional target CRS

#     Returns:
#     - Raster: raster-tools lazy Raster object
#     """
#     if not isinstance(sgeo, Polygon):
#         raise TypeError(f"Expected shapely Polygon, got {type(sgeo)}")
#     if not sgeo.is_valid:
#         raise ValueError(f"Invalid geometry: {explain_validity(sgeo)}")
#     if sgeo.area < 1e-8:
#         raise ValueError("Geometry too small to request DEM.")

#     # Get bounds in EPSG:4326
#     minx, miny, maxx, maxy = sgeo.bounds

#     with tempfile.TemporaryDirectory() as tmpdir:
#         dem_path = f"{tmpdir}/clipped_dem.tif"

#         # Download and clip DEM
#         elevation.clip(
#             bounds=(minx, miny, maxx, maxy), output=dem_path, product="SRTM1"
#         )
#         elevation.clean()  # remove cached data to save space

#         # Open with rioxarray and wrap in raster-tools
#         try:
#             da = rioxarray.open_rasterio(dem_path, masked=True).squeeze(
#                 "band", drop=True
#             )
#         except Exception as e:
#             raise RuntimeError(f"Failed to open clipped DEM: {e}")

#         # Reproject if needed
#         if out_crs is not None:
#             da = da.rio.reproject(out_crs)

#         return Raster(da.chunk())


def _remove_file(path):
    if os.path.exists(path):
        os.remove(path)
    return


def _run(
    study_area_coords,
    saw_coords,
    lyr_roads_path=None,
    lyr_barriers_path=None,
    sk_r=2.44,
    cb_r=3.35,
    sk_d=165,
    cb_d=400,
    fb_d=15,
    hf_d=27,
    pr_d=56,
    lt_d=98,
    ht_d=2470,
    pf_d=2470,
    sk_p=1.25,
    cb_p=1.04,
    lt_p=12.25,
    cb_o=False,
    pbar=None,
    log=None,
    runcnt=1,
):
    """
    Runs delivered cost processing and saves output rasters.

    Parameters:
        study_area_coords: geometry coordinates of study area polygon(s)
        saw_coords: geometry coordinates of sawmill point(s)
        lyr_roads_path: optional path to roads vector data
        lyr_barriers_path: optional path to barriers vector data
        sk_r, cb_r, sk_d, cb_d, fb_d, hf_d, pr_d, lt_d, ht_d, pf_d, sk_p, cb_p, lt_p: various rates and constants
        cb_o: bool, whether to save optional outputs
        pbar: optional progress bar object to update
        log: optional logger (currently unused)
        runcnt: integer run count to number output files uniquely

    Returns:
        dict mapping raster description keys to saved file paths
    """
    warnings.simplefilter("ignore")
    maybe_log(log, "Reading the data...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)

    pnts = [Point(xy) for xy in saw_coords]
    polys = [Polygon(study_area_coords)]

    saw = gpd.GeoDataFrame(geometry=pnts, crs=4326)
    s_area = gpd.GeoDataFrame(geometry=polys, crs=4326)

    ext = saw.union(s_area.unary_union).buffer(0.15)
    ply = box(*ext.total_bounds)

    osm_rds = {
        "highway": [
            "motorway",
            "trunk",
            "primary",
            "secondary",
            "tertiary",
            "unclassified",
            "residential",
        ]
    }
    osm_strms = {"waterway": ["river", "stream", "cannel", "ditch"]}
    osm_waterbody = {"water": ["lake", "reservoir", "pond"]}

    maybe_log(log, "Reading road data...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)
    if lyr_roads_path is None:
        rds = get_osm_data(ply, osm_rds, out_crs=s_area.crs).reset_index()
    else:
        rds = open_vectors(lyr_roads_path).data.compute()

    if lyr_barriers_path is None:
        maybe_log(log, "Getting stream data...")
        strms = get_osm_data(ply, osm_strms, out_crs=s_area.crs).reset_index()
        maybe_log(log, "Getting waterbody data...")
        wtrbd = get_osm_data(ply, osm_waterbody, out_crs=s_area.crs).reset_index()
    else:
        # if barriers vector file is provided, load barriers but set streams and waterbodies as empty GeoDataFrames to avoid errors
        barv = open_vectors(lyr_barriers_path).compute()
        strms = gpd.GeoDataFrame(geometry=[], crs=s_area.crs)
        wtrbd = gpd.GeoDataFrame(geometry=[], crs=s_area.crs)

    # project all data into EPSG:5070
    rds = rds.to_crs(5070)
    strms = strms.to_crs(5070)
    wtrbd = wtrbd.to_crs(5070)
    saw = saw.to_crs(5070)
    s_area = s_area.to_crs(5070)

    maybe_log(log, "Getting elevation Data...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)
    from shapely.validation import explain_validity

    print("DEBUG: Polygon validity:", ply.is_valid)
    print("DEBUG: Polygon issue:", explain_validity(ply))
    print("DEBUG: Polygon area:", ply.area)
    print("DEBUG: Polygon WKT:", ply.wkt)

    elv = get_3dep_data(ply, 30, out_crs=s_area.crs)

    maybe_log(log, "Subsetting and attributing data...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)

    rds["speed"] = rds["highway"].map(h_speed)
    tms = rds.maxspeed.str.slice(0, 2)
    tms = tms.where(tms.str.isnumeric(), 25).astype(float)
    rds["speed"] = rds["speed"].where(rds["maxspeed"].isna(), tms)
    rds["conv"] = 2 * (((1 / (rds["speed"] * 1609.344)) * lt_d) / lt_p)

    maybe_log(log, "Snapping sawmills to roads...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)
    tmp_rds_seg = rds.sindex.nearest(saw.geometry, return_all=False)[1]
    lns = rds.iloc[tmp_rds_seg].geometry.values
    saw["cline"] = lns
    saw["npt"] = saw.apply(
        lambda row: row["cline"].interpolate(row["cline"].project(row["geometry"])),
        axis=1,
    )
    saw = saw.set_geometry("npt").set_crs(saw.crs)

    if lyr_barriers_path is None:
        strm_b = strms[strms["intermittent"].isna()].buffer(30)
        wb_b = wtrbd.buffer(30)
        barv = gpd.GeoDataFrame(geometry=pandas.concat([strm_b, wb_b]), crs=rds.crs)

    bar2 = Vector(barv).to_raster(elv, all_touched=True).set_null_value(None) < 1

    maybe_log(log, "Creating base layers for threshholding...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)
    slp = surface.slope(elv, degrees=False).eval()
    c_rs = creation.constant_raster(elv).set_null_value(0)
    rds_rs = Vector(rds).to_raster(elv, "conv").set_null_value(0).eval()

    maybe_log(log, "Calculating on road hauling costs...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)
    saw_rs = Vector(saw).to_raster(elv).set_null_value(0).eval()
    on_d_saw = distance.cda_cost_distance(rds_rs, saw_rs, elv)

    src_saw = (on_d_saw * 100).astype(int)

    maybe_log(log, "Calculating extraction costs...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)

    b_dst_cs2 = bar2.set_null_value(0)

    saw_d, saw_t, saw_a = distance.cost_distance_analysis(b_dst_cs2, src_saw, elv)

    maybe_log(log, "Calculating additional felling, processing, and treatment costs")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)
    f1 = slp <= 0.35
    fell = (f1 * fb_d).where(f1, hf_d)
    prc = creation.constant_raster(elv, pr_d).astype(float)
    oc = fell + prc

    ht_cost = creation.constant_raster(elv, (ht_d * 0.222395)).astype(float)
    pf_cost = creation.constant_raster(elv, (pf_d * 0.222395)).astype(float)

    maybe_log(log, "Combining costs...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)
    s_c = 2 * (((1 / (sk_r * 1000)) * sk_d) / sk_p)
    c_c = 2 * (((1 / (cb_r * 1000)) * cb_d) / cb_p)

    sk_saw_cost = (saw_d * s_c) + (saw_a / 100) + oc
    cb_saw_cost = (saw_d * c_c) + (saw_a / 100) + oc

    rd_dist = distance.cda_cost_distance(c_rs, (rds_rs > 0).astype(int), elv)

    sk = f1 & (rd_dist < 460)
    cb = (~f1 & (rd_dist < 305)) * 2
    opr = sk + cb

    outdic = {}
    maybe_log(log, "Saving default rasters...")
    if pbar is not None:
        pbar.setValue(pbar.value() + 1)
    o1 = opr == 1
    o2 = opr == 2
    sc1 = sk_saw_cost * o1
    sc2 = cb_saw_cost * o2
    saw_cost = sc1 + sc2
    saw_cost = saw_cost.where(saw_cost >= 0, np.nan)
    d_cost = os.path.join(temp_dir, f"d_cost{runcnt}.tif")
    saw_cost.save(d_cost)
    outdic[f"Delivered Cost {runcnt}"] = d_cost
    add_tr_fr_cost = ht_cost + pf_cost
    a_cost = os.path.join(temp_dir, f"a_cost{runcnt}.tif")
    add_tr_fr_cost.save(a_cost)
    outdic[f"Additional Treatment Cost {runcnt}"] = a_cost

    if cb_o:
        maybe_log(
            log,
            "Saving optional rasters saw, bio, additional cost surfaces, operation surface",
        )
        if pbar is not None:
            pbar.setValue(pbar.value() + 1)

        skidder_cost = os.path.join(temp_dir, f"skidder_cost{runcnt}.tif")
        sk_saw_cost.save(skidder_cost)
        outdic[f"Skidder Cost {runcnt}"] = skidder_cost

        cable_cost = os.path.join(temp_dir, f"cable_cost{runcnt}.tif")
        cb_saw_cost.save(cable_cost)
        outdic[f"Cable Cost {runcnt}"] = cable_cost

        hand_treatment_costs = os.path.join(
            temp_dir, f"hand_treatment_costs{runcnt}.tif"
        )
        ht_cost.save(hand_treatment_costs)
        outdic[f"Hand Treatment Cost {runcnt}"] = hand_treatment_costs

        prescribed_fire_costs = os.path.join(
            temp_dir, f"prescribed_fire_costs{runcnt}.tif"
        )
        pf_cost.save(prescribed_fire_costs)
        outdic[f"Prescribed Fire Cost {runcnt}"] = prescribed_fire_costs

        potential_harv_system = os.path.join(
            temp_dir, f"potential_harv_system{runcnt}.tif"
        )
        opr.save(potential_harv_system)
        outdic[f"Potential Harvesting System {runcnt}"] = potential_harv_system

    if pbar is not None:
        pbar.setValue(pbar.maximum())

    runcnt += 1
    maybe_log(log, "Finished all processing.")

    return outdic, runcnt


def run(
    study_area_coords,
    saw_coords,
    lyr_roads_path=None,
    lyr_barriers_path=None,
    sk_r=2.44,
    cb_r=3.35,
    sk_d=165,
    cb_d=400,
    fb_d=15,
    hf_d=27,
    pr_d=56,
    lt_d=98,
    ht_d=2470,
    pf_d=2470,
    sk_p=1.25,
    cb_p=1.04,
    lt_p=12.25,
    cb_o=False,
    pbar=None,
    log=None,
):
    runcnt = 1
    start = time.time()
    with ProgressBar():
        outdic, runcnt = _run(
            study_area_coords=study_area_coords,
            saw_coords=saw_coords,
            lyr_roads_path=lyr_roads_path,
            lyr_barriers_path=lyr_barriers_path,
            sk_r=sk_r,
            cb_r=cb_r,
            sk_d=sk_d,
            cb_d=cb_d,
            fb_d=fb_d,
            hf_d=hf_d,
            pr_d=pr_d,
            lt_d=lt_d,
            ht_d=ht_d,
            pf_d=pf_d,
            sk_p=sk_p,
            cb_p=cb_p,
            lt_p=lt_p,
            cb_o=cb_o,
            pbar=pbar,
            log=log,
            runcnt=runcnt,
        )
    end = time.time()
    maybe_log(log, f"Total processing time: {end - start:.2f} seconds")
    return outdic


def maybe_log(log, msg):
    """
    Helper function to log messages if a logger is provided.
    """
    if log:
        log(msg)
    else:
        print(msg)  # Fallback to if no logger is provided
