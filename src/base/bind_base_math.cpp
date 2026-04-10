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
 *   - reference/upstream_isis/src/base/objs/FourierTransform/FourierTransform.h
 *   - isis/src/base/objs/InfixToPostfix/InfixToPostfix.h
 *   - isis/src/base/objs/CubeInfixToPostfix/CubeInfixToPostfix.h
 *   - isis/src/base/objs/InlineInfixToPostfix/InlineInfixToPostfix.h
 *   - isis/src/base/objs/NthOrderPolynomial/NthOrderPolynomial.h
 * Binding author: Geng Xun
 * Created: 2026-03-24
 * Updated: 2026-04-09  Geng Xun exposed Ransac helper functions via a Python math submodule.
 * Updated: 2026-04-09  Geng Xun added SurfaceModel binding (bivariate polynomial surface fitting)
 * Updated: 2026-04-09  Geng Xun added MaximumLikelihoodWFunctions binding (robust estimation).
 * Updated: 2026-04-10  Geng Xun added FourierTransform binding (FFT/IFFT on complex vectors).
 * Updated: 2026-04-10  Geng Xun added PrincipalComponentAnalysis binding (PCA via TNT::Array2D adapters).
 * Purpose: Expose Calculator, Affine, BasisFunction, FourierTransform, InfixToPostfix,
 *          CubeInfixToPostfix, InlineInfixToPostfix, NthOrderPolynomial, Ransac helpers, SurfaceModel,
 *          MaximumLikelihoodWFunctions, and PrincipalComponentAnalysis classes to Python via pybind11.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/complex.h>
#include <cmath>
#include <complex>

#include <tnt/tnt_array2d.h>

#include "Calculator.h"
#include "Affine.h"
#include "BasisFunction.h"
#include "FourierTransform.h"
#include "InfixToPostfix.h"
#include "CubeInfixToPostfix.h"
#include "InlineInfixToPostfix.h"
#include "LeastSquares.h"
#include "Matrix.h"
#include "MaximumLikelihoodWFunctions.h"
#include "PolynomialUnivariate.h"
#include "PolynomialBivariate.h"
#include "NthOrderPolynomial.h"
#include "Ransac.h"
#include "SurfaceModel.h"
#include "Buffer.h"
#include "PrincipalComponentAnalysis.h"
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
         .def("__repr__", [](Isis::Calculator &self)
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

     // Added: 2026-03-29 - expose NthOrderPolynomial (inherits BasisFunction, 2-variable nth-degree)

     /**
      * @brief Bindings for the Isis::NthOrderPolynomial class
      * NthOrderPolynomial creates an nth order polynomial basis function with 2 variables.
      * Expand computes pow(t1, i) - pow(t2, i) terms for i from degree down to 1.
      * Inherits from BasisFunction.
      * Source header author(s): not explicitly stated in upstream header
      * @see Isis::NthOrderPolynomial
      */
     py::class_<Isis::NthOrderPolynomial, Isis::BasisFunction>(m, "NthOrderPolynomial")
         .def(py::init<int>(), py::arg("degree"),
              "Construct an NthOrderPolynomial of the specified degree (2 variables, degree coefficients)")
         .def("expand", &Isis::NthOrderPolynomial::Expand, py::arg("vars"),
              "Expand the polynomial with a 2-element variable vector")
         .def("__repr__", [](const Isis::NthOrderPolynomial &self)
              { return "NthOrderPolynomial(variables=" + std::to_string(self.Variables()) +
                       ", coefficients=" + std::to_string(self.Coefficients()) + ")"; });

     // Added: 2026-03-26 - expose InfixToPostfix expression conversion classes

     /**
      * @brief Bindings for the Isis::InfixToPostfix class
      * InfixToPostfix converts mathematical infix expressions to postfix notation.
      * Source header author(s): not explicitly stated in upstream header
      * @see Isis::InfixToPostfix
      */
     py::class_<Isis::InfixToPostfix>(m, "InfixToPostfix")
         .def(py::init<>(), "Construct an InfixToPostfix converter with default operators")
         .def("convert", [](Isis::InfixToPostfix &self, const std::string &infix)
              { return qStringToStdString(self.convert(stdStringToQString(infix))); },
              py::arg("infix"),
              "Convert an infix expression string to postfix notation")
         .def("tokenize_equation", [](Isis::InfixToPostfix &self, const std::string &equation)
              { return qStringToStdString(self.tokenizeEquation(stdStringToQString(equation))); },
              py::arg("equation"),
              "Tokenize an equation string, separating operators and operands")
         .def("__repr__", [](const Isis::InfixToPostfix &)
              { return "InfixToPostfix()"; });

     /**
      * @brief Bindings for the Isis::CubeInfixToPostfix class
      * CubeInfixToPostfix extends InfixToPostfix with cube-specific variables
      * such as phase, incidence, emission angles and file-based references.
      * Source header author(s): not explicitly stated in upstream header
      * @see Isis::CubeInfixToPostfix
      */
     py::class_<Isis::CubeInfixToPostfix, Isis::InfixToPostfix>(m, "CubeInfixToPostfix")
         .def(py::init<>(), "Construct a CubeInfixToPostfix converter with cube-specific operators")
         .def("__repr__", [](const Isis::CubeInfixToPostfix &)
              { return "CubeInfixToPostfix()"; });

     /**
      * @brief Bindings for the Isis::InlineInfixToPostfix class
      * InlineInfixToPostfix extends InfixToPostfix with inline variable/scalar
      * handling for processing expressions that reference column-based data.
      * Source header author(s): not explicitly stated in upstream header
      * @see Isis::InlineInfixToPostfix
      */
     py::class_<Isis::InlineInfixToPostfix, Isis::InfixToPostfix>(m, "InlineInfixToPostfix")
         .def(py::init<>(), "Construct an InlineInfixToPostfix converter with inline-specific operators")
         .def("__repr__", [](const Isis::InlineInfixToPostfix &)
              { return "InlineInfixToPostfix()"; });

     py::module_ ransac = m.def_submodule("Ransac", "ISIS RANSAC helper functions for packed symmetric matrices.");
     ransac.def("isymp", &Isis::isymp, py::arg("row"), py::arg("col"));
     ransac.def("binomial_coeficient", &Isis::binomial_coeficient, py::arg("n"), py::arg("k"));
     ransac.def("indeces_from_set",
                [](int set, int set_size, int n) {
                  std::vector<int> indices(set_size, 0);
                  int status = Isis::indeces_from_set(indices.data(), set, set_size, n);
                  return py::make_tuple(status, indices);
                },
                py::arg("set"), py::arg("set_size"), py::arg("n"),
                "Return (status, indices) for the requested combination set.")
           .def("decompose",
                [](const std::vector<double> &a, int nsize) {
                  std::vector<double> matrix = a;
                  int status = Isis::decompose(matrix.data(), nsize);
                  return py::make_tuple(status, matrix);
                },
                py::arg("a"), py::arg("nsize"),
                "Run in-place Cholesky decomposition on a packed symmetric matrix.")
           .def("foresub",
                [](const std::vector<double> &a, const std::vector<double> &b, int nsize) {
                  std::vector<double> matrix = a;
                  std::vector<double> values = b;
                  int status = Isis::foresub(matrix.data(), values.data(), nsize);
                  return py::make_tuple(status, values);
                },
                py::arg("a"), py::arg("b"), py::arg("nsize"),
                "Run forward substitution using a packed lower-triangular matrix.")
           .def("backsub",
                [](const std::vector<double> &a, const std::vector<double> &b, int nsize) {
                  std::vector<double> matrix = a;
                  std::vector<double> values = b;
                  int status = Isis::backsub(matrix.data(), values.data(), nsize);
                  return py::make_tuple(status, values);
                },
                py::arg("a"), py::arg("b"), py::arg("nsize"),
                "Run backward substitution using a packed symmetric matrix.")
           .def("inverse",
                [](const std::vector<double> &a, int nsize) {
                  std::vector<double> matrix = a;
                  int status = Isis::inverse(matrix.data(), nsize);
                  return py::make_tuple(status, matrix);
                },
                py::arg("a"), py::arg("nsize"),
                "Invert a packed symmetric matrix in-place after decomposition.")
           .def("choleski_solve",
                [](const std::vector<double> &a,
                   const std::vector<double> &b,
                   int nsize,
                   int flag) {
                  std::vector<double> matrix = a;
                  std::vector<double> values = b;
                  int status = Isis::choleski_solve(matrix.data(), values.data(), nsize, flag);
                  return py::make_tuple(status, matrix, values);
                },
                py::arg("a"), py::arg("b"), py::arg("nsize"), py::arg("flag"),
                "Solve a symmetric positive-definite linear system stored in packed form.");

     // Added: 2026-04-09 - bind Isis::SurfaceModel
     /**
      * @brief Bindings for the Isis::SurfaceModel class
      * SurfaceModel fits a 2nd-degree bivariate polynomial surface z=f(x,y) to
      * a set of (x,y,z) triplets using least-squares. After calling solve(),
      * evaluate(x,y) returns the fitted z value and min_max() returns the
      * local minimum/maximum coordinates.
      *
      * Source ISIS header: reference/upstream_isis/src/base/objs/SurfaceModel/SurfaceModel.h
      * Source class: Isis::SurfaceModel
      * Source header author(s): Jeff Anderson (2005-05-09)
      * Binding author: Geng Xun
      */
     py::class_<Isis::SurfaceModel>(m, "SurfaceModel")
         .def(py::init<>(), "Construct a SurfaceModel (empty triplet list, 2nd-degree bivariate polynomial).")
         .def("add_triplet",
              &Isis::SurfaceModel::AddTriplet,
              py::arg("x"), py::arg("y"), py::arg("z"),
              "Add a single (x, y, z) data point.")
         .def("add_triplets",
              [](Isis::SurfaceModel &self,
                 const std::vector<double> &x,
                 const std::vector<double> &y,
                 const std::vector<double> &z) {
                self.AddTriplets(x, y, z);
              },
              py::arg("x"), py::arg("y"), py::arg("z"),
              "Add a list of (x, y, z) data points from three equal-length sequences.")
         .def("solve",
              &Isis::SurfaceModel::Solve,
              "Fit the surface to all added triplets using least-squares. "
              "Must be called before evaluate() or min_max().")
         .def("evaluate",
              &Isis::SurfaceModel::Evaluate,
              py::arg("x"), py::arg("y"),
              "Evaluate the fitted surface at (x, y). Requires prior call to solve().")
         .def("min_max",
              [](Isis::SurfaceModel &self) {
                double x = 0.0, y = 0.0;
                int rc = self.MinMax(x, y);
                return py::make_tuple(rc, x, y);
              },
              "Find the local minimum or maximum of the fitted surface. "
              "Returns (status, x, y) where status=0 means success, "
              "status=1 means the surface is a plane with no extremum.")
         .def("__repr__", [](const Isis::SurfaceModel &) {
              return "SurfaceModel()";
         });

  // Added: 2026-04-09 - MaximumLikelihoodWFunctions binding
  py::enum_<Isis::MaximumLikelihoodWFunctions::Model>(m, "MaximumLikelihoodModel")
      .value("Huber",        Isis::MaximumLikelihoodWFunctions::Huber)
      .value("HuberModified",Isis::MaximumLikelihoodWFunctions::HuberModified)
      .value("Welsch",       Isis::MaximumLikelihoodWFunctions::Welsch)
      .value("Chen",         Isis::MaximumLikelihoodWFunctions::Chen)
      .export_values();

  py::class_<Isis::MaximumLikelihoodWFunctions>(m, "MaximumLikelihoodWFunctions")
      .def(py::init<>(),
           "Construct a MaximumLikelihoodWFunctions with the default model (Huber).")
      .def(py::init<Isis::MaximumLikelihoodWFunctions::Model>(),
           py::arg("model"),
           "Construct with the given model and its default tweaking constant.")
      .def(py::init<Isis::MaximumLikelihoodWFunctions::Model, double>(),
           py::arg("model"), py::arg("tweaking_constant"),
           "Construct with the given model and a specific tweaking constant.")
      .def(py::init<const Isis::MaximumLikelihoodWFunctions &>(),
           py::arg("other"),
           "Copy constructor.")
      .def("set_model",
           py::overload_cast<Isis::MaximumLikelihoodWFunctions::Model>(
               &Isis::MaximumLikelihoodWFunctions::setModel),
           py::arg("model"),
           "Set the model type using the default tweaking constant.")
      .def("set_tweaking_constant_default",
           &Isis::MaximumLikelihoodWFunctions::setTweakingConstantDefault,
           "Reset the tweaking constant to its default for the current model.")
      .def("set_tweaking_constant",
           &Isis::MaximumLikelihoodWFunctions::setTweakingConstant,
           py::arg("tweaking_constant"),
           "Set a specific tweaking constant.")
      .def("model",
           &Isis::MaximumLikelihoodWFunctions::model,
           "Return the current model type.")
      .def("tweaking_constant",
           &Isis::MaximumLikelihoodWFunctions::tweakingConstant,
           "Return the current tweaking constant.")
      .def("sqrt_weight_scaler",
           &Isis::MaximumLikelihoodWFunctions::sqrtWeightScaler,
           py::arg("residual_z_score"),
           "Return the square-root weight scaler for the given residual z-score.")
      .def("tweaking_constant_quantile",
           &Isis::MaximumLikelihoodWFunctions::tweakingConstantQuantile,
           "Return the recommended quantile of the residuals to use as the tweaking constant.")
      .def("weighted_residual_cutoff",
           [](Isis::MaximumLikelihoodWFunctions &self) {
             return qStringToStdString(self.weightedResidualCutoff());
           },
           "Return a string describing the weighted residual cutoff.")
      .def_static("model_to_string",
                  [](Isis::MaximumLikelihoodWFunctions::Model model) {
                    return qStringToStdString(
                        Isis::MaximumLikelihoodWFunctions::modelToString(model));
                  },
                  py::arg("model"),
                  "Convert a Model enum value to its string name.")
      .def_static("string_to_model",
                  [](const std::string &model_name) {
                    return Isis::MaximumLikelihoodWFunctions::stringToModel(
                        stdStringToQString(model_name));
                  },
                  py::arg("model_name"),
                  "Convert a model name string to its Model enum value.")
      .def("__repr__",
           [](const Isis::MaximumLikelihoodWFunctions &self) {
             return "MaximumLikelihoodWFunctions(model=" +
                    qStringToStdString(Isis::MaximumLikelihoodWFunctions::modelToString(
                        self.model())) +
                    ", tweaking_constant=" +
                    std::to_string(self.tweakingConstant()) + ")";
           });

  // ── FourierTransform ───────────────────────────────────────────────────────
  // Added: 2026-04-10 - expose Isis::FourierTransform FFT/IFFT utility.
  py::class_<Isis::FourierTransform>(m, "FourierTransform")
      .def(py::init<>(), "Construct a FourierTransform object.")
      .def("transform",
           &Isis::FourierTransform::Transform,
           py::arg("input"),
           "Apply the forward Fourier transform. Input and output are "
           "lists of complex numbers (real, imag).")
      .def("inverse",
           &Isis::FourierTransform::Inverse,
           py::arg("input"),
           "Apply the inverse Fourier transform. Input and output are "
           "lists of complex numbers (real, imag).")
      .def("is_power_of_two",
           &Isis::FourierTransform::IsPowerOfTwo,
           py::arg("n"),
           "Return True if n is a power of two.")
      .def("lg",
           &Isis::FourierTransform::lg,
           py::arg("n"),
           "Return floor(log2(n)).")
      .def("bit_reverse",
           &Isis::FourierTransform::BitReverse,
           py::arg("n"), py::arg("x"),
           "Bit-reverse x in a field of n bits.")
      .def("next_power_of_two",
           &Isis::FourierTransform::NextPowerOfTwo,
           py::arg("n"),
           "Return the smallest power of two >= n.")
      .def("__repr__", [](const Isis::FourierTransform &) {
            return "FourierTransform()";
          });

  // ── PrincipalComponentAnalysis ──────────────────────────────────────────────
  // Added: 2026-04-10 - expose PCA; TNT::Array2D adapted to 2D Python lists.
  //
  // Helper lambdas: Python list<list<double>> <-> TNT::Array2D<double>
  auto py_to_tnt = [](const std::vector<std::vector<double>> &mat)
      -> TNT::Array2D<double> {
    if (mat.empty() || mat[0].empty()) {
      return TNT::Array2D<double>();
    }
    int rows = static_cast<int>(mat.size());
    int cols = static_cast<int>(mat[0].size());
    // Validate that all rows have the same number of columns.
    for (int r = 1; r < rows; ++r) {
      if (static_cast<int>(mat[r].size()) != cols) {
        throw py::value_error(
          "All rows must have the same number of columns (ragged arrays not supported)");
      }
    }
    TNT::Array2D<double> arr(rows, cols);
    for (int r = 0; r < rows; ++r) {
      for (int c = 0; c < cols; ++c) {
        arr[r][c] = mat[r][c];
      }
    }
    return arr;
  };

  auto tnt_to_py = [](const TNT::Array2D<double> &arr)
      -> std::vector<std::vector<double>> {
    std::vector<std::vector<double>> mat(arr.dim1(),
                                         std::vector<double>(arr.dim2(), 0.0));
    for (int r = 0; r < arr.dim1(); ++r) {
      for (int c = 0; c < arr.dim2(); ++c) {
        mat[r][c] = arr[r][c];
      }
    }
    return mat;
  };

  py::class_<Isis::PrincipalComponentAnalysis>(m, "PrincipalComponentAnalysis")
      .def(py::init<const int>(),
           py::arg("n"),
           "Construct a PCA object for n-dimensional data. Call "
           "add_data() followed by compute_transform() before Transform/Inverse.")
      .def(py::init([py_to_tnt](const std::vector<std::vector<double>> &transform_matrix) {
             return std::make_unique<Isis::PrincipalComponentAnalysis>(
                 py_to_tnt(transform_matrix));
           }),
           py::arg("transform_matrix"),
           "Construct a PCA object from a precomputed 2D transform matrix "
           "(list-of-lists).")
      .def("add_data",
           [](Isis::PrincipalComponentAnalysis &self,
              const std::vector<double> &data) {
             self.AddData(data.data(), static_cast<unsigned int>(data.size()));
           },
           py::arg("data"),
           "Add one observation vector to the running statistics.")
      .def("compute_transform",
           &Isis::PrincipalComponentAnalysis::ComputeTransform,
           "Compute the PCA transform from accumulated data.")
      .def("transform",
           [tnt_to_py, py_to_tnt](Isis::PrincipalComponentAnalysis &self,
                 const std::vector<std::vector<double>> &data_matrix) {
             return tnt_to_py(self.Transform(py_to_tnt(data_matrix)));
           },
           py::arg("data_matrix"),
           "Apply the PCA forward transform. Input/output are 2D list-of-lists.")
      .def("inverse",
           [tnt_to_py, py_to_tnt](Isis::PrincipalComponentAnalysis &self,
                 const std::vector<std::vector<double>> &component_matrix) {
             return tnt_to_py(self.Inverse(py_to_tnt(component_matrix)));
           },
           py::arg("component_matrix"),
           "Apply the PCA inverse transform. Input/output are 2D list-of-lists.")
      .def("transform_matrix",
           [tnt_to_py](Isis::PrincipalComponentAnalysis &self) {
             return tnt_to_py(self.TransformMatrix());
           },
           "Return the current PCA transform matrix as a 2D list-of-lists.")
      .def("dimensions",
           &Isis::PrincipalComponentAnalysis::Dimensions,
           "Return the number of dimensions (n) for this PCA object.")
      .def("__repr__", [](Isis::PrincipalComponentAnalysis &self) {
            return "PrincipalComponentAnalysis(dimensions=" +
                   std::to_string(self.Dimensions()) + ")";
          });
}
