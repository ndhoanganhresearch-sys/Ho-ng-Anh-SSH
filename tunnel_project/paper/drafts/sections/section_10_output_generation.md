## 10. Output Generation

The pipeline closes the loop from scan to deliverable by producing three output products from the same `PipelineContext`: an IFC Building Information Model, a PDF inspection report, and structured CSV/Excel workbooks. Generating all three from one state object keeps the model, the report, and the tabular data consistent by construction.

### 10.1 IFC Building Information Model

The exporter (`ifc_exporter.py`) writes an IFC model through ifcopenshell. It supports both IFC4 (the default) and the infrastructure schema IFC4X3 [29]; when IFC4X3 is selected, the tunnel centerline is written as an `IfcAlignment`, the native alignment entity of the infrastructure schema, and degrades to an `IfcAnnotation` polyline under IFC4. Each cross-section is exported as an `IfcBuildingElementProxy` carrying its measured properties, and the deformed lining is written as a continuous tessellated shell (`IfcPolygonalFaceSet`). Section status drives surface colour through RGB styles for the three severity levels, so the deformation pattern is legible directly in any IFC viewer. In a representative export the model contained 40 section proxies on a valid IFC4X3 alignment, a deformation shell of 3,840 vertices, and component placeholders for cable runs and lighting, demonstrating that the geometric results transfer into a standard BIM exchange format.

### 10.2 PDF inspection report

The report generator (`pdf_reporter.py`) composes a multi-page document with ReportLab, using matplotlib for the embedded charts. The report opens with a cover and a summary of the global parameters, followed by per-section deformation plots (height, width, and ovality against chainage, laid out several sections per page), a per-section data table, and a list of flagged warnings. A separate routine emits a work-order PDF that pairs each flagged section with its recommended action. A representative report rendered to a valid 117 KB PDF in the smoke test.

### 10.3 Structured data export

For downstream analysis the exporter also writes CSV and multi-sheet Excel workbooks containing the global summary metrics and the full per-section table (chainage, radii, widths, heights, ovality, eccentricity, clearance, and warning status). The structured export is the machine-readable counterpart of the PDF, suitable for ingestion into asset-management systems or for longitudinal study across survey campaigns.
