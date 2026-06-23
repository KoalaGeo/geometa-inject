import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List
import yaml

class MCFParser:
    """Parses pygeometa-compliant MCF YAML files into a usable dictionary."""
    def __init__(self, mcf_path: str):
        if not os.path.exists(mcf_path):
            raise FileNotFoundError(f"MCF file not found: {mcf_path}")
        with open(mcf_path, 'r', encoding='utf-8') as f:
            self.data: Dict[str, Any] = yaml.safe_load(f)

    @property
    def title(self) -> str:
        return self.data.get('identification', {}).get('title', 'Untitled Dataset')

    @property
    def abstract(self) -> str:
        return self.data.get('identification', {}).get('abstract', '')

    @property
    def keywords(self) -> List[str]:
        kw_dict = self.data.get('identification', {}).get('keywords', {})
        return kw_dict.get('default', {}).get('keywords', [])

    @property
    def topic_category(self) -> str:
        cats = self.data.get('identification', {}).get('topiccategory', [])
        return cats[0] if cats else 'geoscientificInformation'

    @property
    def organization(self) -> str:
        return self.data.get('contact', {}).get('pointOfContact', {}).get('organization', '')

    @property
    def contact_name(self) -> str:
        return self.data.get('contact', {}).get('pointOfContact', {}).get('individualname', '')

    @property
    def contact_email(self) -> str:
        return self.data.get('contact', {}).get('pointOfContact', {}).get('email', '')

    @property
    def online_resource(self) -> str:
        return self.data.get('metadata', {}).get('dataseturi', '')


class GeoPackageInjector:
    """Handles the injection of standard QGIS/ISO metadata into GeoPackage SQLite tables."""
    
    @staticmethod
    def _generate_qgis_xml(mcf: MCFParser) -> str:
        """Constructs the QGIS XML payload from the MCF data."""
        kw_xml = "".join([f"<keyword>{k}</keyword>" for k in mcf.keywords])
        current_dt = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Simplified for brevity - you can drop in your full QGIS XML template here
        return f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.44.0">
  <identifier>{mcf.title}</identifier>
  <title>{mcf.title}</title>
  <abstract>{mcf.abstract}</abstract>
  <keywords vocabulary="Search keys">{kw_xml}</keywords>
  <keywords vocabulary="gmd:topicCategory">
    <keyword>{mcf.topic_category}</keyword>
  </keywords>
  <contact>
    <name>{mcf.contact_name}</name>
    <organization>{mcf.organization}</organization>
    <email>{mcf.contact_email}</email>
  </contact>
  <links>
    <link url="{mcf.online_resource}" type="WWW:LINK" name="Product Webpage"/>
  </links>
  <dates>
    <date value="{current_dt}" type="Created"/>
  </dates>
</qgis>"""

    @classmethod
    def inject(cls, gpkg_path: str, table_name: str, mcf: MCFParser) -> None:
        if not os.path.exists(gpkg_path):
            raise FileNotFoundError(f"GeoPackage not found: {gpkg_path}")
            
        xml_content = cls._generate_qgis_xml(mcf)
        
        try:
            with sqlite3.connect(gpkg_path) as conn:
                cursor = conn.cursor()
                
                # 1. Ensure tables exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS gpkg_metadata (
                        id INTEGER NOT NULL PRIMARY KEY,
                        md_scope TEXT NOT NULL DEFAULT 'dataset',
                        md_standard_uri TEXT NOT NULL DEFAULT 'http://mrcc.com/qgis.dtd',
                        mime_type TEXT NOT NULL DEFAULT 'text/xml',
                        metadata TEXT NOT NULL
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS gpkg_metadata_reference (
                        reference_scope TEXT NOT NULL,
                        table_name TEXT,
                        column_name TEXT,
                        row_id_value INTEGER,
                        timestamp DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                        md_file_id INTEGER NOT NULL,
                        md_parent_id INTEGER
                    );
                """)

                # 2. Insert metadata
                cursor.execute(
                    "INSERT INTO gpkg_metadata (md_scope, metadata) VALUES (?, ?)",
                    ("dataset", xml_content)
                )
                metadata_id = cursor.lastrowid

                # 3. Update gpkg_contents description
                cursor.execute(
                    "UPDATE gpkg_contents SET description = ? WHERE table_name = ?",
                    (mcf.abstract, table_name)
                )

                # 4. Link metadata to table
                cursor.execute(
                    "INSERT INTO gpkg_metadata_reference (reference_scope, table_name, md_file_id) VALUES (?, ?, ?)",
                    ("table", table_name, metadata_id)
                )
                
        except sqlite3.Error as e:
            print(f"SQLite error during GeoPackage injection: {e}")


class ShapefileInjector:
    """Handles the creation of ESRI-compliant Shapefile XML metadata."""
    
    @classmethod
    def inject(cls, shp_path: str, mcf: MCFParser) -> None:
        if not shp_path.lower().endswith('.shp'):
            raise ValueError("Target file must be a .shp file")
            
        xml_path = shp_path + ".xml"
        current_dt = datetime.now()
        
        root = ET.Element("metadata", {"xml:lang": "en"})

        # Esri Block
        esri = ET.SubElement(root, "Esri")
        ET.SubElement(esri, "CreaDate").text = current_dt.strftime("%Y%m%d")
        ET.SubElement(esri, "CreaTime").text = current_dt.strftime("%H%M")
        ET.SubElement(esri, "ArcGISFormat").text = "1.0"
        ET.SubElement(esri, "SyncOnce").text = "TRUE"

        # Data Identification Info
        dataIdInfo = ET.SubElement(root, "dataIdInfo")
        
        idCitation = ET.SubElement(dataIdInfo, "idCitation")
        ET.SubElement(idCitation, "resTitle").text = mcf.title
        
        ET.SubElement(dataIdInfo, "idAbs").text = mcf.abstract
        ET.SubElement(dataIdInfo, "idCredit").text = mcf.organization

        search_keys = ET.SubElement(dataIdInfo, "searchKeys")
        for k in mcf.keywords:
            ET.SubElement(search_keys, "keyword").text = k
        ET.SubElement(search_keys, "keyword").text = mcf.topic_category

        # Point of Contact
        idPoC = ET.SubElement(dataIdInfo, "idPoC")
        ET.SubElement(idPoC, "rpIndName").text = mcf.contact_name
        ET.SubElement(idPoC, "rpOrgName").text = mcf.organization
        rpCntInfo = ET.SubElement(idPoC, "rpCntInfo")
        cntAddress = ET.SubElement(rpCntInfo, "cntAddress")
        ET.SubElement(cntAddress, "eMailAdd").text = mcf.contact_email
        cntOnlineRes = ET.SubElement(rpCntInfo, "cntOnlineRes")
        ET.SubElement(cntOnlineRes, "linkage").text = mcf.online_resource

        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)


class MetadataManager:
    """Facade for managing metadata injection across formats."""
    def __init__(self, mcf_path: str):
        self.mcf = MCFParser(mcf_path)

    def apply_to_gpkg(self, gpkg_path: str, table_name: str) -> None:
        """Applies MCF metadata to a GeoPackage."""
        GeoPackageInjector.inject(gpkg_path, table_name, self.mcf)
        print(f"Successfully injected metadata into {gpkg_path} (Layer: {table_name})")

    def apply_to_shapefile(self, shp_path: str) -> None:
        """Generates an ESRI XML metadata file for a Shapefile."""
        ShapefileInjector.inject(shp_path, self.mcf)
        print(f"Successfully created Shapefile metadata at {shp_path}.xml")