/**
 * Source ISIS header: isis/src/control/objs/InterestOperatorFactory/InterestOperatorFactory.h
 * Source class: InterestOperatorFactory
 * Source header author(s): not explicitly stated in upstream header
 * Binding author: Geng Xun
 * Created: 2026-03-27
 * Updated: 2026-03-27
 *
 * Purpose: Expose InterestOperatorFactory static factory method for creating InterestOperator instances from PVL configuration
 */

// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

#include <memory>

#include <pybind11/pybind11.h>

#include "InterestOperator.h"
#include "InterestOperatorFactory.h"
#include "Pvl.h"

namespace py = pybind11;

/**
 * @brief Bindings for InterestOperatorFactory class
 *
 * This factory class provides a static method for creating InterestOperator instances
 * from PVL configuration. The factory pattern allows runtime selection of concrete
 * InterestOperator subclasses based on the configuration provided.
 *
 * @param m The pybind11 module to which the InterestOperatorFactory bindings will be added.
 *
 * @note The create method returns a pointer to an InterestOperator object. The return
 * value policy is set to take_ownership since the factory creates a new instance that
 * Python should manage. The factory itself uses py::nodelete since it only contains
 * static methods and should never be instantiated or deleted.
 *
 * @author Geng Xun
 * @date 2026-03-27
 */
void bind_interest_operator_factory(py::module_ &m) {
  py::class_<Isis::InterestOperatorFactory,
             std::unique_ptr<Isis::InterestOperatorFactory, py::nodelete>>(m, "InterestOperatorFactory")
      .def_static("create",
                  [](Isis::Pvl &pvl) -> Isis::InterestOperator * {
                    return Isis::InterestOperatorFactory::Create(pvl);
                  },
                  py::arg("pvl"),
                  py::return_value_policy::take_ownership,
                  "Create an InterestOperator instance from PVL configuration.\n\n"
                  "Parameters\n"
                  "----------\n"
                  "pvl : Pvl\n"
                  "    PVL object containing InterestOperator configuration\n\n"
                  "Returns\n"
                  "-------\n"
                  "InterestOperator\n"
                  "    Pointer to the created InterestOperator instance\n\n"
                  "Raises\n"
                  "------\n"
                  "IException\n"
                  "    If the PVL configuration is invalid or operator type is unknown");
}
