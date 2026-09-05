import unittest
import sys
import random
sys.path.append('/home/master/fraud_detection')
from spark_jobs.ml.check_data_drift import calculate_psi_and_ks

class TestPipeline(unittest.TestCase):
    def test_calculate_psi_and_ks_stable(self):
        random.seed(42)
        expected_data = [random.gauss(100, 15) for _ in range(500)]
        actual_data = [random.gauss(100, 15) for _ in range(500)]
        
        psi, ks_stat = calculate_psi_and_ks(expected_data, actual_data)
        self.assertGreaterEqual(psi, 0.0)
        self.assertGreaterEqual(ks_stat, 0.0)
        self.assertLess(psi, 0.1)  # Should be stable

    def test_calculate_psi_and_ks_drifted(self):
        random.seed(42)
        expected_data = [random.gauss(100, 15) for _ in range(500)]
        actual_data = [random.gauss(250, 50) for _ in range(500)]
        
        psi, ks_stat = calculate_psi_and_ks(expected_data, actual_data)
        self.assertGreater(psi, 0.25)  # Should be critical drift

if __name__ == '__main__':
    unittest.main()
