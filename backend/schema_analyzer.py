import pandas as pd

class SchemaAnalyzer:
    def __init__(self, tables):
        """
        :param tables: Dictionary of {table_name: pd.DataFrame}
        """
        self.tables = tables
        self.schema = {}

    def analyze(self):
        """analyzes all loaded tables and returns a schema dictionary."""
        for table_name, df in self.tables.items():
            table_info = {
                "name": table_name,
                "row_count": len(df),
                "columns": [],
                "potential_keys": [],
                "potential_foreign_keys": []
            }

            for col in df.columns:
                col_type = str(df[col].dtype)
                unique_count = df[col].nunique()
                null_count = int(df[col].isnull().sum())
                is_numeric = pd.api.types.is_numeric_dtype(df[col])
                is_datetime = 'date' in col.lower() or 'time' in col.lower() or pd.api.types.is_datetime64_any_dtype(df[col])
                
                # Context-Aware Classification
                classification = "other"
                if col.endswith("_id") or col == "id":
                    classification = "identifier"
                elif is_datetime:
                    classification = "timestamp"
                elif is_numeric:
                    classification = "numeric"
                elif df[col].dtype == "object" and unique_count < 50:
                    classification = "categorical"
                
                col_data = {
                    "name": col,
                    "type": col_type,
                    "classification": classification,
                    "unique_count": unique_count,
                    "null_count": null_count
                }
                table_info["columns"].append(col_data)

                # Potential Primary Key Inference
                if classification == "identifier" and unique_count == len(df) and null_count == 0:
                    table_info["potential_keys"].append(col)

                # Potential Foreign Key Inference
                if classification == "identifier" and not (unique_count == len(df) and null_count == 0):
                    # Look for targets: e.g. customer_id -> olist_customers_dataset
                    # We strip 'olist_' and '_dataset' to match heuristics or just check substrings
                    potential_targets = []
                    for t in self.tables.keys():
                        if t == table_name: continue
                        clean_t = t.replace("olist_", "").replace("_dataset", "")
                        clean_col = col.replace("_id", "")
                        if clean_col in clean_t or clean_t in clean_col:
                            potential_targets.append(t)
                    
                    if potential_targets:
                         table_info["potential_foreign_keys"].append({
                             "column": col,
                             "suggested_tables": potential_targets
                         })

            self.schema[table_name] = table_info

        return self.schema

    def get_table_schema(self, table_name):
        return self.schema.get(table_name)
