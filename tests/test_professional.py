import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "convert.py"
spec = importlib.util.spec_from_file_location("professional_converter", SCRIPT)
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class ProfessionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.available = converter.capabilities()

    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="converter-professional-")
        self.root = Path(self.workspace.name)

    def tearDown(self):
        self.assertEqual(list(self.root.glob(".file-converter-*")), [])
        self.workspace.cleanup()

    def convert(self, source, target, **options):
        original = hashlib.sha256(source.read_bytes()).hexdigest()
        try:
            return converter.convert(source, argparse.Namespace(format=target, **options), self.available)
        finally:
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original)

    def test_blender_scene_exports_and_reimports(self):
        if not self.available["professional"]["blender"]:
            self.skipTest("Blender unavailable")
        import trimesh
        source = self.root / "scene.glb"
        trimesh.Scene(trimesh.creation.box(extents=(2, 3, 4))).export(source)
        for target in ["obj", "stl", "ply", "gltf", "fbx", "blend", "png"]:
            with self.subTest(target=target):
                result = self.convert(source, target, allow_layout_loss=True)
                self.assertGreater(Path(result["output"]).stat().st_size, 0)
                if target == "gltf":
                    payload = json.loads(Path(result["output"]).read_text(encoding="utf-8"))
                    self.assertTrue(all(item.get("uri", "data:").startswith("data:") for item in payload.get("buffers", [])))
                elif target == "png":
                    from PIL import Image
                    with Image.open(result["output"]) as image:
                        self.assertEqual(image.size, (512, 512))

    def test_mesh_fallback_and_unsupported_engine_discovery(self):
        import trimesh
        source = self.root / "mesh.off"
        trimesh.creation.box().export(source)
        result = self.convert(source, "stl", allow_layout_loss=True)
        mesh = trimesh.load_mesh(result["output"])
        self.assertEqual(len(mesh.faces), 12)
        self.assertNotIn("fbx", converter.targets_for(source, self.available))

    def test_dxf_conversion_and_rendering(self):
        import ezdxf
        source = self.root / "drawing.dxf"
        document = ezdxf.new("R2018")
        document.modelspace().add_lwpolyline([(0, 0), (100, 0), (100, 60), (0, 60)], close=True)
        document.modelspace().add_circle((50, 30), 15)
        document.modelspace().add_text("CAD test", dxfattribs={"height": 5, "insert": (10, 70)})
        document.saveas(source)
        for target in ["dxf", "svg", "pdf", "png"]:
            with self.subTest(target=target):
                result = self.convert(source, target)
                self.assertGreater(Path(result["output"]).stat().st_size, 0)
        if not self.available["professional"]["oda"]:
            with self.assertRaisesRegex(ValueError, "ODA"):
                self.convert(source, "dwg")

    def geographic_source(self, name="places.geojson"):
        import geopandas as gpd
        from shapely.geometry import Point
        source = self.root / name
        gpd.GeoDataFrame({"code": ["0001", "0002"], "name": ["上海", "北京"]},
                         geometry=[Point(121.47, 31.23), Point(116.40, 39.90)], crs="EPSG:4326").to_file(source, driver="GeoJSON")
        return source

    def test_geographic_formats_and_shapefile_bundle(self):
        import geopandas as gpd
        source = self.geographic_source()
        for target in ["gpkg", "fgb", "geojson", "shp.zip", "kml", "csv", "xlsx"]:
            if target in {"kml", "fgb"} and target not in self.available["professional"]["gis_write_targets"]:
                continue
            with self.subTest(target=target):
                result = self.convert(source, target, allow_layout_loss=True)
                output = Path(result["output"])
                if target == "shp.zip":
                    with zipfile.ZipFile(output) as archive:
                        self.assertTrue(any(name.endswith(".prj") for name in archive.namelist()))
                        self.assertTrue(any(name.endswith(".dbf") for name in archive.namelist()))
                    restored = self.convert(output, "geojson")
                    self.assertEqual(len(gpd.read_file(restored["output"])), 2)
                elif target not in {"csv", "xlsx"}:
                    self.assertEqual(len(gpd.read_file(output)), 2)

    def test_geographic_reprojection_and_coordinate_csv(self):
        import geopandas as gpd
        from pyproj import CRS
        source = self.geographic_source()
        projected = Path(self.convert(source, "gpkg", target_crs="EPSG:3857")["output"])
        self.assertTrue(CRS(gpd.read_file(projected).crs).equals(CRS("EPSG:3857")))
        restored = Path(self.convert(projected, "geojson")["output"])
        point = gpd.read_file(restored).geometry.iloc[0]
        self.assertAlmostEqual(point.x, 121.47, places=5)
        self.assertAlmostEqual(point.y, 31.23, places=5)
        coordinates = self.root / "coordinates.csv"
        coordinates.write_text("id,lon,lat\n0001,121.47,31.23\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source-crs"):
            self.convert(coordinates, "geojson", x_column="lon", y_column="lat")
        converted = self.convert(coordinates, "geojson", x_column="lon", y_column="lat", source_crs="EPSG:4326")
        self.assertEqual(gpd.read_file(converted["output"])["id"].iloc[0], "0001")

    def test_geographic_layers_and_shapefile_field_limits(self):
        import geopandas as gpd
        from shapely.geometry import Point
        source = self.root / "layers.gpkg"
        frame = gpd.GeoDataFrame({"code": ["a"]}, geometry=[Point(0, 0)], crs="EPSG:4326")
        frame.to_file(source, layer="one", driver="GPKG")
        frame.to_file(source, layer="two", driver="GPKG")
        with self.assertRaisesRegex(ValueError, "Multiple geographic layers"):
            self.convert(source, "geojson")
        self.convert(source, "geojson", layer="two")
        named = self.root / "long.geojson"
        frame.rename(columns={"code": "a_very_long_field_name"}).to_file(named, driver="GeoJSON")
        with self.assertRaisesRegex(ValueError, "Shapefile cannot preserve"):
            self.convert(named, "shp.zip")

    def test_font_collection_requires_index(self):
        from fontTools.ttLib import TTCollection, TTFont
        font = Path("C:/Windows/Fonts/arial.ttf")
        if not font.exists():
            self.skipTest("Font fixture unavailable")
        source = self.root / "collection.ttc"
        collection = TTCollection()
        collection.fonts = [TTFont(font), TTFont(font)]
        collection.save(source)
        collection.close()
        with self.assertRaisesRegex(ValueError, "font-index"):
            self.convert(source, "woff2")
        result = self.convert(source, "woff2", font_index=1)
        with TTFont(result["output"]) as restored, TTFont(font) as original:
            self.assertEqual(restored.getGlyphOrder(), original.getGlyphOrder())


if __name__ == "__main__":
    unittest.main()
