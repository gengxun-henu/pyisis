"""
Unit tests for ISIS math classes: Calculator, Affine, and BasisFunction
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


if __name__ == '__main__':
    unittest.main()
