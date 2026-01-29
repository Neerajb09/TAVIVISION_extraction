import math

class AorticStenosisValues:
    def __init__(self, input_data):
        self.annulus_area = self._safe_float(input_data.get("annulusArea"))
        self.anatomy = input_data.get("aorticValveAnatomyType").lower()
        self.calcium_score = int(input_data.get("calciumScore"))
        self.icd4mm = self._safe_float(input_data.get("icd4mm"))
        self.icd6mm = self._safe_float(input_data.get("icd6mm"))
        self.icd8mm = self._safe_float(input_data.get("icd8mm"))

        # Validate annulus area
        if not (270.0 <= self.annulus_area <= 840.0):
            raise ValueError(
                f"Report generation is available for annulus areas between 270–840 mm². "
                f"Received: {self.annulus_area}. Myval is not available for this annulus area."
            )

        # Calculate annulus diameter
        self.annulus_diameter = round(math.sqrt((4 * self.annulus_area) / math.pi), 1)

        # Validate anatomy type
        if "bicuspid" in self.anatomy:
            self.anatomy_type = "bicuspid"
            import re
            match = re.search(r"type\s*([0-2][a-c]?)", self.anatomy, re.I)
            self.bicuspid_type = f"Type {match.group(1)}" if match else None
        elif "tricuspid" in self.anatomy:
            self.anatomy_type = "tricuspid"
            self.bicuspid_type = None
        else:
            raise ValueError("Anatomy must include 'bicuspid' or 'tricuspid'.")
        
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
            if value == '' or value is None:
                return 0
            return float(value)
        except (TypeError, ValueError):
            return default

    def calculate_oversize_value(self):
        if self.anatomy_type == "tricuspid":
            if self.calcium_score <= 450:
                oversize_value = "10% - 15%"
                severity_range = "None to Mild"
            elif self.calcium_score <= 1000:
                oversize_value = "5% - 10%"
                severity_range = "Mild to Moderate"
            else:
                oversize_value = "0% - 5%"
                severity_range = "Severe"
        else:  # bicuspid
            oversize_value = "0% - 5%"
            if self.calcium_score <= 450:
                severity_range = "None to Mild"
            elif self.calcium_score <= 1000:
                severity_range = "Mild to Moderate"
            else:
                severity_range = "Severe"

        return oversize_value, severity_range

    def calculate_annulus_table_and_myval_size(self, oversize_value):
        myval_sizes = [20, 21.5, 23, 24.5, 26, 27.5, 29, 30.5, 32, 33.5, 35]
        myval_areas = [
            314.159, 363.05, 415.476, 471.435, 530.929, 593.957, 660.52,
            730.617, 804.248, 881.413, 962.113
        ]

        oversizing_data = []
        for size, area in zip(myval_sizes, myval_areas):
            description = ""
            if self.anatomy_type == "bicuspid":
                valid_icds = [v for v in [self.icd4mm, self.icd6mm, self.icd8mm] if v > 0]
                if not valid_icds:
                    oversizing = (area - self.annulus_area) / self.annulus_area * 100
                    oversizing_data.append({
                        "size": size, "area": area,
                        "oversizing": round(oversizing, 2),
                        "diameter": size, "description": description
                    })
                    continue

                min_icd = min(valid_icds)
                if min_icd < self.annulus_diameter:
                    oversizing = (size - min_icd) / min_icd * 100
                    description = "ICD value is smaller than the annulus diameter so MyVal size is calculated based on the ICD value"
                    oversizing_data.append({
                        "size": size, "area": area,
                        "oversizing": round(oversizing, 2),
                        "diameter": size, "description": description
                    })
                else:
                    oversizing = (area - self.annulus_area) / self.annulus_area * 100
                    oversizing_data.append({
                        "size": size, "area": area,
                        "oversizing": round(oversizing, 2),
                        "diameter": size, "description": description
                    })
            else:  # tricuspid
                oversizing = (area - self.annulus_area) / self.annulus_area * 100
                oversizing_data.append({
                    "size": size, "area": area,
                    "oversizing": round(oversizing, 2),
                    "diameter": size, "description": description
                })

        # --- select closest Myval size based on midpoint ---
        min_oversize, max_oversize = [float(x) for x in oversize_value.replace("%","").split("-")]
        midpoint = (min_oversize + max_oversize) / 2

        finite_data = [d for d in oversizing_data if math.isfinite(d["oversizing"])]

        def pick_closest(data):
            best = None
            for curr in data:
                if not best:
                    best = curr
                    continue
                d_curr = abs(curr["oversizing"] - midpoint)
                d_best = abs(best["oversizing"] - midpoint)
                if d_curr != d_best:
                    best = curr if d_curr < d_best else best
                elif abs(curr["oversizing"]) != abs(best["oversizing"]):
                    best = curr if abs(curr["oversizing"]) < abs(best["oversizing"]) else best
                else:
                    best = curr if curr["size"] < best["size"] else best
            return best

        closest = pick_closest(finite_data) if finite_data else None
        if closest and closest["oversizing"] < -2.5:
            positive_only = [d for d in finite_data if d["oversizing"] >= 0]
            if positive_only:
                closest = pick_closest(positive_only)

        warning = None if finite_data else "Note: No valid MyVal size available."

        # Filter table to 2 rows before and after closest
        if closest:
            index = finite_data.index(closest)
            filtered_table = finite_data[max(0, index-2):index+3]
            table = [{"THV_Diameters": d["diameter"], "Annular_Area_Under_Or_Over_Sizing": f"{d['oversizing']}%"} for d in filtered_table]
        else:
            table = []

        return {
            "table": table,
            "closest_myval_size": closest["diameter"] if closest else "N/A",
            "actual_oversize": closest["oversizing"] if closest else None,
            "warning": warning,
            "description": closest["description"] if closest else "N/A"
        }

    def calculate_myval_height(self, myval_size):
        heights = {
            20: 17.35, 21.5: 18.35, 23: 17.85, 24.5: 18.75, 26: 18.85,
            27.5: 19.25, 29: 20.35, 30.5: 20.9, 32: 21.14, 33.5: 21.5, 35: 21.85
        }
        size = float(str(myval_size).split()[0])
        return str(heights.get(size, "N/A"))

    def calculate_all(self):
        oversize_value, severity_range = self.calculate_oversize_value()
        result = self.calculate_annulus_table_and_myval_size(oversize_value)
        height = self.calculate_myval_height(result["closest_myval_size"])
        print(result["description"])
        return {
            "annulus_diameter": self.annulus_diameter,
            "oversize_value": oversize_value,
            "CalciumSeverity": severity_range,
            "myval_size": result["closest_myval_size"],
            "actual_oversize": result["actual_oversize"],
            "myval_height": height,
            "aortic_valve_anatomy": self.anatomy_type,
            "bicuspid_type": self.bicuspid_type,
            "annulus_table": result["table"],
            "warning": result["warning"],
            "description": result["description"],
        }

# # Example usage
# if __name__ == "__main__":
#     aortic = AorticStenosisValues(500, "Tricuspid", 600, 0, 0, 0)
#     print(aortic.calculate_all())
