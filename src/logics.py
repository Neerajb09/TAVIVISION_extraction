import pandas as pd
# import re

class ConditionEvaluator:
    def __init__(self, input_data):
        """
        Initializes the ConditionEvaluator with values provided in a dictionary.

        Parameters:
            input_data (dict): A dictionary containing the input values.
        """
        self.input_data = input_data
        self.STJ = self._safe_float(input_data.get("stjDiameter"))
        self.Annulus_dia = self._safe_float(input_data.get("annulusDiameter"))
        self.LVOT = self._safe_float(input_data.get("lvotDiameter"))
        self.Asc_Aorta = self._safe_float(input_data.get("ascAortaDiameter"))
        self.RCA = self._safe_float(input_data.get("rcaHeight"))
        self.LCA = self._safe_float(input_data.get("lcaHeight"))
        self.SOV_Height = self._safe_float(input_data.get("sovHeight"))
        self.SOV_left = self._safe_float(input_data.get("sovLeftDiameter"))
        self.SOV_right = self._safe_float(input_data.get("sovRightDiameter"))
        self.SOV_non = self._safe_float(input_data.get("sovNonDiameter"))
        self.SOV_Dia = self._safe_float(input_data.get("sovDiameter"))
        self.Valve_anatomy = input_data.get("aorticValveAnatomyType")  # Default to 'Unknown'
        self.Calcium = self._safe_float(input_data.get("calciumScore"))
        self.ICD4mm = self._safe_float(input_data.get("icd4mm"))
        self.ICD6mm = self._safe_float(input_data.get("icd6mm"))
        self.ICD8mm = self._safe_float(input_data.get("icd8mm"))
        self.VTCR = self._safe_float(input_data.get("vtcR"))
        self.VTCL = self._safe_float(input_data.get("vtcL"))
        

    def _safe_float(self, value, default=0.0):
        """
        Safely converts a value to float. Returns a default value if the input is None or invalid.

        Parameters:
            value: The value to convert.
            default: The default value to return if conversion fails.

        Returns:
            float: The converted float value or the default value.
        """
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
        
    def extract_valve_type(self, sentence):
        if sentence is None:
            return "Not Found"
        sentence = sentence.lower()
        if 'bicuspid' in sentence:
            return 'bicuspid'
        elif 'tricuspid' in sentence:
            return 'tricuspid'
        else:
            return 'Not Found'

    def evaluate_STJ(self):
        if self.STJ is None or self.Annulus_dia is None:
            return ["Not Eligible", None, None, None]
        if self.STJ >= self.Annulus_dia:
            return ["Favourable", ((self.STJ - self.Annulus_dia) / self.Annulus_dia) * 100, None, str(self.Annulus_dia)+' mm']
        else:
            return ["Attention Required", None, ((self.Annulus_dia - self.STJ) / self.Annulus_dia) * 100, str(self.Annulus_dia)+' mm']

    def evaluate_SOV(self, SOV_value):
        # print("a", SOV_value)
        if SOV_value == "None" or SOV_value is None or int(SOV_value) == 0 or self.Annulus_dia is None:
            return ["Not Eligible", None, None, None]
        threshold = self.Annulus_dia * 1.2
        if SOV_value >= threshold:
            return ["Favourable", ((SOV_value - threshold) / threshold) * 100, None, str(round(threshold,2))+' mm']
        else:
            return ["Attention Required", None, ((threshold - SOV_value ) / threshold) * 100, str(round(threshold,2))+' mm']

    def evaluate_RCA(self):
        if self.RCA is None:
            return ["Not Eligible", None, None, None]
        if self.RCA >= 10:
            return ["Favourable", (self.RCA - 10) * 10, None, '10 mm']
        else:
            return ["Attention Required", None, (10 - self.RCA) * 10, '10 mm']

    def evaluate_LCA(self):
        if self.LCA is None:
            return ["Not Eligible", None, None, None]
        if self.LCA >= 10:
            return ["Favourable", (self.LCA - 10) * 10, None, '10 mm']
        else:
            return ["Attention Required", None, (10 - self.LCA) * 10, '10 mm']

    def evaluate_LVOT(self):
        if self.LVOT is None or self.Annulus_dia is None:
            return ["Not Eligible", None, None, None]
        if self.LVOT >= self.Annulus_dia:
            return ["Favourable", ((self.LVOT - self.Annulus_dia) / self.Annulus_dia) * 100, None, str(self.Annulus_dia)+' mm']
        else:
            return ["Attention Required", None, ((self.Annulus_dia - self.LVOT) / self.Annulus_dia) * 100, str(self.Annulus_dia)+' mm']

    def evaluate_Valve_anatomy(self):
        if self.Valve_anatomy is None:
            return ["Not Eligible", None, None, None]
        valve_type = self.extract_valve_type(self.Valve_anatomy)
        if valve_type == "bicuspid":
            return ["Attention Required", None, None, "Tricuspid"]
        else:
            return ["Favourable", None, None, "Tricuspid"]

    def evaluate_Calcium(self):
        if self.Calcium is None:
            return ["Not Eligible", None, None, None]
        if self.Calcium > 1000:
            return ["Attention Required", None, (self.Calcium - 1000) / 10, '1000 mm³']
        else:
            return ["Favourable", (1000 - self.Calcium) / 10, None, '1000 mm³']
        
    def evaluate_ICD(self, ICD):
        if ICD is None or self.Annulus_dia is None:
            return ["Not Eligible", None, None, None]
        threshold = self.Annulus_dia
        # print(threshold)
        if ICD >= threshold:
            return ["Favourable", ((ICD - threshold) / threshold) * 100, None, str(round(threshold,2))+' mm']
        else:
            return ["Attention Required", None, ((threshold - ICD) / threshold) * 100, str(round(threshold,2))+' mm']
    
    def evaluate_Asc_Aorta(self):
        if self.Asc_Aorta is None:
            return ["Not Eligible", None, None, None]
        threshold = 40
        if self.Asc_Aorta < threshold:
            return ["Favourable", None, None, "40 mm"]
        else:
            return ["Attention Required", None, ((self.Asc_Aorta - threshold) / threshold) * 100, "40 mm"]

    def evaluate_VTC(self, vtc):
        if vtc is None or vtc is 0.0:
            return ["Not Eligible", None, None, None]
        threshold = 4.0
        # print(threshold)
        if vtc >= threshold:
            return ["Favourable", ((vtc - threshold) / threshold) * 100, None, str(round(threshold,2))+' mm']
        else:
            return ["Attention Required", None, ((threshold - vtc) / threshold) * 100, str(round(threshold,2))+' mm']
            
        
    def evaluate_all(self):
        return {
            "stjDiameter": self.evaluate_STJ(),
            "sovRightDiameter": self.evaluate_SOV(self.SOV_right),
            "sovLeftDiameter": self.evaluate_SOV(self.SOV_left),
            "sovNonDiameter": self.evaluate_SOV(self.SOV_non),
            "sovDiameter": self.evaluate_SOV(self.SOV_Dia),
            "icd4mm": self.evaluate_ICD(self.ICD4mm),
            "icd6mm": self.evaluate_ICD(self.ICD6mm),
            "icd8mm": self.evaluate_ICD(self.ICD8mm),
            "rcaHeight": self.evaluate_RCA(),
            "lcaHeight": self.evaluate_LCA(),
            "lvotDiameter": self.evaluate_LVOT(),
            "ascAortaDiameter": self.evaluate_Asc_Aorta(),
            "aorticValveAnatomyType": self.evaluate_Valve_anatomy(),
            "calciumScore": self.evaluate_Calcium(),
            "vtcL": self.evaluate_VTC(self.VTCL),
            "vtcR": self.evaluate_VTC(self.VTCR),
            
        }

    def generate_results_table(self):
        evaluations = self.evaluate_all()
        data = []

        for criteria, result in evaluations.items():
            row = {
                "Criteria": criteria,
                "Value": self.input_data.get(criteria),
                "Favourable or Attention Required": result[0],
                "Favourable %": result[1] if result[1] is not None else '',
                "Attention Required %": result[2] if result[2] is not None else '',
                "Threshold Value": result[3]
            }
            data.append(row)
            
        return data
        # return pd.DataFrame(data)

# Example Usage
# input_values = {
#     "stjDiameter": 36.0,
#     "sovHeight": 16,
#     "annulusDiameter": 26.1,
#     "sovLeftDiameter": 30,
#     "sovRightDiameter": 33.1,
#     "sovNonDiameter": 32,
#     "rcaHeight": 17.8,
#     "lcaHeight": 21.6,
#     "lvotDiameter": 25.1,
#     "aorticValveAnatomyType": "Bicuspid Type 1a",
#     "calciumScore": 1449,
#     "icd4mm" : 27,
#     "icd6mm" : 29.5,
#     "icd8mm" : 31,
#     "ascAortaDiameter" : 43,
#     # "vtcL": 5,
#     # "vtcR": 6
# }

# evaluator = ConditionEvaluator(input_values)
# results_table = evaluator.generate_results_table()
# print(results_table)
