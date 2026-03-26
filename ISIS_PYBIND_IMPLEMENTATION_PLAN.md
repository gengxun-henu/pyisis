# USGS ISIS 9.0.0 Pybind11 Implementation Plan

**Project**: PyISIS - Python bindings for USGS ISIS (Integrated Software for Imagers and Spectrometers)
**Version**: ISIS 9.0.0
**Binding Technology**: pybind11
**Date**: 2026-03-26
**Status**: Detailed Implementation Roadmap

---

## Executive Summary

This document outlines a comprehensive implementation plan for creating Python bindings for USGS ISIS 9.0.0 using pybind11. The plan prioritizes **non-GUI classes** and follows a **directory-based approach** (base → control → mission), focusing on classes that provide the most value to Python users while ensuring comprehensive unit test coverage based on existing C++ tests.

### Current Progress
- **Total ISIS Classes**: 314 (tracked in `todo_pybind11.csv`)
- **Already Converted**: 107 classes (34%)
- **Remaining**: 168 classes (53%)
- **Skipped** (abstract/Qt-heavy): ~39 classes (13%)

### Implementation Strategy
1. **Base Directory First**: Complete foundational classes (Math, Utility, Parsing, Statistics, Pattern Matching)
2. **Control Directory**: Focus on control network and bundle adjustment classes
3. **Mission Directory**: Implement mission-specific cameras (LRO, Hayabusa2, etc.)
4. **Non-GUI Only**: Exclude classes with heavy Qt signal/slot dependencies
5. **Unit Tests**: Create Python unit tests based on existing C++ tests

---

## Phase 1: Base Directory Classes

The base directory contains foundational classes used throughout ISIS. Priority is given to classes that are frequently used and have minimal dependencies.

### 1.1 Math Classes (Priority: HIGH)

**Remaining Classes**: 15 classes

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `LeastSquares` | HIGH | 未转换 | Medium | Core math functionality for fitting |
| `Matrix` | HIGH | 未转换 | Medium | Linear algebra operations |
| `PolynomialUnivariate` | HIGH | 未转换 | Low | 1D polynomial operations |
| `PolynomialBivariate` | HIGH | 未转换 | Low | 2D polynomial operations |
| `NthOrderPolynomial` | MEDIUM | 未转换 | Low | General polynomial class |
| `NumericalApproximation` | MEDIUM | 未转换 | Medium | Abstract base - expose concrete methods |
| `InfixToPostfix` | MEDIUM | 未转换 | Low | Expression parsing |
| `InlineInfixToPostfix` | MEDIUM | 未转换 | Low | Optimized expression parsing |
| `CubeInfixToPostfix` | LOW | 未转换 | Medium | Cube-specific expression parsing |
| `CubeCalculator` | LOW | 未转换 | Medium | Cube-specific calculations |
| `FunctionTools` | LOW | 未转换 | Medium | Abstract base - helper utilities |
| `MaximumLikelihoodWFunctions` | LOW | 未转换 | High | Statistical modeling |
| `NumericalAtmosApprox` | LOW | 未转换 | Medium | Atmospheric approximation |
| `SurfaceModel` | LOW | 未转换 | High | Surface modeling |
| `Basis1VariableFunction` | LOW | 未转换 | Low | Abstract base |

**Implementation File**: `src/base/bind_base_math.cpp` (extend existing)

**Test File**: `tests/unitTest/math_unit_test.py` (extend existing)

**Estimated Effort**: 3-4 weeks

---

### 1.2 Utility Classes (Priority: HIGH)

**Remaining Classes**: 16 classes

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `Stretch` | HIGH | 未转换 | Medium | Abstract base - image stretching |
| `GaussianStretch` | HIGH | 未转换 | Low | Gaussian-based stretch |
| `Kernels` | HIGH | 未转换 | Medium | SPICE kernel management |
| `CSVReader` | HIGH | 未转换 | Low | CSV file parsing |
| `TextFile` | HIGH | 未转换 | Low | Text file I/O |
| `EndianSwapper` | MEDIUM | 未转换 | Low | Byte order conversion |
| `LineEquation` | MEDIUM | 未转换 | Low | 2D line operations |
| `Pixel` | MEDIUM | 未转换 | Low | Pixel coordinate class |
| `PolygonTools` | MEDIUM | 未转换 | Medium | Polygon geometry utilities |
| `ID` | LOW | 未转换 | Low | Unique identifier generator |
| `Selection` | LOW | 未转换 | Low | Abstract base - selection interface |
| `SparseBlockMatrix` | LOW | 未转换 | High | Sparse matrix operations |
| `CubeStretch` | LOW | 未转换 | Medium | Cube-specific stretching |
| `ExportPdsTable` | LOW | 未转换 | Medium | PDS table export |
| `ImportPdsTable` | LOW | 未转换 | Medium | PDS table import |
| `GSLUtility` | LOW | 未转换 | Medium | GSL wrapper utilities |
| `Area3D` | LOW | 未转换 | Low | 3D area calculations |

**Implementation File**: `src/base/bind_base_utility.cpp` (extend existing)

**Test File**: `tests/unitTest/utility_unit_test.py` (extend existing)

**Estimated Effort**: 3-4 weeks

---

### 1.3 Parsing Classes (Priority: HIGH)

**Remaining Classes**: 13 classes

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `FileList` | HIGH | 未转换 | Low | File list management |
| `IString` | HIGH | 未转换 | Low | ISIS string utilities |
| `PvlFormat` | MEDIUM | 未转换 | Medium | PVL formatting |
| `PvlFormatPds` | MEDIUM | 未转换 | Medium | PDS-specific PVL format |
| `PvlSequence` | MEDIUM | 未转换 | Low | PVL sequence handling |
| `PvlToken` | MEDIUM | 未转换 | Low | PVL tokenization |
| `PvlTokenizer` | MEDIUM | 未转换 | Medium | PVL tokenizer |
| `LabelTranslationManager` | MEDIUM | 未转换 | Medium | Abstract base - label translation |
| `PvlToPvlTranslationManager` | MEDIUM | 未转换 | Medium | PVL-to-PVL translation |
| `PvlToXmlTranslationManager` | MEDIUM | 未转换 | Medium | PVL-to-XML translation |
| `XmlToPvlTranslationManager` | MEDIUM | 未转换 | Medium | XML-to-PVL translation |
| `PvlTranslationTable` | MEDIUM | 未转换 | Medium | Translation table management |

**Implementation File**: `src/base/bind_base_parsing.cpp` (new file)

**Test File**: `tests/unitTest/parsing_unit_test.py` (new file)

**Estimated Effort**: 2-3 weeks

---

### 1.4 Statistics Classes (Priority: MEDIUM)

**Remaining Classes**: 5 classes

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `QuickFilter` | HIGH | 未转换 | Low | Fast filtering operations |
| `OverlapStatistics` | MEDIUM | 未转换 | Medium | Overlap region statistics |
| `PrincipalComponentAnalysis` | MEDIUM | 未转换 | High | PCA implementation |
| `FourierTransform` | MEDIUM | 未转换 | High | FFT operations |
| `StatCumProbDistDynCalc` | LOW | 未转换 | High | Qt-heavy, statistical distribution |

**Implementation File**: `src/bind_statistics.cpp` (extend existing)

**Test File**: `tests/unitTest/statistics_unit_test.py` (extend existing)

**Estimated Effort**: 2-3 weeks

---

### 1.5 Pattern Matching Classes (Priority: MEDIUM)

**Remaining Classes**: 17 classes

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `Chip` | HIGH | 未转换 | Medium | Image chip extraction |
| `AutoReg` | HIGH | 未转换 | High | Abstract base - auto-registration |
| `Gruen` | HIGH | 未转换 | High | Gruen matching algorithm |
| `AdaptiveGruen` | HIGH | 未转换 | High | Adaptive Gruen algorithm |
| `MaximumCorrelation` | MEDIUM | 未转换 | Medium | Max correlation matcher |
| `MinimumDifference` | MEDIUM | 未转换 | Medium | Min difference matcher |
| `ImagePolygon` | MEDIUM | 未转换 | Medium | Image polygon geometry |
| `ImageOverlapSet` | MEDIUM | 未转换 | Medium | Overlap set management |
| `AutoRegFactory` | MEDIUM | 未转换 | Low | Factory for AutoReg |
| `PolygonSeeder` | MEDIUM | 未转换 | Medium | Abstract base - polygon seeding |
| `GridPolygonSeeder` | MEDIUM | 未转换 | Low | Grid-based seeding |
| `LimitPolygonSeeder` | MEDIUM | 未转换 | Low | Limited seeding |
| `StripPolygonSeeder` | MEDIUM | 未转换 | Low | Strip-based seeding |
| `PolygonSeederFactory` | LOW | 未转换 | Low | Factory for PolygonSeeder |
| `AtmosModelFactory` | LOW | 未转换 | Low | Factory for AtmosModel |
| `NormModelFactory` | LOW | 未转换 | Low | Factory for NormModel |
| `PhotoModelFactory` | LOW | 未转换 | Low | Factory for PhotoModel |

**Implementation File**: `src/base/bind_base_pattern.cpp` (extend existing)

**Test File**: `tests/unitTest/pattern_unit_test.py` (extend existing)

**Estimated Effort**: 4-5 weeks

---

### 1.6 Low-Level Cube I/O Classes (Priority: MEDIUM)

**Remaining Classes**: 10 classes

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `BoxcarManager` | MEDIUM | 未转换 | Low | Boxcar data management |
| `OriginalLabel` | MEDIUM | 未转换 | Low | Original label handling |
| `OriginalXmlLabel` | MEDIUM | 未转换 | Low | XML label handling |
| `Blobber` | LOW | 未转换 | Medium | Abstract base - blob operations |
| `CubeBsqHandler` | LOW | 未转换 | High | BSQ format handler |
| `CubeTileHandler` | LOW | 未转换 | High | Tile format handler |
| `CubeIoHandler` | LOW | 未转换 | High | Abstract base - I/O handler |
| `CubeCachingAlgorithm` | LOW | 未转换 | High | Abstract base - caching |
| `RawCubeChunk` | LOW | 未转换 | High | Raw chunk management |
| `RegionalCachingAlgorithm` | LOW | 未转换 | High | Regional caching |

**Implementation File**: `src/bind_low_level_cube_io.cpp` (extend existing)

**Test File**: `tests/unitTest/low_level_cube_io_unit_test.py` (extend existing)

**Estimated Effort**: 3-4 weeks

---

### 1.7 High-Level Cube I/O Classes (Priority: MEDIUM)

**Remaining Classes**: 17 classes

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `JP2Exporter` | HIGH | 未转换 | Medium | JPEG2000 export |
| `JP2Importer` | HIGH | 未转换 | Medium | JPEG2000 import |
| `SubArea` | MEDIUM | 未转换 | Medium | Sub-area extraction |
| `ProcessExport` | MEDIUM | 未转换 | High | Abstract base - export processing |
| `ProcessExportPds` | MEDIUM | 未转换 | High | PDS export processing |
| `ProcessMapMosaic` | MEDIUM | 未转换 | High | Map mosaic processing |
| `ProcessMosaic` | MEDIUM | 未转换 | High | General mosaic processing |
| `ProcessPolygons` | MEDIUM | 未转换 | High | Polygon processing |
| `ProcessRubberSheet` | MEDIUM | 未转换 | High | Rubber sheet transformation |
| `ProcessGroundPolygons` | LOW | 未转换 | High | Ground polygon processing |
| `ImageExporter` | LOW | 未转换 | High | Abstract base - image export |
| `ImageImporter` | LOW | 未转换 | High | Abstract base - image import |
| `StreamExporter` | LOW | 未转换 | High | Abstract base - stream export |
| `TiffExporter` | LOW | 未转换 | Medium | TIFF export |
| `TiffImporter` | LOW | 未转换 | Medium | TIFF import |
| `QtExporter` | LOW | 未转换 | Medium | Qt-based export |
| `QtImporter` | LOW | 未转换 | Medium | Qt-based import |

**Implementation File**: `src/bind_high_level_cube_io.cpp` (extend existing)

**Test File**: `tests/unitTest/high_level_cube_io_unit_test.py` (extend existing)

**Estimated Effort**: 4-5 weeks

---

### 1.8 Radiometric and Photometric Correction Classes (Priority: LOW)

**Remaining Classes**: 12 classes

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `PhotoModel` | MEDIUM | 未转换 | High | Abstract base - photometric model |
| `AtmosModel` | MEDIUM | 未转换 | High | Abstract base - atmospheric model |
| `Hapke` | MEDIUM | 未转换 | High | Hapke photometric model |
| `HapkeAtm1` | MEDIUM | 未转换 | High | Hapke atmospheric model 1 |
| `HapkeAtm2` | MEDIUM | 未转换 | High | Hapke atmospheric model 2 |
| `AlbedoAtm` | LOW | 未转换 | Medium | Albedo atmospheric correction |
| `Anisotropic1` | LOW | 未转换 | Medium | Anisotropic model 1 |
| `Anisotropic2` | LOW | 未转换 | Medium | Anisotropic model 2 |
| `Isotropic1` | LOW | 未转换 | Medium | Isotropic model 1 |
| `Isotropic2` | LOW | 未转换 | Medium | Isotropic model 2 |
| `ShadeAtm` | LOW | 未转换 | Medium | Shade atmospheric correction |
| `TopoAtm` | LOW | 未转换 | Medium | Topographic atmospheric correction |

**Implementation File**: `src/base/bind_base_photometric.cpp` (new file)

**Test File**: `tests/unitTest/photometric_unit_test.py` (new file)

**Estimated Effort**: 3-4 weeks

---

## Phase 2: Control Directory Classes

Control network classes are essential for photogrammetric processing and bundle adjustment.

### 2.1 Control Network Core Classes (Priority: HIGH)

**Remaining Classes**: 21 classes

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `BundleControlPoint` | HIGH | 未转换 | High | Control point for bundle adjustment |
| `BundleMeasure` | HIGH | 未转换 | High | Measurement in bundle adjustment (Qt-heavy) |
| `BundleObservationVector` | HIGH | 未转换 | Medium | Vector of observations |
| `ControlNetFilter` | HIGH | 未转换 | Medium | Control network filtering |
| `ControlNetStatistics` | HIGH | 未转换 | Medium | Network statistics |
| `ControlNetValidMeasure` | HIGH | 未转换 | Medium | Measure validation |
| `ControlNetVersioner` | MEDIUM | 未转换 | Medium | Version management |
| `ImageOverlap` | MEDIUM | 未转换 | Medium | Image overlap analysis |
| `LidarControlPoint` | MEDIUM | 未转换 | Medium | LIDAR control points |
| `BundleLidarControlPoint` | MEDIUM | 未转换 | Medium | LIDAR bundle control point |
| `BundleLidarPointVector` | MEDIUM | 未转换 | Medium | Vector of LIDAR points |
| `BundleLidarRangeConstraint` | MEDIUM | 未转换 | Medium | LIDAR range constraints |
| `IsisBundleObservation` | MEDIUM | 未转换 | High | ISIS bundle observation |
| `CsmBundleObservation` | MEDIUM | 未转换 | High | CSM bundle observation |
| `InterestOperator` | LOW | 未转换 | High | Abstract base - interest detection |
| `InterestOperatorFactory` | LOW | 未转换 | Low | Factory for InterestOperator |
| `BundleAdjust` | SKIP | 未转换 | Very High | Qt-heavy, complex signals/slots |
| `BundleObservation` | SKIP | 未转换 | High | Abstract base with complex inheritance |
| `BundleResults` | SKIP | 未转换 | High | Qt-heavy results class |
| `BundleSolutionInfo` | SKIP | 未转换 | High | Qt-heavy solution info |
| `ControlNetVitals` | SKIP | 未转换 | High | Qt-heavy vitals monitoring |

**Implementation File**: `src/control/bind_control_core.cpp` (extend existing)

**Test File**: `tests/unitTest/control_core_unit_test.py` (extend existing)

**Estimated Effort**: 5-6 weeks

---

## Phase 3: Mission Directory Classes

Mission-specific camera models, prioritizing LRO and Hayabusa2 as requested.

### 3.1 LRO (Lunar Reconnaissance Orbiter) Classes (Priority: HIGHEST)

**Mission**: LRO
**Instruments**: LROC (NAC, WAC), Mini-RF

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `LroNarrowAngleCamera` | HIGH | To Add | High | LROC NAC camera model |
| `LroWideAngleCamera` | HIGH | To Add | High | LROC WAC camera model |
| `LroNarrowAngleDistortionMap` | MEDIUM | To Add | Medium | NAC distortion model |
| `LroWideAngleDistortionMap` | MEDIUM | To Add | Medium | WAC distortion model |
| `LroNarrowAngleSumming` | MEDIUM | To Add | Medium | NAC summing modes |
| `LroWideAngleSumming` | MEDIUM | To Add | Medium | WAC summing modes |
| `MiniRF` | MEDIUM | To Add | High | Mini-RF radar camera |

**Implementation File**: `src/mission/bind_lro_cameras.cpp` (new file)

**Test File**: `tests/unitTest/lro_camera_unit_test.py` (new file)

**Estimated Effort**: 3-4 weeks

**Note**: LRO camera classes need to be researched in the ISIS source code. They may be named differently (e.g., `LrocNarrowAngleCamera`, `LrocWideAngleCamera`).

---

### 3.2 Hayabusa2 Classes (Priority: HIGHEST)

**Mission**: Hayabusa2
**Instruments**: ONC (Optical Navigation Camera)

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `Hayabusa2OncCamera` | HIGH | To Add | High | ONC camera model |
| `Hayabusa2OncDistortionMap` | MEDIUM | To Add | Medium | ONC distortion model |
| `Hayabusa2NirsCamera` | MEDIUM | To Add | High | NIRS3 camera (if applicable) |

**Implementation File**: `src/mission/bind_hayabusa2_cameras.cpp` (new file)

**Test File**: `tests/unitTest/hayabusa2_camera_unit_test.py` (new file)

**Estimated Effort**: 2-3 weeks

**Note**: Hayabusa2 camera classes need to be researched in the ISIS source code to determine exact class names and availability.

---

### 3.3 Other Mission Classes (Priority: MEDIUM)

**Already Bound Missions** (extend as needed):
- Mars Express (HRSC) ✓
- Mars Global Surveyor (MOC) ✓
- Mars Reconnaissance Orbiter (HiRISE, CTX, CRISM, MARCI) ✓
- MESSENGER (MDIS) ✓
- NEAR Shoemaker (MSI) ✓
- Trace Gas Orbiter (CaSSIS) ✓

**Mars Reconnaissance Orbiter - Remaining Classes**: 24 classes

Most MRO classes are related to HiRISE calibration and are low priority for initial bindings:

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `MocLabels` | LOW | 未转换 | Medium | MOC label parsing |
| `MocNarrowAngleSumming` | LOW | 未转换 | Medium | MOC NAC summing |
| `MocWideAngleDetectorMap` | LOW | 未转换 | Medium | MOC WAC detector map |
| `MocWideAngleDistortionMap` | LOW | 未转换 | Medium | MOC WAC distortion |
| HiRISE Calibration Classes | SKIP | 未转换 | Very High | Complex calibration pipeline (20 classes) |

**Estimated Effort**: 2-3 weeks (for high-priority classes only)

---

## Phase 4: Camera and Sensor Classes

Additional camera and sensor support classes.

### 4.1 Spice, Instruments, and Cameras (Priority: MEDIUM)

**Remaining Classes**: Camera detector maps, ground maps, and specialized cameras

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `IrregularBodyCameraGroundMap` | MEDIUM | 未转换 | High | Irregular body mapping |
| `PushFrameCameraCcdLayout` | MEDIUM | 未转换 | Medium | Push-frame CCD layout |
| `PushFrameCameraDetectorMap` | MEDIUM | 未转换 | Medium | Push-frame detector mapping |
| `PushFrameCameraGroundMap` | MEDIUM | 未转换 | Medium | Push-frame ground mapping |
| `ReseauDistortionMap` | MEDIUM | 未转换 | Medium | Reseau distortion correction |
| `RollingShutterCameraDetectorMap` | MEDIUM | 未转换 | Medium | Rolling shutter detector |
| `VariableLineScanCameraDetectorMap` | MEDIUM | 未转换 | Medium | Variable line scan detector |
| `RadarGroundMap` | MEDIUM | 未转换 | High | Radar ground mapping |
| `RadarGroundRangeMap` | MEDIUM | 未转换 | High | Radar range mapping |
| `RadarPulseMap` | MEDIUM | 未转换 | Medium | Radar pulse mapping |
| `RadarSkyMap` | MEDIUM | 未转换 | High | Radar sky mapping |
| `RadarSlantRangeMap` | MEDIUM | 未转换 | High | Radar slant range |
| `Quaternion` | MEDIUM | 未转换 | Medium | Quaternion math for rotations |
| `SpacecraftPosition` | MEDIUM | 未转换 | High | Spacecraft position |
| `SpicePosition` | MEDIUM | 未转换 | High | SPICE position |
| `SpiceRotation` | MEDIUM | 未转换 | High | SPICE rotation |
| `Spice` | SKIP | 未转换 | Very High | Qt-heavy, complex SPICE interface |
| `CameraStatistics` | LOW | 未转换 | Medium | Camera statistics |
| `CSMSkyMap` | LOW | 未转换 | Medium | CSM sky mapping |
| `PixelFOV` | LOW | 未转换 | Medium | Pixel field of view |
| `LightTimeCorrectionState` | LOW | 未转换 | Low | Light time correction |

**Implementation File**: `src/bind_camera_maps.cpp` (extend existing)

**Test File**: `tests/unitTest/camera_maps_unit_test.py` (extend existing)

**Estimated Effort**: 4-5 weeks

---

## Phase 5: System and Miscellaneous Classes

### 5.1 System Classes (Priority: LOW)

| Class | Priority | Status | Complexity | Notes |
|-------|----------|--------|------------|-------|
| `Plugin` | LOW | 未转换 | Medium | Plugin system |

**Implementation File**: `src/base/bind_base_system.cpp` (new file)

**Test File**: `tests/unitTest/system_unit_test.py` (new file)

**Estimated Effort**: 1 week

---

### 5.2 SensorUtilities Classes (Priority: LOW)

These classes are from a separate SensorUtilities library and have low priority:

**Remaining Classes**: 12 lightweight value classes and abstract bases

**Estimated Effort**: 2-3 weeks (if needed)

---

## Implementation Guidelines

### File Organization

```
src/
├── base/
│   ├── bind_base_math.cpp           # Math classes
│   ├── bind_base_utility.cpp        # Utility classes
│   ├── bind_base_parsing.cpp        # NEW: Parsing classes
│   ├── bind_base_pattern.cpp        # Pattern matching
│   ├── bind_base_filters.cpp        # Filter classes
│   ├── bind_base_photometric.cpp    # NEW: Photometric models
│   └── bind_base_system.cpp         # NEW: System classes
├── control/
│   ├── bind_control_core.cpp        # Control network classes
│   └── bind_bundle_advanced.cpp     # Advanced bundle (disabled)
├── mission/
│   ├── bind_mission_cameras.cpp     # Existing mission cameras
│   ├── bind_lro_cameras.cpp         # NEW: LRO cameras
│   └── bind_hayabusa2_cameras.cpp   # NEW: Hayabusa2 cameras
├── bind_camera_maps.cpp             # Camera mapping classes
├── bind_statistics.cpp              # Statistics classes
├── bind_low_level_cube_io.cpp       # Low-level I/O
├── bind_high_level_cube_io.cpp      # High-level I/O
└── module.cpp                        # Main module definition
```

### Test Organization

```
tests/unitTest/
├── math_unit_test.py                # Math classes tests
├── utility_unit_test.py             # Utility classes tests
├── parsing_unit_test.py             # NEW: Parsing tests
├── pattern_unit_test.py             # Pattern matching tests
├── filters_unit_test.py             # Filter tests
├── photometric_unit_test.py         # NEW: Photometric tests
├── control_core_unit_test.py        # Control network tests
├── lro_camera_unit_test.py          # NEW: LRO camera tests
├── hayabusa2_camera_unit_test.py    # NEW: Hayabusa2 tests
├── camera_maps_unit_test.py         # Camera mapping tests
├── statistics_unit_test.py          # Statistics tests
├── low_level_cube_io_unit_test.py   # Low-level I/O tests
├── high_level_cube_io_unit_test.py  # High-level I/O tests
└── _unit_test_support.py            # Shared test utilities
```

---

## Coding Standards

### 1. File Header Template

```cpp
// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @file
 * @brief Pybind11 bindings for ISIS [category] classes
 *
 * Source ISIS headers:
 *   - isis/src/[path]/[ClassName]/[ClassName].h
 * Binding author: [Author Name]
 * Created: [Date]
 * Purpose: [Brief description]
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "[ClassName].h"
#include "helpers.h"

namespace py = pybind11;
```

### 2. Binding Patterns

**Simple Class**:
```cpp
py::class_<Isis::ClassName>(m, "ClassName")
    .def(py::init<>())
    .def("method_name", &Isis::ClassName::MethodName, "Docstring");
```

**QString Conversion** (use helpers):
```cpp
#include "helpers.h"

.def("get_name", [](const Isis::ClassName &self) {
    return qStringToStdString(self.Name());
})
.def("set_name", [](Isis::ClassName &self, const std::string &name) {
    self.SetName(stdStringToQString(name));
})
```

**QVector to std::vector**:
```cpp
std::vector<double> qVectorToStdVector(const QVector<double> &qvec) {
    return std::vector<double>(qvec.begin(), qvec.end());
}
```

### 3. Unit Test Patterns

```python
import unittest
from _unit_test_support import ip

class ClassNameUnitTest(unittest.TestCase):
    """Test suite for ClassName bindings"""

    def test_construction(self):
        """Test basic construction"""
        obj = ip.ClassName()
        self.assertIsNotNone(obj)

    def test_method_name(self):
        """Test method_name functionality"""
        obj = ip.ClassName()
        result = obj.method_name()
        self.assertEqual(result, expected_value)

if __name__ == '__main__':
    unittest.main()
```

### 4. Documentation

- Every class binding must include a docstring
- Every method must include a parameter description and return value
- Complex methods should include usage examples in comments

---

## Testing Strategy

### Unit Test Requirements

1. **Based on C++ Tests**: Python unit tests should mirror existing ISIS C++ unit tests
2. **Comprehensive Coverage**:
   - Constructor tests
   - Accessor/mutator tests
   - Core functionality tests
   - Edge case and error handling tests
3. **Test Data**: Use existing ISIS test data from `$ISISDATA/testData` when available
4. **Isolation**: Each test class should be independent
5. **Documentation**: Each test method should have a docstring explaining what it tests

### Test Discovery

All tests must be discoverable by:
```bash
python -m unittest discover -s tests/unitTest -p "*_unit_test.py" -v
```

---

## Priority Implementation Order

### Tier 1 (Highest Priority - Complete First)
1. **Math Classes**: LeastSquares, Matrix, Polynomial classes (3-4 weeks)
2. **Utility Classes**: Stretch, Kernels, CSVReader, TextFile (3-4 weeks)
3. **Parsing Classes**: FileList, IString, PVL classes (2-3 weeks)
4. **LRO Cameras**: LROC NAC/WAC (3-4 weeks)
5. **Hayabusa2 Cameras**: ONC camera (2-3 weeks)

**Total Tier 1 Estimated Effort**: 13-18 weeks (~3-4.5 months)

### Tier 2 (Medium Priority)
1. **Statistics Classes**: QuickFilter, OverlapStatistics (2-3 weeks)
2. **Pattern Matching**: Chip, AutoReg, Gruen (4-5 weeks)
3. **Control Network**: BundleControlPoint, filters, statistics (5-6 weeks)
4. **Low-Level I/O**: BoxcarManager, OriginalLabel (3-4 weeks)

**Total Tier 2 Estimated Effort**: 14-18 weeks (~3.5-4.5 months)

### Tier 3 (Lower Priority)
1. **High-Level I/O**: JP2 Import/Export, SubArea (4-5 weeks)
2. **Photometric Models**: Hapke, atmospheric models (3-4 weeks)
3. **Camera Maps**: Detector/ground/sky maps (4-5 weeks)
4. **System Classes**: Plugin (1 week)

**Total Tier 3 Estimated Effort**: 12-15 weeks (~3-3.75 months)

---

## Dependencies and Blockers

### Known Issues

1. **bind_bundle_advanced.cpp**: Currently disabled due to complex dependencies
   - Need to resolve QSharedPointer issues
   - May require updating ISIS version or adjusting holder types

2. **Qt Dependencies**: Many classes use Qt signal/slot mechanisms
   - These are marked as SKIP in the plan
   - Alternative: Provide minimal interface without signals

3. **Abstract Base Classes**: Some classes are pure virtual
   - Expose only instantiable derived classes
   - Document abstract classes in comments

### External Dependencies

- **ISIS 9.0.0**: Must be installed in conda environment
- **ISISDATA**: Required for many unit tests
- **SPICE Kernels**: Required for camera and SPICE-related tests
- **Test Data**: Mission-specific test cubes needed for camera tests

---

## Resource Requirements

### Development Environment

- ISIS 9.0.0 installed via conda (`isis=9.0.0`)
- Python 3.9+ with pybind11
- CMake 3.18+
- C++17 compiler (g++ or clang++)
- Qt 5.x development libraries

### Test Data

- ISIS test data (`$ISISDATA/testData`)
- Mission-specific cubes:
  - LRO: LROC NAC/WAC cubes
  - Hayabusa2: ONC cubes
  - MRO: HiRISE, CTX cubes (already available)

### Documentation

- ISIS C++ API documentation
- pybind11 documentation
- Mission instrument specifications

---

## Success Criteria

1. **Code Coverage**: All non-GUI, non-abstract classes bound (target: 85%+ of applicable classes)
2. **Test Coverage**: All bound classes have comprehensive unit tests (target: 90%+ code coverage)
3. **Documentation**: All classes and methods documented with docstrings
4. **Build System**: Clean CMake build with no warnings
5. **CI/CD**: All tests pass in GitHub Actions
6. **Performance**: Python bindings have minimal overhead compared to C++

---

## Timeline Estimate

| Phase | Duration | Classes | Cumulative Progress |
|-------|----------|---------|---------------------|
| Phase 1.1-1.3 (Base: Math, Utility, Parsing) | 8-11 weeks | 44 classes | 44/168 (26%) |
| Phase 3.1-3.2 (LRO, Hayabusa2) | 5-7 weeks | 10-15 classes | 59/168 (35%) |
| Phase 1.4-1.5 (Statistics, Pattern) | 6-8 weeks | 22 classes | 81/168 (48%) |
| Phase 2.1 (Control Networks) | 5-6 weeks | 15 classes | 96/168 (57%) |
| Phase 1.6-1.7 (Cube I/O) | 7-9 weeks | 27 classes | 123/168 (73%) |
| Phase 1.8 (Photometric) | 3-4 weeks | 12 classes | 135/168 (80%) |
| Phase 4.1 (Camera/Sensor) | 4-5 weeks | 21 classes | 156/168 (93%) |
| Phase 5 (System/Misc) | 3-4 weeks | 12 classes | 168/168 (100%) |

**Total Estimated Duration**: 41-54 weeks (~10-13.5 months)

**Tier 1 Completion** (highest value): 13-18 weeks (~3-4.5 months)

---

## Appendix A: Class Status Summary

### By Category

| Category | Total | Converted | Remaining | % Complete |
|----------|-------|-----------|-----------|------------|
| Math | 17 | 2 | 15 | 12% |
| Utility | 18 | 2 | 16 | 11% |
| Parsing | 14 | 1 | 13 | 7% |
| Statistics | 7 | 2 | 5 | 29% |
| Pattern Matching | 19 | 2 | 17 | 11% |
| Low-Level Cube I/O | 18 | 8 | 10 | 44% |
| High-Level Cube I/O | 29 | 12 | 17 | 41% |
| Control Networks | 28 | 7 | 21 | 25% |
| Map Projection | 22 | 22 | 0 | 100% ✓ |
| Spice/Camera | 31 | 10 | 21 | 32% |
| Radiometric/Photometric | 12 | 0 | 12 | 0% |
| Mars Missions | 34 | 10 | 24 | 29% |
| Other Missions | 4 | 4 | 0 | 100% ✓ |
| SensorUtilities | 12 | 0 | 12 | 0% |
| System | 1 | 0 | 1 | 0% |
| **TOTAL** | **314** | **107** | **168** | **34%** |

---

## Appendix B: Skipped Classes (Qt-Heavy/Abstract)

Classes marked as SKIP due to heavy Qt dependencies or purely abstract interfaces:

1. BundleAdjust (Qt signals/slots)
2. BundleResults (Qt signals/slots)
3. BundleSolutionInfo (Qt signals/slots)
4. ControlNetVitals (Qt signals/slots)
5. Spice (Qt signals/slots)
6. StatCumProbDistDynCalc (Qt signals/slots)
7. BundleObservation (pure virtual, complex)
8. Multiple HiRISE calibration classes (specialized, complex)

Total: ~39 classes

---

## Appendix C: Reference Files

- **Progress Log**: `pybind_progress_log.md`
- **Class Inventory**: `todo_pybind11.csv`
- **Method Details**: `class_bind_methods_details/*.csv` (312 files)
- **Existing Bindings**: `src/base/`, `src/control/`, `src/mission/`
- **Existing Tests**: `tests/unitTest/`
- **CMake Build**: `CMakeLists.txt`

---

## Appendix D: Next Steps

### Immediate Actions (Week 1-2)

1. **Research LRO Classes**: Verify class names and locations in ISIS source
   - Expected location: `isis/src/lro/objs/` or `isis/src/lro/apps/`
   - Look for: `LrocNarrowAngleCamera`, `LrocWideAngleCamera`

2. **Research Hayabusa2 Classes**: Verify availability in ISIS 9.0.0
   - Expected location: `isis/src/hayabusa2/objs/`
   - Look for: `Hayabusa2OncCamera` or similar

3. **Set Up Test Data**: Obtain LRO and Hayabusa2 test cubes
   - LRO LROC NAC: narrow-angle camera cube
   - LRO LROC WAC: wide-angle camera cube
   - Hayabusa2 ONC: optical navigation camera cube

4. **Start Tier 1 Implementation**:
   - Begin with `LeastSquares` class (Math)
   - Create `bind_base_parsing.cpp` and start with `FileList`
   - Research and begin LRO camera bindings

### Weekly Milestones (Suggested)

- **Week 1-2**: Research, setup, LeastSquares, FileList
- **Week 3-4**: Matrix, PolynomialUnivariate, IString
- **Week 5-8**: Remaining Math classes, Stretch, Kernels
- **Week 9-12**: LRO cameras, Hayabusa2 cameras
- **Week 13+**: Continue with Tier 2 classes

---

## Conclusion

This implementation plan provides a comprehensive roadmap for completing Python bindings for USGS ISIS 9.0.0. By following the phased approach prioritizing base classes, control networks, and mission-specific cameras (LRO, Hayabusa2), the project can deliver high-value functionality incrementally while maintaining code quality and test coverage.

The plan is flexible and can be adjusted based on:
- Actual complexity discovered during implementation
- Priority changes from stakeholders
- Availability of test data
- Discovery of blocking dependencies

Regular progress updates should be made to `pybind_progress_log.md` and `todo_pybind11.csv` as classes are completed.

---

**Document Version**: 1.0
**Last Updated**: 2026-03-26
**Author**: Implementation Plan Generated for PyISIS Project
