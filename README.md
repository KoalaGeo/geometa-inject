# geometa-inject

**A lightweight, zero-dependency Python utility for injecting Pygeometa Metadata Control Files (MCF) directly into geospatial distribution formats.**

---

## 📖 Overview

When building automated geospatial data pipelines (such as generating H3 discrete global grid aggregations), managing hardcoded XML metadata strings inside processing logic becomes difficult to maintain. 

`geometa-inject` solves this by decoupling metadata from your geoprocessing scripts. It reads an OSGeo Metadata Control File (MCF) formatted in YAML and natively injects it into standard spatial file formats. 

### Key Features
* **GeoPackage (`.gpkg`):** Injects QGIS/ISO compliant XML directly into the standard OGC `gpkg_metadata` and `gpkg_metadata_reference` SQLite tables using native Python `sqlite3`.
* **ESRI Shapefile (`.shp`):** Generates standard ArcGIS-compliant `.shp.xml` sidecar files using `xml.etree.ElementTree`.
* **Zero Heavy Dependencies:** Relies entirely on the Python Standard Library and `PyYAML`. No GDAL, ArcPy, or QGIS installations are required.
* **`pycsw` Aligned:** Uses the same YAML MCF structure natively understood by `pygeometa` and `pycsw`, creating a single source of truth for both file distribution and catalogue publishing.

---

## ⚙️ Installation

You can install this package locally into your environment. From the root of the repository, run:

```bash
pip install .

```

*Requirements:* Python 3.8+ and `PyYAML`.

---

## 🚀 Quickstart

### 1. Create your MCF YAML File (`dataset_meta.yml`)

Create a single, easily updatable YAML file that holds all your dataset's metadata.

```yaml
mcf:
  version: 1.0
metadata:
  identifier: example_dataset_v1
  language: eng
  dataseturi: [https://example.com/dataset/](https://example.com/dataset/)
identification:
  title: Example Spatial Dataset V1
  abstract: A comprehensive spatial dataset aggregated to an H3 Hexagonal Grid.
  keywords:
    default:
      keywords:
        - spatial
        - H3
        - open data
  topiccategory:
    - geoscientificInformation
contact:
  pointOfContact:
    organization: Your Organization
    individualname: Data Manager
    email: data@example.com

```

### 2. Inject into your Spatial Data

In your spatial processing script, initialize the `MetadataManager` and apply the metadata to your exported files.

```python
from geometa_inject import MetadataManager
import geopandas as gpd

# ... your spatial processing logic ...
gpkg_path = "output/example_dataset_v1.gpkg"
layer_name = "example_layer"
shp_path = "output/example_dataset_v1.shp"

# Export geometries
gdf.to_file(gpkg_path, driver="GPKG", layer=layer_name)
gdf.to_file(shp_path, driver="ESRI Shapefile")

# Initialize the Metadata Injector
meta_manager = MetadataManager("config/dataset_meta.yml")

# Inject standard metadata seamlessly
meta_manager.apply_to_gpkg(gpkg_path, layer_name)
meta_manager.apply_to_shapefile(shp_path)

print("Metadata injection complete!")

```

---

## 🏗️ Architecture & Upstream Roadmap

This tool operates as a localized "writer/injector" for the MCF ecosystem.

Currently, `geometa-inject` is built as a standalone utility to immediately unblock data production pipelines. In the future, the goal is to propose this functionality upstream as a Pull Request to the core `pygeometa` repository (e.g., as a `pygeometa.injectors` module), allowing the broader open-source geospatial community to natively embed MCF data into physical database files.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome. If you find edge cases in specific GIS software parsers (e.g., specific quirks in how ArcGIS Pro reads the `.shp.xml` or how QGIS renders the SQLite payload), please open an issue!

```

```