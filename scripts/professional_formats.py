"""Local adapters for 3D scenes, CAD drawings and geospatial data."""
import base64
import importlib.util
import json
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

MODEL_INPUTS = {".obj", ".stl", ".ply", ".off", ".gltf", ".glb", ".fbx", ".blend"}
GIS_INPUTS = {".geojson", ".gpkg", ".shp", ".kml", ".gpx", ".fgb"}
GIS_DRIVERS = {"geojson": "GeoJSON", "gpkg": "GPKG", "shp.zip": "ESRI Shapefile",
               "kml": "KML", "gpx": "GPX", "fgb": "FlatGeobuf"}


def blender_path():
    configured = os.environ.get("FILE_CONVERTER_BLENDER")
    if configured and Path(configured).is_file():
        return configured
    executable = shutil.which("blender")
    if executable:
        return executable
    root = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blender Foundation"
    matches = sorted(root.glob("Blender */blender.exe"), reverse=True) if root.is_dir() else []
    return str(matches[0]) if matches else None


def oda_path():
    configured = os.environ.get("FILE_CONVERTER_ODA")
    if configured and Path(configured).is_file():
        return configured
    return shutil.which("ODAFileConverter")


def capabilities():
    has = lambda name: bool(importlib.util.find_spec(name))
    drivers = {}
    if has("pyogrio"):
        import pyogrio
        drivers = pyogrio.list_drivers()
    return {"blender": blender_path(), "trimesh": has("trimesh"), "dxf": has("ezdxf"),
            "cad_render": has("ezdxf") and has("matplotlib"), "oda": oda_path(),
            "gis": all(has(name) for name in ["geopandas", "pyogrio", "pyproj", "shapely"]),
            "gis_write_targets": [name for name, driver in GIS_DRIVERS.items() if "w" in drivers.get(driver, "")],
            "gis_drivers": drivers}


def model(source, workspace, target, args):
    executable = blender_path()
    output = workspace / f"converted.{target}"
    if executable and source.suffix.lower() != ".off" and target != "off":
        if target not in {"obj", "stl", "ply", "gltf", "glb", "fbx", "blend", "png"}:
            raise ValueError("Unsupported Blender target")
        command = [executable, "--background", "--factory-startup", "--disable-autoexec", "--python",
                   str(Path(__file__).with_name("blender_worker.py")), "--",
                   "--input", str(source), "--output", str(output)]
        if args.allow_layout_loss:
            command.append("--allow-loss")
        result = subprocess.run(command, capture_output=True, timeout=180)
        if result.returncode or not output.is_file():
            raise ValueError("Blender conversion failed: " + result.stderr.decode("utf-8", "replace")[-1200:]
                             + result.stdout.decode("utf-8", "replace")[-1000:])
        if target == "gltf":
            document = json.loads(output.read_text(encoding="utf-8"))
            for group in ["buffers", "images"]:
                for item in document.get(group, []):
                    uri = item.get("uri", "")
                    if uri and not uri.startswith("data:"):
                        from urllib.parse import unquote
                        asset = (output.parent / unquote(uri)).resolve()
                        if not asset.is_relative_to(workspace.resolve()) or not asset.is_file():
                            raise ValueError("glTF export references an external asset")
                        content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
                        item["uri"] = "data:" + content_type + ";base64," + base64.b64encode(asset.read_bytes()).decode("ascii")
            output.write_text(json.dumps(document), encoding="utf-8")
        return [output], ["3D import/export can change unsupported materials, modifiers, animation or format-specific features"], "isolated_blender_export_reimported"
    if source.suffix.lower() in {".fbx", ".blend"} or target in {"fbx", "blend", "png"}:
        raise ValueError("This scene route requires Blender")
    import trimesh
    if target not in {"obj", "stl", "ply", "off", "glb"}:
        raise ValueError("Fallback mesh converter supports OBJ/STL/PLY/OFF/GLB")
    if not args.allow_layout_loss:
        raise ValueError("Mesh fallback flattens scene structure; choose --allow-layout-loss")
    scene = trimesh.load_scene(source, process=False)
    mesh = scene.to_mesh()
    if not len(mesh.vertices) or not len(mesh.faces):
        raise ValueError("Model contains no triangle mesh")
    payload = mesh.export(file_type=target)
    output.write_bytes(payload.encode("utf-8") if isinstance(payload, str) else payload)
    checked = trimesh.load_scene(output, process=False).to_mesh()
    if not len(checked.vertices) or not len(checked.faces):
        raise ValueError("Exported model has no mesh")
    return [output], ["Mesh fallback: hierarchy, animation and advanced materials are flattened"], "mesh_output_reopened"


def cad(source, workspace, target, args):
    import ezdxf
    if source.suffix.lower() == ".dwg" or target == "dwg":
        executable = oda_path()
        if not executable:
            raise ValueError("DWG conversion requires an installed ODA File Converter; set FILE_CONVERTER_ODA")
        from ezdxf.addons import odafc
        previous = ezdxf.options.get("odafc-addon", "win_exec_path")
        try:
            ezdxf.options.set("odafc-addon", "win_exec_path", executable)
            document = odafc.readfile(str(source)) if source.suffix.lower() == ".dwg" else ezdxf.readfile(source)
            if target == "dwg":
                output = workspace / "converted.dwg"
                odafc.export_dwg(document, str(output), version="R2018", replace=False)
                check = odafc.readfile(str(output))
                if len(check.modelspace()) != len(document.modelspace()):
                    raise ValueError("DWG entity count changed")
                return [output], ["ODA conversion requires drawing-specific review"], "dwg_reopened"
        finally:
            ezdxf.options.set("odafc-addon", "win_exec_path", previous)
    else:
        document = ezdxf.readfile(source)
    auditor = document.audit()
    if auditor.has_errors:
        raise ValueError("DXF audit found unresolved drawing errors")
    if target == "dxf":
        output = workspace / "converted.dxf"
        document.saveas(output)
        check = ezdxf.readfile(output)
        if len(check.modelspace()) != len(document.modelspace()):
            raise ValueError("DXF entity count changed")
        return [output], [], "dxf_entity_count_checked"
    if target not in {"svg", "pdf", "png"}:
        raise ValueError("Drawing targets are DXF, SVG, PDF and PNG; DWG needs ODA")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy
    layout = document.layouts.get(args.layout)
    if layout is None:
        raise ValueError("Requested CAD layout does not exist")
    figure = plt.figure(figsize=(10, 7))
    try:
        axes = figure.add_axes((0, 0, 1, 1))
        axes.set_axis_off()
        Frontend(RenderContext(document), MatplotlibBackend(axes),
                 config=Configuration(background_policy=BackgroundPolicy.WHITE)).draw_layout(layout, finalize=True)
        output = workspace / f"converted.{target}"
        figure.savefig(output, dpi=args.dpi, bbox_inches="tight", pad_inches=0.1)
    finally:
        plt.close(figure)
    if target == "pdf":
        from document_formats import verify
        verify(output)
    elif target == "png":
        from PIL import Image
        with Image.open(output) as image:
            image.load()
    else:
        from defusedxml import ElementTree
        ElementTree.parse(output)
    return [output], ["2D CAD rendering; 3D entities use top projection, external references and unsupported entities need review"], "cad_render_reopened"


def geo(source, workspace, target, args):
    import geopandas as gpd
    import pyogrio
    import pandas as pd
    from pyproj import CRS
    suffix = source.suffix.lower()
    if suffix in {".csv", ".xlsx"}:
        table = pd.read_csv(source, dtype=str, encoding=args.encoding) if suffix == ".csv" else pd.read_excel(source, dtype=str, sheet_name=args.sheet or 0)
        if not args.source_crs:
            raise ValueError("Tabular coordinates require --source-crs")
        if args.geometry_column:
            if args.geometry_column not in table.columns:
                raise ValueError("Geometry column not found")
            geometry = gpd.GeoSeries.from_wkt(table.pop(args.geometry_column), crs=args.source_crs)
        else:
            if not args.x_column or not args.y_column:
                raise ValueError("Coordinate table requires --x-column and --y-column")
            geometry = gpd.points_from_xy(pd.to_numeric(table[args.x_column], errors="raise"),
                                          pd.to_numeric(table[args.y_column], errors="raise"), crs=args.source_crs)
        frame = gpd.GeoDataFrame(table, geometry=geometry, crs=args.source_crs)
    else:
        input_path = "zip://" + str(source) if source.name.lower().endswith(".shp.zip") else str(source)
        layers = pyogrio.list_layers(input_path)
        if len(layers) > 1 and not args.layer:
            raise ValueError("Multiple geographic layers: choose --layer NAME")
        frame = gpd.read_file(input_path, engine="pyogrio", layer=args.layer or layers[0][0])
        if args.source_crs:
            if frame.crs and not CRS(frame.crs).equals(CRS(args.source_crs)):
                raise ValueError("--source-crs conflicts with dataset metadata")
            frame = frame.set_crs(args.source_crs)
    if frame.empty or frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("Dataset has no features or has missing/empty geometries")
    if frame.crs is None:
        raise ValueError("Source CRS unknown; specify --source-crs")
    destination_crs = args.target_crs or ("EPSG:4326" if target in {"geojson", "kml", "gpx"} else frame.crs)
    if target in {"geojson", "kml", "gpx"} and not CRS(destination_crs).equals(CRS("EPSG:4326")):
        raise ValueError("GeoJSON/KML/GPX output requires WGS84; choose another format for projected coordinates")
    frame = frame.to_crs(destination_crs)
    warnings = []
    if target in {"csv", "xlsx"}:
        if "geometry_wkt" in frame.columns:
            raise ValueError("Dataset already contains geometry_wkt; rename it before export")
        table = pd.DataFrame(frame.drop(columns=frame.geometry.name))
        table["geometry_wkt"] = frame.geometry.to_wkt()
        from table_formats import write_tables
        rows = [list(table.columns)] + table.values.tolist()
        outputs = write_tables([(source.stem, rows)], workspace, target, args)
        warnings.append("Geometry exported as WKT; restore using CRS " + str(frame.crs))
        return outputs, warnings, "geographic_attribute_table_written"
    driver = GIS_DRIVERS.get(target)
    if not driver or "w" not in pyogrio.list_drivers().get(driver, ""):
        raise ValueError("Geographic output driver unavailable")
    if target == "shp.zip":
        bad = [name for name in frame.columns if name != frame.geometry.name and
               (len(name.encode("utf-8")) > 10 or frame[name].apply(lambda value: isinstance(value, (dict, list))).any())]
        if bad:
            raise ValueError("Shapefile cannot preserve these field names/types: " + ", ".join(bad))
        data_dir = workspace / "shape"
        data_dir.mkdir()
        dataset = data_dir / "converted.shp"
    else:
        dataset = workspace / f"converted.{target}"
    if target == "gpx":
        if not set(frame.geometry.geom_type).issubset({"Point", "LineString", "MultiLineString"}):
            raise ValueError("GPX supports points and track/route lines, not polygon geometries")
        if len(frame.columns) > 1:
            if not args.allow_layout_loss:
                raise ValueError("GPX attribute mapping needs --allow-layout-loss; only geometry will be retained")
            frame = frame[[frame.geometry.name]].copy()
            warnings.append("GPX export retains geometry only")
    frame.to_file(dataset, driver=driver, engine="pyogrio", encoding="UTF-8")
    checked = gpd.read_file(dataset, engine="pyogrio")
    if len(checked) != len(frame):
        raise ValueError("Geographic feature count changed")
    if checked.crs is None or not CRS(checked.crs).equals(CRS(frame.crs)):
        raise ValueError("Geographic CRS verification failed")
    restored_columns = {str(name).casefold() for name in checked.columns if name != checked.geometry.name}
    missing = [name for name in frame.columns if name != frame.geometry.name and str(name).casefold() not in restored_columns]
    if missing:
        if not args.allow_layout_loss:
            raise ValueError("Target drops geographic attributes; choose --allow-layout-loss: " + ", ".join(missing))
        warnings.append("Attributes omitted by target: " + ", ".join(missing))
    if target == "shp.zip":
        output = workspace / "converted.shp.zip"
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in sorted(dataset.parent.iterdir()):
                archive.write(item, item.name)
    else:
        output = dataset
    warnings.append("Geographic export verified feature count and CRS; symbology is not retained")
    return [output], warnings, "geographic_features_and_crs_reopened"
