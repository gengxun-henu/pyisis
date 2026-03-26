"""
Unit tests for ISIS math classes: Calculator, Affine, BasisFunction, LeastSquares, Matrix, PolynomialUnivariate, and PolynomialBivariate
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
        ls.add_known([0.0], 1.0)
        ls.add_known([1.0], 3.0)
        ls.add_known([2.0], 5.0)

        self.assertEqual(ls.knowns(), 3)

        # Solve the system
        result = ls.solve()
        self.assertIsNotNone(result)


class MatrixUnitTest(unittest.TestCase):
    """Test suite for Matrix class bindings"""

    def test_matrix_default_construction(self):
        """Test default Matrix construction"""
        mat = ip.Matrix()
        self.assertIsNotNone(mat)
        self.assertIn("Matrix", repr(mat))

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


if __name__ == '__main__':
    unittest.main()
