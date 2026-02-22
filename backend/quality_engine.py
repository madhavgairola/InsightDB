import pandas as pd
import numpy as np

class QualityEngine:
    def __init__(self, tables, schemas, validation_policy=None):
        """
        :param tables: Dictionary of {table_name: pd.DataFrame}
        :param schemas: Dictionary of {table_name: schema_dict}
        :param validation_policy: AI-generated policy for context-aware auditing
        """
        self.tables = tables
        self.schemas = schemas
        self.validation_policy = validation_policy or {}
        self.metrics = {}

    def compute_metrics(self):
        """Computes quality metrics and upgraded Trust Score for all tables."""
        
        global_max_date = self._get_global_max_date()

        for table_name, df in self.tables.items():
            schema = self.schemas.get(table_name, {})
            table_metrics = {
                "completeness": 0.0,
                "uniqueness": 0.0,
                "freshness": 0.0,
                "orphan_rate": 0.0,
                "outlier_rate": 0.0,
                "negative_rate": 0.0,
                "trust_score": 0.0,
                "issues": [],
                "column_stats": {},
                "sub_scores": {}
            }
            
            total_rows = len(df)
            if total_rows == 0:
                self.metrics[table_name] = table_metrics
                continue
                
            # 1. Completeness (Weighted 20%)
            total_cells = df.size
            total_nulls = df.isnull().sum().sum()
            completeness = (total_cells - total_nulls) / total_cells
            table_metrics["completeness"] = round(completeness * 100, 2)
            if completeness < 0.9: table_metrics["issues"].append("High number of missing values")

            # 2. Identifier Health (Weighted 25%)
            # Check primary keys uniqueness and nullability
            id_sub_score = 100
            pk_cols = schema.get("potential_keys", [])
            for col in pk_cols:
                # PK should be 100% unique and 0% null already by definition in analyzer, 
                # but let's check identifier columns in general.
                pass
            
            # General health of all identifier columns
            id_cols = [c for c in schema.get("columns", []) if c["classification"] == "identifier"]
            if id_cols:
                id_nulls = sum([c["null_count"] for c in id_cols])
                id_uniqueness_avg = sum([c["unique_count"] for c in id_cols]) / (len(id_cols) * total_rows)
                id_sub_score = (id_uniqueness_avg * 80) + ((1 - (id_nulls / (len(id_cols) * total_rows))) * 20)
            
            table_metrics["sub_scores"]["identifier_health"] = round(id_sub_score, 2)

            # 3. FK Integrity / Referential Integrity (Weighted 25%)
            fk_sub_score = 100
            total_orphans = 0
            fks = schema.get("potential_foreign_keys", [])
            if fks:
                for fk in fks:
                    col = fk["column"]
                    target_table_name = fk["suggested_tables"][0] # Just take first suggestion for now
                    if target_table_name in self.tables:
                        target_df = self.tables[target_table_name]
                        # Assume PK in target is first potential_key or just 'id' if exists
                        target_pk = self.schemas[target_table_name]["potential_keys"][0] if self.schemas[target_table_name]["potential_keys"] else None
                        
                        if target_pk:
                            child_ids = set(df[col].dropna())
                            parent_ids = set(target_df[target_pk])
                            orphans = child_ids - parent_ids
                            
                            if orphans:
                                orphan_count = df[df[col].isin(orphans)].shape[0]
                                orphan_rate = orphan_count / total_rows
                                total_orphans += orphan_count
                                table_metrics["issues"].append(f"{round(orphan_rate*100, 2)}% orphans in {col} (ref {target_table_name})")
                
                fk_integrity_rate = 1 - (total_orphans / (len(fks) * total_rows))
                fk_sub_score = fk_integrity_rate * 100
            
            table_metrics["orphan_rate"] = round((total_orphans / total_rows) * 100, 2) if total_rows > 0 else 0
            table_metrics["sub_scores"]["fk_integrity"] = round(fk_sub_score, 2)

            # 4. Numeric Sanity (Weighted 15%)
            sanity_sub_score = 100
            total_negatives = 0
            total_outliers = 0
            num_numeric_cols = 0
            
            for col_meta in schema.get("columns", []):
                col = col_meta["name"]
                if col_meta["classification"] == "numeric":
                    num_numeric_cols += 1
                    series = df[col].dropna()
                    if series.empty: continue
                    
                    # Store stats
                    mean = series.mean()
                    std = series.std()
                    table_metrics["column_stats"][col] = {"mean": float(mean), "std": float(std)}
                    
                    # Smart Negative Check (AI Driven)
                    policy = self.validation_policy.get(table_name, {}).get(col, {})
                    is_unsigned = policy.get("is_unsigned", True) # Default to unsigned for safety
                    
                    negs = (series < 0).sum()
                    if negs > 0 and is_unsigned:
                        total_negatives += negs
                        table_metrics["issues"].append(f"Negative values in {col} (expected unsigned)")
                    elif negs > 0:
                        # If AI said signed, it's NOT a negative_rate penalty
                        pass
                    
                    # Smart Range Check (AI Driven)
                    p_range = policy.get("range")
                    if p_range and len(p_range) == 2:
                        out_of_range = ((series < p_range[0]) | (series > p_range[1])).sum()
                        if out_of_range > 0:
                            table_metrics["issues"].append(f"Value range violation in {col} (expected {p_range})")
                            total_outliers += out_of_range
                    
                    # Outliers (Z-score > 3)
                    if std > 0:
                        outliers = (np.abs((series - mean) / std) > 3).sum()
                        total_outliers += outliers
                        if outliers / total_rows > 0.05:
                            table_metrics["issues"].append(f"High outlier rate in {col} ({round(outliers/total_rows*100, 1)}%)")

            if num_numeric_cols > 0:
                neg_rate = total_negatives / (num_numeric_cols * total_rows)
                out_rate = total_outliers / (num_numeric_cols * total_rows)
                sanity_sub_score = (1 - neg_rate) * 50 + (1 - out_rate) * 50
            
            table_metrics["negative_rate"] = round((total_negatives / total_rows) * 100, 2) if total_rows > 0 else 0
            table_metrics["outlier_rate"] = round((total_outliers / total_rows) * 100, 2) if total_rows > 0 else 0
            table_metrics["sub_scores"]["numeric_sanity"] = round(sanity_sub_score, 2)

            # 5. Categorical Rare Values
            for col_meta in schema.get("columns", []):
                col = col_meta["name"]
                if col_meta["classification"] == "categorical":
                    series = df[col].dropna()
                    if series.empty: continue
                    val_counts = series.value_counts(normalize=True)
                    rare_mask = val_counts < 0.01
                    if rare_mask.any():
                        rare_count = rare_mask.sum()
                        table_metrics["issues"].append(f"{rare_count} rare categories in {col} (<1% frequency)")

            # 6. Freshness (Weighted 15%)
            freshness_score = self._calculate_freshness(df, global_max_date)
            table_metrics["freshness"] = round(freshness_score, 2)
            table_metrics["sub_scores"]["freshness"] = freshness_score

            # 7. AI Sequence Rules (Contextual Integrity)
            table_policy = self.validation_policy.get(table_name, {})
            sequence_penalty = 0
            for col, policy in table_policy.items():
                rules = policy.get("sequence_rules", [])
                for rule in rules:
                    before_col = rule.get("before")
                    after_col = rule.get("after")
                    if before_col in df.columns and after_col in df.columns:
                        # e.g. purchase before delivery
                        try:
                            t_before = pd.to_datetime(df[before_col], errors='coerce')
                            t_after = pd.to_datetime(df[after_col], errors='coerce')
                            violations = (t_before > t_after).sum()
                            if violations > 0:
                                table_metrics["issues"].append(f"Logic Error: {before_col} appears AFTER {after_col} in {violations} rows")
                                sequence_penalty += (violations / total_rows) * 10
                        except: pass
            
            # Adjust trust score based on sequence violations
            trust_score_deduction = min(sequence_penalty, 20)

            # TRUST SCORE CALCULATION (Weighted Average)
            trust_score = (
                (id_sub_score * 0.25) +
                (fk_sub_score * 0.25) +
                (completeness * 100 * 0.20) +
                (sanity_sub_score * 0.15) +
                (freshness_score * 0.15)
            )
            table_metrics["trust_score"] = max(0, round(trust_score - trust_score_deduction, 2))
            
            if table_metrics["trust_score"] < 60:
                 table_metrics["issues"].append("Critical: Low overall trust score.")

            self.metrics[table_name] = table_metrics

        return self.metrics

    def _get_global_max_date(self):
        global_max_date = pd.Timestamp.min
        for df in self.tables.values():
            for col in df.columns:
                if 'date' in col.lower() or 'time' in col.lower():
                    try:
                        tm = pd.to_datetime(df[col], errors='coerce').max()
                        if pd.notnull(tm) and tm > global_max_date: global_max_date = tm
                    except: pass
        return global_max_date if global_max_date != pd.Timestamp.min else pd.Timestamp.now()

    def _calculate_freshness(self, df, global_max):
        table_max = None
        for col in df.columns:
            if 'date' in col.lower() or 'time' in col.lower():
                try:
                    tm = pd.to_datetime(df[col], errors='coerce').max()
                    if pd.notnull(tm) and (table_max is None or tm > table_max): table_max = tm
                except: pass
        
        if not table_max: return 50.0
        days_diff = (global_max - table_max).days
        if days_diff < 30: return 100.0
        if days_diff > 365: return 20.0
        return 100 - (days_diff / 365 * 80)
