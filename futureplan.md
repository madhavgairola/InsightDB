# InsightDB Future Roadmap 🚀

This document outlines planned upgrades and features designed to move InsightDB from a hackathon MVP to a mature, enterprise-grade data intelligence platform.

## 1. AI-Driven Dynamic Audit Rules
**Goal**: Eliminate false positives in data quality audits (e.g., flagging Latitude/Longitude as "invalid negative values").

- **Mechanism**: On system initialization, perform a one-time "Schema Intent Analysis" using an LLM.
- **Workflow**:
    1. AI analyzes column names, data types, and sample distributions.
    2. AI generates a `validation_policy.json` (e.g., `{"price": "unsigned", "latitude": "signed"}`).
    3. The `QualityEngine` consumes this policy to apply context-aware rules.
- **Impact**: Makes the system truly universal—it can audit an e-commerce DB today and a scientific telemetry DB tomorrow without code changes.

## 2. Deep Referential Integrity Graphs
- **Idea**: Beyond calculating simple orphan rates, visualize the entire database relationship graph.
- **Feature**: Highlight "broken branches" in the UI where referential integrity falls below a certain threshold.

## 3. Advanced Outlier Reasoning
- **Idea**: Use AI to explain *why* something is an outlier.
- **Feature**: Instead of just flagging a Z-score > 3, use the LLM to check if the high value correlates with other factors (e.g., "This shipping price is high because the product weight is in the 99th percentile").

## 4. Multi-Source Integration
- **Idea**: Support connecting to live SQL databases (PostgreSQL, MySQL, Snowflake) rather than just static CSV files.
