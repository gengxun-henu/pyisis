"""
Unit tests for ISIS math classes: Calculator, Affine, BasisFunction,
LeastSquares, Matrix, PolynomialUnivariate, PolynomialBivariate,
NthOrderPolynomial, InfixToPostfix, CubeInfixToPostfix, InlineInfixToPostfix,
and SurfaceModel

Author: Geng Xun
Created: 2026-03-24
Last Modified: 2026-04-09
Updated: 2026-03-29  Geng Xun added regression coverage for Calculator, linear algebra, polynomial, and infix/postfix bindings.
Updated: 2026-04-09  Geng Xun added SurfaceModel focused unit tests.
"""
import unittest
import math

from _unit_test_support import ip


def make_basis_function():
    """Create a concrete BasisFunction using the bound upstream constructor signature."""
    return ip.BasisFunction("unit_test_basis", 1, 3)


class CalculatorUnitTest(unittest.TestCase):
    """Test suite for Calculator class bindings"""

    def test_calculator_construction(self):
        """Test basic Calculator construction"""
        calc = ip.Calculator()
        self.assertIsNotNone(calc)
        self.assertTrue(calc.empty())
        self.assertIn("Calculator", repr(calc))

    def test_calculator_push_pop_scalar(self):
        """Test pushing and popping scalar values"""
        calc = ip.Calculator()
        calc.push(5.0)
        self.assertFalse(calc.empty())

        result = calc.pop()
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0], 5.0, places=12)
        self.assertTrue(calc.empty())

    def test_calculator_push_vector(self):
        """Test pushing and popping vector values"""
        calc = ip.Calculator()
        test_vector = [1.0, 2.0, 3.0, 4.0, 5.0]
        calc.push(test_vector)

        result = calc.pop()
        self.assertEqual(len(result), len(test_vector))
        for i, val in enumerate(test_vector):
            self.assertAlmostEqual(result[i], val, places=12)

    def test_calculator_arithmetic_operations(self):
        """Test basic arithmetic operations"""
        calc = ip.Calculator()

        # Test addition
        calc.push(10.0)
        calc.push(5.0)
        calc.add()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 15.0, places=12)

        # Test subtraction
        calc.push(10.0)
        calc.push(3.0)
        calc.subtract()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 7.0, places=12)

        # Test multiplication
        calc.push(4.0)
        calc.push(5.0)
        calc.multiply()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 20.0, places=12)

        # Test division
        calc.push(20.0)
        calc.push(4.0)
        calc.divide()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 5.0, places=12)

    def test_calculator_trigonometric_functions(self):
        """Test trigonometric functions"""
        calc = ip.Calculator()

        # Test sine
        calc.push(math.pi / 2)
        calc.sine()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 1.0, places=12)

        # Test cosine
        calc.push(0.0)
        calc.cosine()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 1.0, places=12)

        # Test tangent
        calc.push(math.pi / 4)
        calc.tangent()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 1.0, places=10)

    def test_calculator_logarithm_operations(self):
        """Test logarithm operations"""
        calc = ip.Calculator()

        # Test natural log
        calc.push(math.e)
        calc.log()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 1.0, places=12)

        # Test log10
        calc.push(100.0)
        calc.log10()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 2.0, places=12)

    def test_calculator_comparison_operations(self):
        """Test comparison operations"""
        calc = ip.Calculator()

        # Test greater than
        calc.push(10.0)
        calc.push(5.0)
        calc.greater_than()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 1.0, places=12)  # True is represented as 1.0

        # Test less than
        calc.push(3.0)
        calc.push(7.0)
        calc.less_than()
        result = calc.pop()
        self.assertAlmostEqual(result[0], 1.0, places=12)

    def test_calculator_clear(self):
        """Test clearing the calculator stack"""
        calc = ip.Calculator()
        calc.push(1.0)
        calc.push(2.0)
        calc.push(3.0)
        self.assertFalse(calc.empty())

        calc.clear()
        self.assertTrue(calc.empty())


class AffineUnitTest(unittest.TestCase):
    """Test suite for Affine class bindings"""

    def test_affine_construction(self):
        """Test basic Affine construction"""
        affine = ip.Affine()
        self.assertIsNotNone(affine)
        self.assertIn("Affine", repr(affine))

    def test_affine_identity_transformation(self):
        """Test identity transformation"""
        affine = ip.Affine()
        affine.identity()

        # Test forward transformation with identity
        affine.compute(10.0, 20.0)
        self.assertAlmostEqual(affine.xp(), 10.0, places=12)
        self.assertAlmostEqual(affine.yp(), 20.0, places=12)

        # Test inverse transformation with identity
        affine.compute_inverse(10.0, 20.0)
        self.assertAlmostEqual(affine.x(), 10.0, places=12)
        self.assertAlmostEqual(affine.y(), 20.0, places=12)

    def test_affine_translation(self):
        """Test translation transformation"""
        affine = ip.Affine()
        affine.identity()
        affine.translate(5.0, 10.0)

        affine.compute(0.0, 0.0)
        self.assertAlmostEqual(affine.xp(), 5.0, places=12)
        self.assertAlmostEqual(affine.yp(), 10.0, places=12)

    def test_affine_scaling(self):
        """Test scaling transformation"""
        affine = ip.Affine()
        affine.identity()
        affine.scale(2.0)

        affine.compute(3.0, 4.0)
        self.assertAlmostEqual(affine.xp(), 6.0, places=12)
        self.assertAlmostEqual(affine.yp(), 8.0, places=12)

    def test_affine_rotation(self):
        """Test rotation transformation"""
        affine = ip.Affine()
        affine.identity()
        affine.rotate(90.0)

        affine.compute(1.0, 0.0)
        self.assertAlmostEqual(affine.xp(), 0.0, places=10)
        self.assertAlmostEqual(affine.yp(), 1.0, places=10)

    def test_affine_solve(self):
        """Test solving for affine coefficients"""
        affine = ip.Affine()

        # Create simple test data for identity transformation
        x = [0.0, 1.0, 0.0]
        y = [0.0, 0.0, 1.0]
        xp = [0.0, 1.0, 0.0]
        yp = [0.0, 0.0, 1.0]

        affine.solve(x, y, xp, yp, 3)

        # Test the solved transformation
        affine.compute(1.0, 1.0)
        self.assertAlmostEqual(affine.xp(), 1.0, places=10)
        self.assertAlmostEqual(affine.yp(), 1.0, places=10)


class BasisFunctionUnitTest(unittest.TestCase):
    """Test suite for BasisFunction class bindings"""

    def test_basis_function_construction(self):
        """Test BasisFunction construction with the upstream constructor signature"""
        basis = make_basis_function()
        self.assertIsNotNone(basis)
        self.assertIn("BasisFunction", repr(basis))
        self.assertEqual(basis.variables(), 1)
        self.assertEqual(basis.coefficients(), 3)

    def test_basis_function_coefficients(self):
        """Test setting and using coefficients"""
        basis = make_basis_function()

        # Set some coefficients
        coefs = [1.0, 2.0, 3.0]
        basis.set_coefficients(coefs)

        # Verify coefficients can be retrieved
        self.assertEqual(basis.coefficients(), len(coefs))

    def test_basis_function_name(self):
        """Test getting function name"""
        basis = make_basis_function()
        name = basis.name()
        self.assertIsInstance(name, str)
        self.assertEqual(name, "unit_test_basis")


class LeastSquaresUnitTest(unittest.TestCase):
    """Test suite for LeastSquares class bindings"""

    def test_least_squares_construction(self):
        """Test LeastSquares construction with BasisFunction"""
        basis = make_basis_function()
        """Test basic LeastSquares construction"""
        basis = ip.PolynomialUnivariate(2)  # degree 2 polynomial
        ls = ip.LeastSquares(basis)
        self.assertIsNotNone(ls)
        self.assertIn("LeastSquares", repr(ls))
        self.assertEqual(ls.rows(), 0)
        self.assertEqual(ls.knowns(), 0)

    def test_least_squares_add_known(self):
        """Test adding known data points"""
        basis = make_basis_function()
        ls = ip.LeastSquares(basis)

        # Add a known data point
        ls.add_known([1.0], 2.0, 1.0)
        self.assertEqual(ls.knowns(), 1)

        # Add another
        ls.add_known([2.0], 4.0)
        self.assertEqual(ls.knowns(), 2)

    def test_least_squares_solve_method_enum(self):
        """Test SolveMethod enum values"""
        self.assertTrue(hasattr(ip.LeastSquares, 'SolveMethod'))
        self.assertTrue(hasattr(ip.LeastSquares.SolveMethod, 'SVD'))
        self.assertTrue(hasattr(ip.LeastSquares.SolveMethod, 'QRD'))
        self.assertTrue(hasattr(ip.LeastSquares.SolveMethod, 'SPARSE'))

    def test_least_squares_simple_fit(self):
        """Test a simple linear fit"""
        basis = ip.BasisFunction("linear", 1, 2)
        ls = ip.LeastSquares(basis)

        # Fit y = 2x + 1
        basis = ip.PolynomialUnivariate(1)  # linear fit
        ls = ip.LeastSquares(basis)

        # Add some known points for a linear relationship: y = 2x + 1
        ls.add_known([0.0], 1.0)
        ls.add_known([1.0], 3.0)
        ls.add_known([2.0], 5.0)

        self.assertEqual(ls.knowns(), 3)
        self.assertEqual(ls.rows(), 3)

    def test_least_squares_solve_svd(self):
        """Test solving least squares with SVD method"""
        basis = ip.PolynomialUnivariate(1)  # linear fit
        ls = ip.LeastSquares(basis)

        # Add known points for y = 2x + 1
        ls.add_known([0.0], 1.0)
        ls.add_known([1.0], 3.0)
        ls.add_known([2.0], 5.0)
        ls.add_known([3.0], 7.0)

        # Solve using SVD
        result = ls.solve(ip.LeastSquares.SolveMethod.SVD)
        self.assertEqual(result, 0)  # Success

        # Evaluate at known points
        self.assertAlmostEqual(ls.evaluate([0.0]), 1.0, places=10)
        self.assertAlmostEqual(ls.evaluate([1.0]), 3.0, places=10)
        self.assertAlmostEqual(ls.evaluate([2.0]), 5.0, places=10)

    def test_least_squares_residuals(self):
        """Test getting residuals from fit"""
        basis = ip.PolynomialUnivariate(1)
        ls = ip.LeastSquares(basis)

        # Add points with some noise
        ls.add_known([0.0], 1.0)
        ls.add_known([1.0], 3.0)
        ls.add_known([2.0], 5.0)

        self.assertEqual(ls.knowns(), 3)

        # Solve the system
        result = ls.solve()
        self.assertIsNotNone(result)
        residuals = ls.residuals()

        # For a perfect fit, residuals should be near zero
        self.assertEqual(len(residuals), 3)
        for res in residuals:
            self.assertAlmostEqual(res, 0.0, places=10)

    def test_least_squares_get_input_expected(self):
        """Test getting input and expected values"""
        basis = ip.PolynomialUnivariate(1)
        ls = ip.LeastSquares(basis)

        ls.add_known([1.5], 3.0)
        ls.add_known([2.5], 5.0)

        input_0 = ls.get_input(0)
        self.assertAlmostEqual(input_0[0], 1.5, places=10)
        self.assertAlmostEqual(ls.get_expected(0), 3.0, places=10)

        input_1 = ls.get_input(1)
        self.assertAlmostEqual(input_1[0], 2.5, places=10)
        self.assertAlmostEqual(ls.get_expected(1), 5.0, places=10)

    def test_least_squares_reset(self):
        """Test resetting least squares"""
        basis = ip.PolynomialUnivariate(1)
        ls = ip.LeastSquares(basis)

        ls.add_known([1.0], 2.0)
        ls.add_known([2.0], 4.0)
        self.assertEqual(ls.knowns(), 2)

        ls.reset()
        self.assertEqual(ls.knowns(), 0)

    @unittest.expectedFailure  # Documents ISIS library bug
    def test_least_squares_double_solve_accumulation_bug(self):
        """Known bug: calling solve() twice accumulates residuals

        This test documents a known bug in the ISIS C++ library where
        calling solve() multiple times on the same LeastSquares object
        accumulates residuals instead of replacing them.

        Workaround: Create a new LeastSquares object for each solve operation.
        """
        basis = ip.PolynomialUnivariate(1)
        ls = ip.LeastSquares(basis)

        # Add some data points
        ls.add_known([1.0], 2.0)
        ls.add_known([2.0], 4.0)

        # First solve
        ls.solve()
        residuals_first = ls.residuals()
        first_count = len(residuals_first)

        # Second solve - this should replace residuals, not accumulate
        ls.solve()
        residuals_second = ls.residuals()
        second_count = len(residuals_second)

        # Bug: residuals_second will have double the entries
        self.assertEqual(first_count, second_count,
                        "Bug: solve() should replace residuals, not accumulate them")


class MatrixUnitTest(unittest.TestCase):
    """Test suite for Matrix class bindings"""

    def test_matrix_sized_construction(self):
        """Test Matrix construction with specified dimensions"""
        mat = ip.Matrix(3, 3)
        self.assertIsNotNone(mat)
        self.assertEqual(mat.rows(), 3)
        self.assertEqual(mat.columns(), 3)

    def test_matrix_sized_construction_with_value(self):
        """Test Matrix construction with dimensions and initial value"""
        mat = ip.Matrix(2, 2, 5.0)
        self.assertIsNotNone(mat)
        self.assertEqual(mat.rows(), 2)
        self.assertEqual(mat.columns(), 2)

    def test_matrix_initial_value_propagation(self):
        """Test that initial value is correctly propagated to all elements"""
        mat = ip.Matrix(3, 3, 7.5)
        # Verify all elements have the initial value
        for i in range(3):
            for j in range(3):
                self.assertEqual(mat[i, j], 7.5,
                                f"Element [{i},{j}] should be 7.5")

    def test_matrix_identity(self):
        """Test creating identity matrix"""
        mat = ip.Matrix.identity(3)
        self.assertIsNotNone(mat)
        self.assertEqual(mat.rows(), 3)
        self.assertEqual(mat.columns(), 3)

    def test_matrix_element_access(self):
        """Test getting and setting matrix elements"""
        mat = ip.Matrix(2, 2, 0.0)

        # Set elements
        mat[0, 0] = 1.0
        mat[0, 1] = 2.0
        mat[1, 0] = 3.0
        mat[1, 1] = 4.0

        # Get elements
        self.assertAlmostEqual(mat[0, 0], 1.0, places=12)
        self.assertAlmostEqual(mat[0, 1], 2.0, places=12)
        self.assertAlmostEqual(mat[1, 0], 3.0, places=12)
        self.assertAlmostEqual(mat[1, 1], 4.0, places=12)

    def test_matrix_operations(self):
        """Test basic matrix operations"""
        mat1 = ip.Matrix.identity(2)
        mat2 = ip.Matrix.identity(2)

        # Test addition
        result = mat1.add(mat2)
        self.assertIsNotNone(result)

        # Test multiplication by scalar
        result = mat1.multiply(2.0)
        self.assertIsNotNone(result)

    def test_matrix_transpose(self):
        """Test matrix transpose"""
        mat = ip.Matrix(2, 3, 1.0)
    def test_matrix_construction_with_size(self):
        """Test Matrix construction with size"""
        mat = ip.Matrix(3, 4)
        self.assertEqual(mat.rows(), 3)
        self.assertEqual(mat.columns(), 4)

    def test_matrix_construction_with_value(self):
        """Test Matrix construction with initial value"""
        mat = ip.Matrix(2, 2, 5.0)
        self.assertEqual(mat.rows(), 2)
        self.assertEqual(mat.columns(), 2)
        # Note: We can't easily test the values without __getitem__ working properly

    def test_matrix_identity(self):
        """Test creating identity matrix"""
        identity = ip.Matrix.identity(3)
        self.assertEqual(identity.rows(), 3)
        self.assertEqual(identity.columns(), 3)

        # Identity matrix should have determinant of 1
        self.assertAlmostEqual(identity.determinant(), 1.0, places=10)

    def test_matrix_trace(self):
        """Test matrix trace calculation"""
        identity = ip.Matrix.identity(3)
        # Trace of 3x3 identity is 3
        self.assertAlmostEqual(identity.trace(), 3.0, places=10)

    def test_matrix_transpose(self):
        """Test matrix transpose"""
        mat = ip.Matrix(2, 3)
        transposed = mat.transpose()
        self.assertEqual(transposed.rows(), 3)
        self.assertEqual(transposed.columns(), 2)

    def test_matrix_determinant_trace(self):
        """Test determinant and trace calculations"""
        mat = ip.Matrix.identity(3)

        # Determinant of identity matrix should be 1
        det = mat.determinant()
        self.assertAlmostEqual(det, 1.0, places=10)

        # Trace of 3x3 identity matrix should be 3
        trace = mat.trace()
        self.assertAlmostEqual(trace, 3.0, places=10)
    def test_matrix_operations(self):
        """Test basic matrix operations"""
        mat1 = ip.Matrix(2, 2, 1.0)
        mat2 = ip.Matrix(2, 2, 2.0)

        # Test addition
        result = mat1.add(mat2)
        self.assertEqual(result.rows(), 2)
        self.assertEqual(result.columns(), 2)

        # Test scalar multiplication
        result = mat1.multiply(3.0)
        self.assertEqual(result.rows(), 2)
        self.assertEqual(result.columns(), 2)


class PolynomialUnivariateUnitTest(unittest.TestCase):
    """Test suite for PolynomialUnivariate class bindings"""

    def test_polynomial_univariate_construction(self):
        """Test PolynomialUnivariate construction"""
        poly = ip.PolynomialUnivariate(2)  # degree 2 polynomial
        self.assertIsNotNone(poly)
        self.assertIn("PolynomialUnivariate", repr(poly))
        self.assertEqual(poly.variables(), 1)
        self.assertEqual(poly.coefficients(), 3)  # degree 2 has 3 coefficients: c0 + c1*x + c2*x^2

    def test_polynomial_univariate_expand(self):
        """Test expanding polynomial with variables"""
        poly = ip.PolynomialUnivariate(2)
        poly.expand([2.0])  # Expand at x=2.0
        # The expansion should work without errors

    def test_polynomial_univariate_inherits_basis_function(self):
        """Test that PolynomialUnivariate inherits from BasisFunction"""
        poly = ip.PolynomialUnivariate(1)
        # Should have BasisFunction methods
        self.assertTrue(hasattr(poly, 'set_coefficients'))
        self.assertTrue(hasattr(poly, 'name'))
        self.assertTrue(hasattr(poly, 'variables'))
        self.assertTrue(hasattr(poly, 'coefficients'))

    def test_polynomial_univariate_derivatives(self):
        """Test derivative calculations"""
        poly = ip.PolynomialUnivariate(2)
        poly.set_coefficients([1.0, 2.0, 3.0])  # 1 + 2x + 3x^2

        # Test derivative with respect to variable
        deriv = poly.derivative_var(2.0)
        self.assertIsNotNone(deriv)

        # Test derivative with respect to coefficient
        deriv_coef = poly.derivative_coef(2.0, 0)
        self.assertIsNotNone(deriv_coef)
        poly = ip.PolynomialUnivariate(2)  # degree 2
        self.assertIsNotNone(poly)
        self.assertIn("PolynomialUnivariate", repr(poly))
        # Degree 2 polynomial has 3 coefficients (a0 + a1*x + a2*x^2)
        self.assertEqual(poly.coefficients(), 3)
        self.assertEqual(poly.variables(), 1)

    def test_polynomial_univariate_expand(self):
        """Test expanding polynomial"""
        poly = ip.PolynomialUnivariate(2)
        poly.expand([2.0])  # Expand at x=2
        # After expand, we should be able to use the polynomial
        # The expand method sets up the basis function terms

    def test_polynomial_univariate_evaluate(self):
        """Test evaluating polynomial"""
        poly = ip.PolynomialUnivariate(2)

        # Set coefficients for: 1 + 2x + 3x^2
        poly.set_coefficients([1.0, 2.0, 3.0])

        # Evaluate at x = 2: 1 + 2(2) + 3(2^2) = 1 + 4 + 12 = 17
        poly.expand([2.0])
        result = poly.evaluate([2.0])
        self.assertAlmostEqual(result, 17.0, places=10)

    def test_polynomial_univariate_derivative(self):
        """Test polynomial derivative calculations"""
        poly = ip.PolynomialUnivariate(2)
        poly.set_coefficients([1.0, 2.0, 3.0])  # 1 + 2x + 3x^2

        # Derivative at x=2 should be: 2 + 6x = 2 + 12 = 14
        poly.expand([2.0])
        deriv = poly.derivative_var(2.0)
        self.assertAlmostEqual(deriv, 14.0, places=10)


class PolynomialBivariateUnitTest(unittest.TestCase):
    """Test suite for PolynomialBivariate class bindings"""

    def test_polynomial_bivariate_construction(self):
        """Test PolynomialBivariate construction"""
        poly = ip.PolynomialBivariate(2)  # degree 2 polynomial
        self.assertIsNotNone(poly)
        self.assertIn("PolynomialBivariate", repr(poly))
        self.assertEqual(poly.variables(), 2)

    def test_polynomial_bivariate_expand(self):
        """Test expanding polynomial with variables"""
        poly = ip.PolynomialBivariate(1)
        poly.expand([1.0, 2.0])  # Expand at x=1.0, y=2.0
        # The expansion should work without errors

    def test_polynomial_bivariate_inherits_basis_function(self):
        """Test that PolynomialBivariate inherits from BasisFunction"""
        poly = ip.PolynomialBivariate(1)
        # Should have BasisFunction methods
        self.assertTrue(hasattr(poly, 'set_coefficients'))
        self.assertTrue(hasattr(poly, 'name'))
        self.assertTrue(hasattr(poly, 'variables'))
        self.assertTrue(hasattr(poly, 'coefficients'))
        poly = ip.PolynomialBivariate(2)  # degree 2
        self.assertIsNotNone(poly)
        self.assertIn("PolynomialBivariate", repr(poly))
        self.assertEqual(poly.variables(), 2)
        # Degree 2 bivariate has 6 coefficients
        # (1, x, y, x^2, xy, y^2)
        self.assertEqual(poly.coefficients(), 6)

    def test_polynomial_bivariate_expand(self):
        """Test expanding bivariate polynomial"""
        poly = ip.PolynomialBivariate(1)  # degree 1
        poly.expand([1.0, 2.0])  # Expand at x=1, y=2
        # After expand, we should be able to use the polynomial

    def test_polynomial_bivariate_evaluate(self):
        """Test evaluating bivariate polynomial"""
        poly = ip.PolynomialBivariate(1)  # Linear: a + bx + cy

        # Set coefficients for: 1 + 2x + 3y
        poly.set_coefficients([1.0, 2.0, 3.0])

        # Evaluate at x=2, y=3: 1 + 2(2) + 3(3) = 1 + 4 + 9 = 14
        poly.expand([2.0, 3.0])
        result = poly.evaluate([2.0, 3.0])
        self.assertAlmostEqual(result, 14.0, places=10)


class NthOrderPolynomialUnitTest(unittest.TestCase):
    """Test suite for NthOrderPolynomial class bindings. Added: 2026-03-29."""

    def test_construction(self):
        """Test NthOrderPolynomial construction with various degrees"""
        poly = ip.NthOrderPolynomial(3)
        self.assertIsNotNone(poly)
        self.assertIn("NthOrderPolynomial", repr(poly))
        self.assertEqual(poly.variables(), 2)
        self.assertEqual(poly.coefficients(), 3)

    def test_construction_degree_1(self):
        """Test degree-1 polynomial"""
        poly = ip.NthOrderPolynomial(1)
        self.assertEqual(poly.variables(), 2)
        self.assertEqual(poly.coefficients(), 1)

    def test_construction_degree_6(self):
        """Test degree-6 polynomial (from upstream unit test)"""
        poly = ip.NthOrderPolynomial(6)
        self.assertEqual(poly.variables(), 2)
        self.assertEqual(poly.coefficients(), 6)

    def test_inherits_basis_function(self):
        """Test that NthOrderPolynomial inherits from BasisFunction"""
        poly = ip.NthOrderPolynomial(3)
        self.assertIsInstance(poly, ip.BasisFunction)
        self.assertTrue(hasattr(poly, 'set_coefficients'))
        self.assertTrue(hasattr(poly, 'evaluate'))
        self.assertTrue(hasattr(poly, 'expand'))
        self.assertTrue(hasattr(poly, 'name'))
        self.assertTrue(hasattr(poly, 'term'))
        self.assertTrue(hasattr(poly, 'coefficient'))

    def test_name(self):
        """Test name() returns the expected class name"""
        poly = ip.NthOrderPolynomial(3)
        self.assertEqual(poly.name(), "NthOrderPolynomial")

    def test_expand_and_evaluate(self):
        """Test expand + evaluate matches upstream unit test expectations.
        Upstream: degree=3, coefs=[0.5, 0.5, 0.5], vars=[2.0, 3.0]
        Terms: pow(2,3)-pow(3,3)=-19, pow(2,2)-pow(3,2)=-5, pow(2,1)-pow(3,1)=-1
        Result: 0.5*(-19) + 0.5*(-5) + 0.5*(-1) = -12.5
        """
        poly = ip.NthOrderPolynomial(3)
        poly.set_coefficients([0.5, 0.5, 0.5])
        result = poly.evaluate([2.0, 3.0])
        self.assertAlmostEqual(result, -12.5, places=10)

    def test_expand_and_evaluate_second(self):
        """Test expand + evaluate with vars=[1.0, -2.0] from upstream.
        Terms: pow(1,3)-pow(-2,3)=9, pow(1,2)-pow(-2,2)=-3, pow(1,1)-pow(-2,1)=3
        Result: 0.5*(9) + 0.5*(-3) + 0.5*(3) = 4.5
        """
        poly = ip.NthOrderPolynomial(3)
        poly.set_coefficients([0.5, 0.5, 0.5])
        result = poly.evaluate([1.0, -2.0])
        self.assertAlmostEqual(result, 4.5, places=10)

    def test_terms_after_expand(self):
        """Test that individual terms are accessible after expand"""
        poly = ip.NthOrderPolynomial(3)
        poly.set_coefficients([0.5, 0.5, 0.5])
        poly.expand([2.0, 3.0])
        # Terms: pow(2,3)-pow(3,3)=-19, pow(2,2)-pow(3,2)=-5, pow(2,1)-pow(3,1)=-1
        self.assertAlmostEqual(poly.term(0), -19.0, places=10)
        self.assertAlmostEqual(poly.term(1), -5.0, places=10)
        self.assertAlmostEqual(poly.term(2), -1.0, places=10)

    def test_expand_wrong_variable_count_raises(self):
        """Test that expand raises when given wrong number of variables"""
        poly = ip.NthOrderPolynomial(3)
        with self.assertRaises(Exception):
            poly.expand([1.0])  # needs 2 variables, not 1

    def test_repr(self):
        """Test __repr__ formatting"""
        poly = ip.NthOrderPolynomial(3)
        r = repr(poly)
        self.assertIn("NthOrderPolynomial", r)
        self.assertIn("variables=2", r)
        self.assertIn("coefficients=3", r)


class InfixToPostfixUnitTest(unittest.TestCase):
    """Test suite for InfixToPostfix class bindings. Added: 2026-03-26."""

    def test_construction(self):
        """Test basic InfixToPostfix construction"""
        converter = ip.InfixToPostfix()
        self.assertIsNotNone(converter)
        self.assertEqual(repr(converter), "InfixToPostfix()")

    def test_convert_simple_addition(self):
        """Test converting a simple addition expression"""
        converter = ip.InfixToPostfix()
        result = converter.convert("1 + 2")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_convert_simple_multiplication(self):
        """Test converting a multiplication expression"""
        converter = ip.InfixToPostfix()
        result = converter.convert("3 * 4")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_convert_precedence(self):
        """Test operator precedence in conversion"""
        converter = ip.InfixToPostfix()
        result = converter.convert("1 + 2 * 3")
        self.assertIsInstance(result, str)
        # Postfix should respect precedence: multiplication before addition
        self.assertTrue(len(result) > 0)

    def test_convert_parentheses(self):
        """Test parenthesized expression conversion"""
        converter = ip.InfixToPostfix()
        result = converter.convert("(1 + 2) * 3")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_convert_function_call(self):
        """Test converting expression with function calls"""
        converter = ip.InfixToPostfix()
        result = converter.convert("sin(1)")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_tokenize_equation(self):
        """Test tokenizing an equation string"""
        converter = ip.InfixToPostfix()
        result = converter.tokenize_equation("1+2*3")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_convert_complex_expression(self):
        """Test converting a complex nested expression"""
        converter = ip.InfixToPostfix()
        result = converter.convert("(1 + 2) * (3 - 4)")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_convert_negative_numbers(self):
        """Test converting expression with negative operator"""
        converter = ip.InfixToPostfix()
        result = converter.convert("--1")
        self.assertIsInstance(result, str)


class CubeInfixToPostfixUnitTest(unittest.TestCase):
    """Test suite for CubeInfixToPostfix class bindings. Added: 2026-03-26."""

    def test_construction(self):
        """Test CubeInfixToPostfix construction"""
        converter = ip.CubeInfixToPostfix()
        self.assertIsNotNone(converter)
        self.assertEqual(repr(converter), "CubeInfixToPostfix()")

    def test_inherits_convert(self):
        """Test that CubeInfixToPostfix inherits convert from InfixToPostfix"""
        converter = ip.CubeInfixToPostfix()
        result = converter.convert("1 + 2")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_inherits_tokenize(self):
        """Test that CubeInfixToPostfix inherits tokenize_equation"""
        converter = ip.CubeInfixToPostfix()
        result = converter.tokenize_equation("1+2")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_isinstance_of_parent(self):
        """Test that CubeInfixToPostfix is an instance of InfixToPostfix"""
        converter = ip.CubeInfixToPostfix()
        self.assertIsInstance(converter, ip.InfixToPostfix)

    def test_cube_specific_variable(self):
        """Test converting expression with cube-specific variable references"""
        converter = ip.CubeInfixToPostfix()
        # CubeInfixToPostfix recognizes cube file references like f1, f2 etc.
        result = converter.convert("f1 + f2")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


class InlineInfixToPostfixUnitTest(unittest.TestCase):
    """Test suite for InlineInfixToPostfix class bindings. Added: 2026-03-26."""

    def test_construction(self):
        """Test InlineInfixToPostfix construction"""
        converter = ip.InlineInfixToPostfix()
        self.assertIsNotNone(converter)
        self.assertEqual(repr(converter), "InlineInfixToPostfix()")

    def test_inherits_convert(self):
        """Test that InlineInfixToPostfix inherits convert from InfixToPostfix"""
        converter = ip.InlineInfixToPostfix()
        result = converter.convert("1 + 2")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_inherits_tokenize(self):
        """Test that InlineInfixToPostfix inherits tokenize_equation"""
        converter = ip.InlineInfixToPostfix()
        result = converter.tokenize_equation("1+2")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_isinstance_of_parent(self):
        """Test that InlineInfixToPostfix is an instance of InfixToPostfix"""
        converter = ip.InlineInfixToPostfix()
        self.assertIsInstance(converter, ip.InfixToPostfix)

    def test_arithmetic_expression(self):
        """Test converting standard arithmetic expression"""
        converter = ip.InlineInfixToPostfix()
        result = converter.convert("2 * 3 + 4")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_scalar_expression(self):
        """Test converting expression with scalar values typical of inline data"""
        converter = ip.InlineInfixToPostfix()
        result = converter.convert("3.14 * 2.0")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_nested_function_expression(self):
        """Test converting nested function expression"""
        converter = ip.InlineInfixToPostfix()
        result = converter.convert("abs(sin(0.5))")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


class SurfaceModelUnitTest(unittest.TestCase):
    """Test suite for SurfaceModel class bindings. Added: 2026-04-09."""

    def test_construction(self):
        """SurfaceModel() constructs without error."""
        sm = ip.SurfaceModel()
        self.assertIsNotNone(sm)

    def test_add_triplet_and_solve(self):
        """add_triplet + solve + evaluate: plane z = x + y."""
        sm = ip.SurfaceModel()
        # z = x + y: triplets for a flat plane
        for x in range(-2, 3):
            for y in range(-2, 3):
                sm.add_triplet(float(x), float(y), float(x + y))
        sm.solve()
        # Evaluate at a new point
        z = sm.evaluate(3.0, 4.0)
        self.assertAlmostEqual(z, 7.0, places=5)

    def test_add_triplets_vector(self):
        """add_triplets vector overload gives the same result as add_triplet."""
        xs = [0.0, 1.0, 0.0, 1.0, 2.0, 2.0]
        ys = [0.0, 0.0, 1.0, 1.0, 0.0, 2.0]
        zs = [x * x + y * y for x, y in zip(xs, ys)]
        sm = ip.SurfaceModel()
        sm.add_triplets(xs, ys, zs)
        sm.solve()
        # z = x^2 + y^2; evaluate at (1,1) → should be ~2
        z = sm.evaluate(1.0, 1.0)
        self.assertAlmostEqual(z, 2.0, places=4)

    def test_min_max_parabolic_bowl(self):
        """min_max returns status=0 and the minimum for a paraboloid z = x^2 + y^2."""
        # Build a dense grid so the fit is well-conditioned
        xs, ys, zs = [], [], []
        for xi in range(-3, 4):
            for yi in range(-3, 4):
                xs.append(float(xi))
                ys.append(float(yi))
                zs.append(float(xi * xi + yi * yi))
        sm = ip.SurfaceModel()
        sm.add_triplets(xs, ys, zs)
        sm.solve()
        status, x_min, y_min = sm.min_max()
        self.assertEqual(status, 0)
        self.assertAlmostEqual(x_min, 0.0, places=4)
        self.assertAlmostEqual(y_min, 0.0, places=4)

    def test_min_max_plane_returns_nonzero_status(self):
        """min_max returns status=1 for a plane (no extremum)."""
        sm = ip.SurfaceModel()
        # Pure linear plane: z = x (no quadratic terms)
        for xi in range(-3, 4):
            for yi in range(-3, 4):
                sm.add_triplet(float(xi), float(yi), float(xi))
        sm.solve()
        status, _x, _y = sm.min_max()
        self.assertEqual(status, 1)

    def test_repr(self):
        """__repr__ returns a non-empty string containing 'SurfaceModel'."""
        sm = ip.SurfaceModel()
        r = repr(sm)
        self.assertIn("SurfaceModel", r)


if __name__ == '__main__':
    unittest.main()
