// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT

/**
 * @file
 * @brief Pybind11 bindings for ISIS math classes
 *
 * Source ISIS headers:
 *   - isis/src/base/objs/Calculator/Calculator.h
 *   - isis/src/base/objs/Affine/Affine.h
 *   - isis/src/base/objs/BasisFunction/BasisFunction.h
 * Binding author: Geng Xun
 * Created: 2026-03-24
 * Purpose: Expose Calculator, Affine, and BasisFunction classes to Python via pybind11.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <cmath>

#include "Calculator.h"
#include "Affine.h"
#include "BasisFunction.h"
#include "LeastSquares.h"
#include "Matrix.h"
#include "PolynomialUnivariate.h"
#include "PolynomialBivariate.h"
#include "Buffer.h"
#include "helpers.h"

namespace py = pybind11;

// Vector conversion functions now provided by helpers.h

void bind_base_math(py::module_ &m)
{
     /**
      * @brief Bindings for the Isis::Calculator class
      * Calculator class provides functionality for performing mathematical operations
      * on image data, including arithmetic, trigonometric, and logical operations.
      * @see Isis::Calculator
      */
     py::class_<Isis::Calculator>(m, "Calculator")
         .def(py::init<>())
         // Stack operations
         .def("push",
              py::overload_cast<double>(&Isis::Calculator::Push),
              py::arg("scalar"),
              "Push a scalar value onto the calculator stack")
         .def("push",
              py::overload_cast<Isis::Buffer &>(&Isis::Calculator::Push),
              py::arg("buffer"),
              "Push a buffer onto the calculator stack")
         .def("push", [](Isis::Calculator &self, const std::vector<double> &vec)
              {
            QVector<double> qvec = stdVectorToQVector(vec);
            self.Push(qvec); }, py::arg("vector"), "Push a vector of values onto the calculator stack")
         .def("pop", [](Isis::Calculator &self, bool keep_specials)
              { return qVectorToStdVector(self.Pop(keep_specials)); }, py::arg("keep_specials") = false, "Pop a vector from the calculator stack")
         .def("empty", &Isis::Calculator::Empty, "Check if the calculator stack is empty")
         .def("clear", &Isis::Calculator::Clear, "Clear the calculator stack")
         .def("print_top", &Isis::Calculator::PrintTop, "Print the top element of the stack")
         // Arithmetic operations
         .def("negative", &Isis::Calculator::Negative, "Negate the top element")
         .def("multiply", &Isis::Calculator::Multiply, "Multiply top two elements")
         .def("add", &Isis::Calculator::Add, "Add top two elements")
         .def("subtract", &Isis::Calculator::Subtract, "Subtract top two elements")
         .def("divide", &Isis::Calculator::Divide, "Divide top two elements")
         .def("modulus", &Isis::Calculator::Modulus, "Compute modulus of top two elements")
         .def("exponent", &Isis::Calculator::Exponent, "Raise to power")
         .def("square_root", &Isis::Calculator::SquareRoot, "Compute square root")
         .def("absolute_value", &Isis::Calculator::AbsoluteValue, "Compute absolute value")
         .def("log", &Isis::Calculator::Log, "Compute natural logarithm")
         .def("log10", &Isis::Calculator::Log10, "Compute base-10 logarithm")
         // Bitwise operations
         .def("left_shift", &Isis::Calculator::LeftShift, "Left shift operation")
         .def("right_shift", &Isis::Calculator::RightShift, "Right shift operation")
         // Min/Max operations
         .def("minimum_pixel", &Isis::Calculator::MinimumPixel, "Get minimum pixel value")
         .def("maximum_pixel", &Isis::Calculator::MaximumPixel, "Get maximum pixel value")
         .def("minimum_line", &Isis::Calculator::MinimumLine, "Get minimum line value")
         .def("maximum_line", &Isis::Calculator::MaximumLine, "Get maximum line value")

         // NOTE: Minimum2() and Maximum2() are not implemented in the ISIS C++ library
         // and cannot be bound until they are added to the upstream source code.
         // See: isis/src/base/objs/Calculator/Calculator.h
         //.def("minimum2", &Isis::Calculator::Minimum2, "Get minimum of top two elements")
         //.def("maximum2", &Isis::Calculator::Maximum2, "Get maximum of top two elements")
         // Comparison operations
         .def("greater_than", &Isis::Calculator::GreaterThan, "Greater than comparison")
         .def("less_than", &Isis::Calculator::LessThan, "Less than comparison")
         .def("equal", &Isis::Calculator::Equal, "Equality comparison")
         .def("less_than_or_equal", &Isis::Calculator::LessThanOrEqual, "Less than or equal comparison")
         .def("greater_than_or_equal", &Isis::Calculator::GreaterThanOrEqual, "Greater than or equal comparison")
         .def("not_equal", &Isis::Calculator::NotEqual, "Not equal comparison")
         // Logical operations
         .def("and_", &Isis::Calculator::And, "Logical AND")
         .def("or_", &Isis::Calculator::Or, "Logical OR")
         // Trigonometric operations
         .def("sine", &Isis::Calculator::Sine, "Compute sine")
         .def("cosine", &Isis::Calculator::Cosine, "Compute cosine")
         .def("tangent", &Isis::Calculator::Tangent, "Compute tangent")
         .def("secant", &Isis::Calculator::Secant, "Compute secant")
         .def("cosecant", &Isis::Calculator::Cosecant, "Compute cosecant")
         .def("cotangent", &Isis::Calculator::Cotangent, "Compute cotangent")
         .def("arcsine", &Isis::Calculator::Arcsine, "Compute arcsine")
         .def("arccosine", &Isis::Calculator::Arccosine, "Compute arccosine")
         .def("arctangent", &Isis::Calculator::Arctangent, "Compute arctangent")
         .def("arctangent2", &Isis::Calculator::Arctangent2, "Compute arctangent2")
         // Hyperbolic functions
         .def("sine_h", &Isis::Calculator::SineH, "Compute hyperbolic sine")
         .def("cosine_h", &Isis::Calculator::CosineH, "Compute hyperbolic cosine")
         .def("tangent_h", &Isis::Calculator::TangentH, "Compute hyperbolic tangent")
         .def("arcsine_h", &Isis::Calculator::ArcsineH, "Compute inverse hyperbolic sine")
         .def("arccosine_h", &Isis::Calculator::ArccosineH, "Compute inverse hyperbolic cosine")
         .def("arctangent_h", &Isis::Calculator::ArctangentH, "Compute inverse hyperbolic tangent")
         .def("__repr__", [](const Isis::Calculator &self)
              { return self.Empty() ? "Calculator(empty)" : "Calculator(has_data)"; });

     /**
      * @brief Bindings for the Isis::Affine class
      * Affine class provides functionality for affine transformations in 2D space.
      * @see Isis::Affine
      */
     py::class_<Isis::Affine>(m, "Affine")
         .def(py::init<>())
         // Transformation setup
         .def("solve", [](Isis::Affine &self, const std::vector<double> &x, const std::vector<double> &y, const std::vector<double> &xp, const std::vector<double> &yp, int n)
              { self.Solve(x.data(), y.data(), xp.data(), yp.data(), n); }, py::arg("x"), py::arg("y"), py::arg("xp"), py::arg("yp"), py::arg("n"), "Solve for affine transformation coefficients")
         .def("identity", &Isis::Affine::Identity, "Set transformation to identity")
         .def("translate", &Isis::Affine::Translate, py::arg("tx"), py::arg("ty"), "Apply translation")
         .def("rotate", &Isis::Affine::Rotate, py::arg("rotation"), "Apply counterclockwise rotation (in degrees)")
         .def("scale", &Isis::Affine::Scale, py::arg("scale_factor"), "Apply scaling")
         // Forward transformation
         .def("compute", &Isis::Affine::Compute, py::arg("x"), py::arg("y"), "Compute forward transformation")
         .def("xp", &Isis::Affine::xp, "Get transformed x coordinate")
         .def("yp", &Isis::Affine::yp, "Get transformed y coordinate")
         // Inverse transformation
         .def("compute_inverse", &Isis::Affine::ComputeInverse, py::arg("xp"), py::arg("yp"), "Compute inverse transformation")
         .def("x", &Isis::Affine::x, "Get inverse transformed x coordinate")
         .def("y", &Isis::Affine::y, "Get inverse transformed y coordinate")
         // Coefficient access
         .def("coefficients", &Isis::Affine::Coefficients, py::arg("variable"), "Get forward transformation coefficients")
         .def("inverse_coefficients", &Isis::Affine::InverseCoefficients, py::arg("variable"), "Get inverse transformation coefficients")
         .def("__repr__", [](const Isis::Affine &self)
              { return "Affine()"; });

     /**
      * @brief Bindings for the Isis::BasisFunction class
      * BasisFunction class provides functionality for basis function operations.
      * @see Isis::BasisFunction
      */
     py::class_<Isis::BasisFunction>(m, "BasisFunction")
         .def(py::init([](const std::string &name, int num_vars, int num_coefs)
                       { return new Isis::BasisFunction(stdStringToQString(name), num_vars, num_coefs); }),
              py::arg("name"),
              py::arg("num_vars"),
              py::arg("num_coefs"))
         .def("set_coefficients", [](Isis::BasisFunction &self, const std::vector<double> &coefs)
              { self.SetCoefficients(coefs); }, py::arg("coefficients"), "Set the function coefficients")
         .def("evaluate", py::overload_cast<const std::vector<double> &>(&Isis::BasisFunction::Evaluate), py::arg("variables"), "Evaluate the function with multiple variables")
         .def("evaluate", py::overload_cast<const double &>(&Isis::BasisFunction::Evaluate), py::arg("variable"), "Evaluate the function with a single variable")
         .def("expand", &Isis::BasisFunction::Expand, py::arg("variables"), "Expand the basis function")
         .def("coefficients", &Isis::BasisFunction::Coefficients, "Get number of coefficients")
         .def("variables", &Isis::BasisFunction::Variables, "Get number of variables")
         .def("name", [](const Isis::BasisFunction &self)
              { return qStringToStdString(self.Name()); }, "Get the function name")
         .def("term", &Isis::BasisFunction::Term, py::arg("index"), "Get a specific term")
         .def("coefficient", &Isis::BasisFunction::Coefficient, py::arg("index"), "Get a specific coefficient")
         .def("__repr__", [](const Isis::BasisFunction &self)
              { return "BasisFunction(name='" + qStringToStdString(self.Name()) + "', " +
                       "coefficients=" + std::to_string(self.Coefficients()) + ", " +
                       "variables=" + std::to_string(self.Variables()) + ")"; });

     /**
      * @brief Bindings for the Isis::LeastSquares class
      * LeastSquares class provides functionality for solving least squares problems
      * and performing curve fitting operations.
      * @see Isis::LeastSquares
      */
     py::class_<Isis::LeastSquares> least_squares(m, "LeastSquares");

     // Bind the SolveMethod enum
     py::enum_<Isis::LeastSquares::SolveMethod>(least_squares, "SolveMethod")
         .value("SVD", Isis::LeastSquares::SVD)
         .value("QRD", Isis::LeastSquares::QRD)
         .value("SPARSE", Isis::LeastSquares::SPARSE)
         .export_values();

     least_squares
         .def(py::init<Isis::BasisFunction &>(),
              py::arg("basis"),
              py::keep_alive<1, 2>(),  // Keep basis alive as long as LeastSquares exists
              "Construct LeastSquares with a basis function")
         // Data input methods
         .def("add_known", &Isis::LeastSquares::AddKnown,
              py::arg("input"),
              py::arg("expected"),
              py::arg("weight") = 1.0,
              "Add a known data point with optional weight")
         .def("weight", &Isis::LeastSquares::Weight,
              py::arg("index"),
              py::arg("weight"),
              "Set weight for a specific equation")
         // Query methods
         .def("get_input", &Isis::LeastSquares::GetInput, py::arg("row"), "Get input variables for a row")
         .def("get_expected", &Isis::LeastSquares::GetExpected, py::arg("row"), "Get expected value for a row")
         .def("rows", &Isis::LeastSquares::Rows, "Get number of rows (equations)")
         .def("knowns", &Isis::LeastSquares::Knowns, "Get number of known data points")
         .def("get_sigma0", &Isis::LeastSquares::GetSigma0, "Get standard deviation of unit weight")
         .def("get_degrees_of_freedom", &Isis::LeastSquares::GetDegreesOfFreedom, "Get degrees of freedom")
         .def("get_epsilons", &Isis::LeastSquares::GetEpsilons, "Get epsilon values for sparse solver")
         // Solution methods
         .def("solve", &Isis::LeastSquares::Solve,
              py::arg("method") = Isis::LeastSquares::SVD,
              "Solve the least squares system")
         .def("evaluate", &Isis::LeastSquares::Evaluate, py::arg("input"), "Evaluate using solved coefficients")
         // Results methods
         .def("residuals", &Isis::LeastSquares::Residuals, "Get all residuals")
         .def("residual", &Isis::LeastSquares::Residual, py::arg("i"), "Get a single residual")
         // Configuration methods
         .def("reset", &Isis::LeastSquares::Reset, "Reset the solver")
         .def("reset_sparse", &Isis::LeastSquares::ResetSparse, "Reset the sparse solver")
         .def("set_parameter_weights", &Isis::LeastSquares::SetParameterWeights,
              py::arg("weights"),
              "Set parameter weights")
         .def("set_number_of_constrained_parameters", &Isis::LeastSquares::SetNumberOfConstrainedParameters,
              py::arg("n"),
              "Set number of constrained parameters")
         .def("__repr__", [](const Isis::LeastSquares &self)
              { return "LeastSquares(rows=" + std::to_string(self.Rows()) +
                       ", knowns=" + std::to_string(self.Knowns()) + ")"; });

     /**
      * @brief Bindings for the Isis::Matrix class
      * Matrix class provides functionality for matrix operations and linear algebra.
      * Note: Matrix requires explicit dimensions - no default constructor available.
      * @see Isis::Matrix
      */
     py::class_<Isis::Matrix>(m, "Matrix")
         .def(py::init<int, int>(), py::arg("rows"), py::arg("columns"), "Construct a matrix with specified dimensions")
         .def(py::init<int, int, double>(), py::arg("rows"), py::arg("columns"), py::arg("value"), "Construct a matrix with specified dimensions and initial value")
         // Static factory methods
         .def_static("identity", &Isis::Matrix::Identity, py::arg("n"), "Create an identity matrix of size n x n")
         // Query methods - Note: Rows() and Columns() are non-const in ISIS, so we use lambdas to work around this limitation
         .def("rows", [](Isis::Matrix &self) { return self.Rows(); }, "Get number of rows")
         .def("columns", [](Isis::Matrix &self) { return self.Columns(); }, "Get number of columns")
         .def("determinant", &Isis::Matrix::Determinant, "Calculate the determinant")
         .def("trace", &Isis::Matrix::Trace, "Calculate the trace")
         .def("eigenvalues", &Isis::Matrix::Eigenvalues, "Get eigenvalues")
         // Matrix operations
         .def("add", &Isis::Matrix::Add, py::arg("matrix"), "Add two matrices")
         .def("subtract", &Isis::Matrix::Subtract, py::arg("matrix"), "Subtract two matrices")
         .def("multiply", py::overload_cast<Isis::Matrix &>(&Isis::Matrix::Multiply), py::arg("matrix"), "Multiply two matrices")
         .def("multiply", py::overload_cast<double>(&Isis::Matrix::Multiply), py::arg("scalar"), "Multiply matrix by scalar")
         .def("multiply_element_wise", &Isis::Matrix::MultiplyElementWise, py::arg("matrix"), "Element-wise multiplication")
         .def("transpose", &Isis::Matrix::Transpose, "Get transpose of the matrix")
         .def("inverse", &Isis::Matrix::Inverse, "Get inverse of the matrix")
         .def("eigenvectors", &Isis::Matrix::Eigenvectors, "Get eigenvectors")
         // Element access - Use non-const access for getting/setting values
         .def("__getitem__", [](Isis::Matrix &self, std::pair<int, int> idx) {
              return self[idx.first][idx.second];
         }, py::arg("index"), "Get element at (row, column)")
         .def("__setitem__", [](Isis::Matrix &self, std::pair<int, int> idx, double value) {
              self[idx.first][idx.second] = value;
         }, py::arg("index"), py::arg("value"), "Set element at (row, column)")
         .def("__repr__", [](Isis::Matrix &self)
              { return "Matrix(rows=" + std::to_string(self.Rows()) +
                       ", columns=" + std::to_string(self.Columns()) + ")"; });

     /**
      * @brief Bindings for the Isis::PolynomialUnivariate class
      * PolynomialUnivariate class provides functionality for 1D polynomial operations.
      * Inherits from BasisFunction.
      * @see Isis::PolynomialUnivariate
      */
     py::class_<Isis::PolynomialUnivariate, Isis::BasisFunction>(m, "PolynomialUnivariate")
         .def(py::init<int>(), py::arg("degree"), "Construct a univariate polynomial of specified degree")
         .def("expand", &Isis::PolynomialUnivariate::Expand, py::arg("vars"), "Expand the polynomial with variables")
         .def("derivative_var", &Isis::PolynomialUnivariate::DerivativeVar,
              py::arg("value"),
              "Calculate derivative with respect to the variable")
         .def("derivative_coef", &Isis::PolynomialUnivariate::DerivativeCoef,
              py::arg("value"),
              py::arg("coef_index"),
              "Calculate derivative with respect to a coefficient")
         .def("__repr__", [](const Isis::PolynomialUnivariate &self)
              { return "PolynomialUnivariate(degree=" + std::to_string(self.Coefficients() - 1) + ")"; });

     /**
      * @brief Bindings for the Isis::PolynomialBivariate class
      * PolynomialBivariate class provides functionality for 2D polynomial operations.
      * Inherits from BasisFunction.
      * @see Isis::PolynomialBivariate
      */
     py::class_<Isis::PolynomialBivariate, Isis::BasisFunction>(m, "PolynomialBivariate")
         .def(py::init<int>(), py::arg("degree"), "Construct a bivariate polynomial of specified degree")
         .def("expand", &Isis::PolynomialBivariate::Expand, py::arg("vars"), "Expand the polynomial with variables")
         .def("__repr__", [](const Isis::PolynomialBivariate &self)
              { return "PolynomialBivariate(degree=" + std::to_string((int)sqrt(self.Coefficients()) - 1) + ")"; });
}
