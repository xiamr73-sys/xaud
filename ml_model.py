import numpy as np
import os

class MotorEfficiencyPredictor:
    """
    A simple Neural Network (mock) to predict motor efficiency 
    based on geometric parameters.
    In a real scenario, this would load a .pth or .h5 model file.
    """
    def __init__(self):
        self.weights_1 = np.random.randn(5, 10) * 0.1
        self.bias_1 = np.zeros(10)
        self.weights_2 = np.random.randn(10, 1) * 0.1
        self.bias_2 = np.array([0.85]) # Bias towards realistic efficiency

    def predict(self, d_si, d_so, d_ri, d_ro, slots, poles, speed, torque):
        """
        Predict efficiency based on inputs.
        Inputs are normalized roughly to expected ranges.
        """
        # Feature vector: [d_so_norm, d_ro_norm, airgap_norm, slots_norm, poles_norm]
        x = np.array([
            d_so / 200.0, 
            d_ro / 200.0, 
            abs(d_si - d_ro) / 2.0, # Airgap approx
            slots / 50.0,
            poles / 50.0
        ])
        
        # Simple forward pass (Mocking a trained model)
        # Layer 1 (Relu)
        h = np.maximum(0, np.dot(x, self.weights_1) + self.bias_1)
        # Layer 2 (Sigmoid-ish output scaled)
        out = np.dot(h, self.weights_2) + self.bias_2
        
        # Add some "physics-informed" adjustments so the mock isn't totally random
        # Penalize very small airgaps or huge slot/pole counts randomly
        penalty = 0
        if abs(d_si - d_ro) < 0.5: penalty += 0.05
        
        return float(np.clip(out - penalty, 0.5, 0.98))

# Singleton instance
_predictor = MotorEfficiencyPredictor()

def predict_efficiency_dl(d_si, d_so, d_ri, d_ro, slots, poles, speed, torque):
    return _predictor.predict(d_si, d_so, d_ri, d_ro, slots, poles, speed, torque)
