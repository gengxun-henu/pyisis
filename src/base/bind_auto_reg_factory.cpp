/**
 * Source ISIS header: isis/src/base/objs/AutoRegFactory/AutoRegFactory.h
 * Source class: AutoRegFactory
 * Source header author(s): Jeff Anderson (2005-05-04 original author per header)
 * Binding author: Geng Xun
 * Created: 2026-04-03
 * Updated: 2026-04-03
 *
 * Purpose: Expose AutoRegFactory static factory method for creating AutoReg instances from PVL configuration
 */

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>

#include <pybind11/pybind11.h>

#include "AutoReg.h"
#include "AutoRegFactory.h"
#include "Pvl.h"

namespace py = pybind11;

/**
 * @brief Bindings for AutoRegFactory class
 *
 * This factory class provides a static method for creating AutoReg instances
 * from PVL configuration. The factory pattern allows runtime selection of concrete
 * AutoReg subclasses (MaximumCorrelation, MinimumDifference, Gruen, AdaptiveGruen)
 * based on the PVL configuration provided.
 *
 * @param m The pybind11 module to which the AutoRegFactory bindings will be added.
 *
 * @note The create method returns a pointer to an AutoReg object. The return
 * value policy is set to take_ownership since the factory creates a new instance that
 * Python should manage. The factory itself uses py::nodelete since it only contains
 * static methods and should never be instantiated or deleted.
 *
 * @author Geng Xun
 * @date 2026-04-03
 */
void bind_auto_reg_factory(py::module_ &m) {
  py::class_<Isis::AutoRegFactory,
             std::unique_ptr<Isis::AutoRegFactory, py::nodelete>>(m, "AutoRegFactory")
      .def_static("create",
                  [](Isis::Pvl &pvl) -> Isis::AutoReg * {
                    return Isis::AutoRegFactory::Create(pvl);
                  },
                  py::arg("pvl"),
                  py::return_value_policy::take_ownership,
                  "Create an AutoReg instance from PVL configuration.\n\n"
                  "Parameters\n"
                  "----------\n"
                  "pvl : Pvl\n"
                  "    PVL object containing AutoRegistration configuration.\n"
                  "    Must include an Algorithm group with Name keyword specifying\n"
                  "    the registration algorithm (e.g., MaximumCorrelation,\n"
                  "    MinimumDifference, Gruen, AdaptiveGruen), PatternChip group\n"
                  "    with chip dimensions, and SearchChip group with search area.\n\n"
                  "Returns\n"
                  "-------\n"
                  "AutoReg\n"
                  "    Pointer to the created AutoReg instance (concrete subclass)\n\n"
                  "Raises\n"
                  "------\n"
                  "IException\n"
                  "    If the PVL configuration is invalid, required groups/keywords\n"
                  "    are missing, or the algorithm type is unknown");
}
