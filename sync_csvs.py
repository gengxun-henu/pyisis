#!/usr/bin/env python3
"""
Sync class_bind_methods_details CSVs against actual binding code.
For each CSV row with Bound=="N", check if the method is actually bound in code.
If so, change to "Y" with a note.
"""
import csv
import re
import os
import sys

DATE_NOTE = "2026-04-11 台账同步"

# Map: (csv_path, source_file, class_pattern_in_code)
# class_pattern_in_code is a regex to find the py::class_ or py::enum_ block
TASKS = [
    ("class_bind_methods_details/base_chip_methods.csv",
     "src/base/bind_base_pattern.cpp", "Chip"),
    ("class_bind_methods_details/base_kernels_methods.csv",
     "src/base/bind_base_filters.cpp", "Kernels"),
    ("class_bind_methods_details/base_universal_ground_map_methods.csv",
     "src/base/bind_base_ground_map.cpp", "UniversalGroundMap"),
    ("class_bind_methods_details/base_iexception_methods.csv",
     "src/base/bind_base_support.cpp", "IException"),
    ("class_bind_methods_details/base_i_exception_methods.csv",
     "src/base/bind_base_support.cpp", "IException"),
    ("class_bind_methods_details/control_bundle_control_point_methods.csv",
     "src/control/bind_bundle_advanced.cpp", "BundleControlPoint"),
    ("class_bind_methods_details/control_bundle_solution_info_methods.csv",
     "src/control/bind_bundle_advanced.cpp", "BundleSolutionInfo"),
    ("class_bind_methods_details/control_bundle_results_methods.csv",
     "src/control/bind_bundle_advanced.cpp", "BundleResults"),
    ("class_bind_methods_details/control_bundle_target_body_methods.csv",
     "src/control/bind_control_core.cpp", "BundleTargetBody"),
    ("class_bind_methods_details/control_control_net_valid_measure_methods.csv",
     "src/control/bind_control_core.cpp", "ControlNetValidMeasure"),
    ("class_bind_methods_details/base_pvl_methods.csv",
     "src/base/bind_base_pvl.cpp", "Pvl"),
    ("class_bind_methods_details/base_pvl_object_methods.csv",
     "src/base/bind_base_pvl.cpp", "PvlObject"),
    ("class_bind_methods_details/base_pvl_container_methods.csv",
     "src/base/bind_base_pvl.cpp", "PvlContainer"),
    ("class_bind_methods_details/base_pvl_keyword_methods.csv",
     "src/base/bind_base_pvl.cpp", "PvlKeyword"),
    ("class_bind_methods_details/base_text_file_methods.csv",
     "src/base/bind_base_utility.cpp", "TextFile"),
    ("class_bind_methods_details/base_stretch_methods.csv",
     "src/base/bind_base_filters.cpp", "Stretch"),
    ("class_bind_methods_details/base_camera_methods.csv",
     "src/bind_camera.cpp", "Camera"),
    ("class_bind_methods_details/base_spice_position_methods.csv",
     "src/bind_spice_navigation.cpp", "SpicePosition"),
    ("class_bind_methods_details/base_spice_rotation_methods.csv",
     "src/bind_spice_navigation.cpp", "SpiceRotation"),
    ("class_bind_methods_details/base_table_methods.csv",
     "src/bind_low_level_cube_io.cpp", "Table"),
    ("class_bind_methods_details/base_table_field_methods.csv",
     "src/bind_low_level_cube_io.cpp", "TableField"),
    ("class_bind_methods_details/base_table_record_methods.csv",
     "src/bind_low_level_cube_io.cpp", "TableRecord"),
    ("class_bind_methods_details/base_surface_point_methods.csv",
     "src/base/bind_base_shape_support.cpp", "SurfacePoint"),
    ("class_bind_methods_details/control_control_measure_methods.csv",
     "src/control/bind_control_core.cpp", "ControlMeasure"),
    ("class_bind_methods_details/control_control_net_methods.csv",
     "src/control/bind_control_core.cpp", "ControlNet"),
    ("class_bind_methods_details/base_cube_methods.csv",
     "src/bind_low_level_cube_io.cpp", "Cube"),
    ("class_bind_methods_details/base_process_import_methods.csv",
     "src/bind_high_level_cube_io.cpp", "ProcessImport"),
    ("class_bind_methods_details/base_process_by_brick_methods.csv",
     "src/bind_high_level_cube_io.cpp", "ProcessByBrick"),
    ("class_bind_methods_details/base_overlap_statistics_methods.csv",
     "src/base/bind_base_image_overlap.cpp", "OverlapStatistics"),
    ("class_bind_methods_details/base_image_overlap_methods.csv",
     "src/base/bind_base_image_overlap.cpp", "ImageOverlap"),
    ("class_bind_methods_details/base_image_overlap_set_methods.csv",
     "src/base/bind_base_image_overlap.cpp", "ImageOverlapSet"),
]

def to_snake_case(name):
    """Convert CamelCase to snake_case for matching."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def extract_bound_symbols(source_code):
    """Extract all bound Python-side names from .def(), py::init, py::enum_, py::class_ etc."""
    symbols = set()
    
    # .def("name", ...) - method definitions
    for m in re.finditer(r'\.def\(\s*"([^"]+)"', source_code):
        symbols.add(m.group(1))
    
    # .def_static("name", ...)
    for m in re.finditer(r'\.def_static\(\s*"([^"]+)"', source_code):
        symbols.add(m.group(1))
    
    # .def_property("name", ...) and .def_property_readonly("name", ...)
    for m in re.finditer(r'\.def_property(?:_readonly)?\(\s*"([^"]+)"', source_code):
        symbols.add(m.group(1))
    
    # .def_readwrite("name", ...) and .def_readonly("name", ...)
    for m in re.finditer(r'\.def_read(?:write|only)\(\s*"([^"]+)"', source_code):
        symbols.add(m.group(1))
    
    # py::init constructors
    if re.search(r'py::init', source_code):
        symbols.add('__init__')
    
    # py::enum_ values - .value("Name", ...)
    for m in re.finditer(r'\.value\(\s*"([^"]+)"', source_code):
        symbols.add(m.group(1))
    
    # __repr__, __str__, __len__, __getitem__, __setitem__ etc
    for m in re.finditer(r'\.def\(\s*"(__\w+__)"', source_code):
        symbols.add(m.group(1))
    
    return symbols

def extract_class_block(source_code, class_name):
    """Try to extract the binding block for a specific class.
    Returns the full source if we can't isolate it - better to over-match than under-match."""
    # Look for py::class_<...ClassName...> or py::enum_<...ClassName...>
    # Just return the full source - matching across blocks is complex and we want thoroughness
    return source_code

def build_name_variants(cpp_method_name):
    """Build possible Python-side names for a C++ method name."""
    variants = set()
    variants.add(cpp_method_name)
    variants.add(cpp_method_name.lower())
    snake = to_snake_case(cpp_method_name)
    variants.add(snake)
    # Common patterns
    if cpp_method_name.startswith("get") or cpp_method_name.startswith("Get"):
        stripped = cpp_method_name[3:]
        variants.add(to_snake_case(stripped))
        variants.add(stripped.lower())
    if cpp_method_name.startswith("set") or cpp_method_name.startswith("Set"):
        stripped = cpp_method_name[3:]
        variants.add("set_" + to_snake_case(stripped))
        variants.add(to_snake_case(cpp_method_name))
    if cpp_method_name.startswith("is") or cpp_method_name.startswith("Is"):
        stripped = cpp_method_name[2:]
        variants.add("is_" + to_snake_case(stripped))
        variants.add(to_snake_case(cpp_method_name))
    if cpp_method_name.startswith("has") or cpp_method_name.startswith("Has"):
        stripped = cpp_method_name[3:]
        variants.add("has_" + to_snake_case(stripped))
        variants.add(to_snake_case(cpp_method_name))
    # Specific known mappings
    variants.add(cpp_method_name.replace("::", "_"))
    return variants

def check_method_bound(cpp_method_name, method_type, bound_symbols, source_code, class_name):
    """Check if a method is bound in the source code."""
    # Class Symbol check
    if method_type and "Class Symbol" in method_type:
        pat = rf'py::class_\s*<[^>]*{re.escape(class_name)}'
        if re.search(pat, source_code):
            return True
        return False
    
    # Enum check
    if method_type and ("enum" in method_type.lower() or "Enum" in method_type):
        pat = rf'py::enum_\s*<[^>]*{re.escape(class_name)}'
        if re.search(pat, source_code):
            return True
        # Also check for enum values
        return False
    
    # Constructor
    if cpp_method_name in ("Constructor", "constructor", class_name) or \
       (method_type and "constructor" in method_type.lower()):
        if re.search(r'py::init', source_code):
            return True
        return False
    
    # Destructor
    if cpp_method_name in ("Destructor", "destructor", "~" + class_name):
        return False  # typically not bound
    
    # operator overloads
    if cpp_method_name.startswith("operator"):
        op_map = {
            "operator==": "__eq__",
            "operator!=": "__ne__",
            "operator<": "__lt__",
            "operator>": "__gt__",
            "operator<=": "__le__",
            "operator>=": "__ge__",
            "operator+": "__add__",
            "operator-": "__sub__",
            "operator*": "__mul__",
            "operator/": "__truediv__",
            "operator[]": "__getitem__",
            "operator()": "__call__",
            "operator<<": "__lshift__",
            "operator>>": "__rshift__",
        }
        for op, pyname in op_map.items():
            if op in cpp_method_name and pyname in bound_symbols:
                return True
        return False
    
    # Regular methods - check variants
    variants = build_name_variants(cpp_method_name)
    for v in variants:
        if v in bound_symbols:
            return True
    
    # Also do a direct search in source for the method name (catches lambdas etc.)
    # Search for the C++ method name being called within a .def block
    if re.search(rf'&\w*::{re.escape(cpp_method_name)}\b', source_code):
        return True
    
    return False

def process_csv(csv_path, source_file, class_name):
    """Process a single CSV file."""
    if not os.path.exists(csv_path):
        print(f"SKIP: {csv_path} not found")
        return 0
    if not os.path.exists(source_file):
        print(f"SKIP: {source_file} not found")
        return 0
    
    with open(source_file, 'r') as f:
        source_code = f.read()
    
    bound_symbols = extract_bound_symbols(source_code)
    
    # Read CSV
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) < 2:
        print(f"SKIP: {csv_path} too few rows")
        return 0
    
    header = rows[0]
    
    # Find column indices
    method_col = None
    bound_col = None
    notes_col = None
    type_col = None
    
    for i, h in enumerate(header):
        hl = h.strip().lower()
        if hl in ('method', 'method_name', 'methodname', 'name', 'method name'):
            method_col = i
        elif hl in ('bound', 'bound?', 'is_bound', 'bound_status', 'pybind_bound'):
            bound_col = i
        elif hl in ('notes', 'note', 'comment', 'comments', 'remark', 'remarks'):
            notes_col = i
        elif hl in ('type', 'method_type', 'category'):
            type_col = i
    
    if method_col is None:
        # Try first column
        method_col = 0
    if bound_col is None:
        # Search more aggressively
        for i, h in enumerate(header):
            if 'bound' in h.lower() or 'status' in h.lower():
                bound_col = i
                break
    if notes_col is None:
        for i, h in enumerate(header):
            if 'note' in h.lower() or 'comment' in h.lower() or 'remark' in h.lower():
                notes_col = i
                break
    
    if bound_col is None:
        print(f"SKIP: {csv_path} - no 'Bound' column found. Headers: {header}")
        return 0
    
    changes = 0
    for row_idx in range(1, len(rows)):
        row = rows[row_idx]
        if len(row) <= bound_col:
            continue
        
        current_bound = row[bound_col].strip()
        if current_bound.upper() == 'Y':
            continue  # Already marked
        if current_bound.upper() not in ('N', 'NO', ''):
            continue  # Skip special statuses
        
        method_name = row[method_col].strip() if len(row) > method_col else ""
        method_type = row[type_col].strip() if type_col is not None and len(row) > type_col else ""
        
        if not method_name:
            continue
        
        if check_method_bound(method_name, method_type, bound_symbols, source_code, class_name):
            row[bound_col] = 'Y'
            note = f"{DATE_NOTE}；已在 {source_file} 暴露"
            if notes_col is not None and len(row) > notes_col:
                existing = row[notes_col].strip()
                if existing:
                    row[notes_col] = existing + "; " + note
                else:
                    row[notes_col] = note
            elif notes_col is not None:
                while len(row) <= notes_col:
                    row.append("")
                row[notes_col] = note
            rows[row_idx] = row
            changes += 1
            print(f"  {class_name}.{method_name}: N -> Y")
    
    if changes > 0:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"  Updated {csv_path}: {changes} methods marked Y")
    else:
        print(f"  {csv_path}: no changes needed")
    
    return changes

# Main
total_changes = 0
for csv_path, source_file, class_name in TASKS:
    print(f"\n=== {class_name} ({csv_path}) ===")
    changes = process_csv(csv_path, source_file, class_name)
    total_changes += changes

print(f"\n=== TOTAL: {total_changes} methods updated N->Y ===")
