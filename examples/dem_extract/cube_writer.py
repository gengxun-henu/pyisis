"""ISIS Cube writer helpers for DEM rasters."""

from __future__ import annotations

from pathlib import Path

from .grid import RasterResult


def preflight_cube_writer_bindings(ip) -> list[str]:
    missing: list[str] = []
    for name in ("Cube", "LineManager"):
        if not hasattr(ip, name):
            missing.append(name)
    cube_type = getattr(ip, "Cube", None)
    if cube_type is not None:
        for name in ("set_dimensions", "set_pixel_type", "create", "put_group", "write"):
            if not hasattr(cube_type, name):
                missing.append(f"Cube.{name}")
    pixel_type = getattr(ip, "PixelType", None)
    if pixel_type is None or not hasattr(pixel_type, "Real"):
        missing.append("PixelType.Real")
    return missing


def _copy_mapping_group(template_cube, output_cube) -> None:
    try:
        mapping = template_cube.group("Mapping")
    except Exception as exc:
        raise RuntimeError("Template cube does not expose a readable Mapping group.") from exc
    output_cube.put_group(mapping)


def write_radius_cube(ip, template_cube, output_path: str | Path, raster: RasterResult) -> None:
    missing = preflight_cube_writer_bindings(ip)
    if missing:
        raise RuntimeError(f"isis_pybind is missing required Cube writer bindings: {', '.join(missing)}")
    output_cube = ip.Cube()
    output_cube.set_dimensions(len(raster.values[0]) if raster.values else 0, len(raster.values), 1)
    output_cube.set_pixel_type(ip.PixelType.Real)
    output_cube.create(str(output_path))
    try:
        _copy_mapping_group(template_cube, output_cube)
        for line_index, row in enumerate(raster.values, start=1):
            line_manager = ip.LineManager(output_cube, False)
            if hasattr(line_manager, "set_line"):
                line_manager.set_line(line_index, 1)
            for sample_index, value in enumerate(row):
                line_manager[sample_index] = float(value)
            output_cube.write(line_manager)
    finally:
        if hasattr(output_cube, "close"):
            output_cube.close()
