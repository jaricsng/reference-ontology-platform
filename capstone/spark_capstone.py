#!/usr/bin/env python3
"""Capstone scale demonstration: re-implement the Module 1 transform in Spark.

Same input (admissions.csv), same logic (clean → dedupe → marts), different
engine. We then compare the Spark marts row-for-row against the dbt/DuckDB marts
to prove the logic was portable: only the compute engine changed.

The point: the *transform is code*, independent of the runtime. DuckDB ran it
in-process on a laptop; Spark would run it across a cluster on billions of rows —
identical results.
"""
from __future__ import annotations

import os
import sys

import duckdb
import pandas as pd
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RAW = os.path.join(REPO, "m1-ingestion", "data", "raw", "admissions.csv")
DUCKDB = os.path.join(REPO, "m1-ingestion", "hospital_ingest", "hospital.duckdb")
OUT = os.path.join(HERE, "output")
TS_FMT = "yyyy-MM-dd'T'HH:mm:ss"


def build_spark_marts(spark: SparkSession) -> dict:
    # Read every column as a string (mirrors DuckDB reading text then casting),
    # preserving whitespace so our trim() does the cleaning.
    df = (spark.read
          .option("header", True)
          .option("ignoreLeadingWhiteSpace", False)
          .option("ignoreTrailingWhiteSpace", False)
          .csv(RAW))

    # --- staging: clean types, trim/normalise, drop invalid rows ---
    cleaned = df.select(
        F.trim("admission_id").alias("admission_id"),
        F.trim("patient_id").alias("patient_id"),
        F.trim("patient_name").alias("patient_name"),
        F.trim("ward_name").alias("ward_name"),
        F.upper(F.trim("bed_code")).alias("bed_code"),
        F.to_timestamp("admit_ts", TS_FMT).alias("admitted_at"),
        F.when(F.trim("discharge_ts") == "", None)
         .otherwise(F.to_timestamp(F.trim("discharge_ts"), TS_FMT)).alias("discharged_at"),
    ).where(
        (F.col("admission_id") != "") & F.col("admission_id").isNotNull()
        & (F.col("patient_id") != "") & F.col("patient_id").isNotNull()
    )

    # --- dedupe on admission_id (keep latest by admitted_at) ---
    w = Window.partitionBy("admission_id").orderBy(F.col("admitted_at").desc_nulls_last())
    stg = (cleaned.withColumn("_rn", F.row_number().over(w))
           .where(F.col("_rn") == 1).drop("_rn")
           .withColumn("status", F.when(F.col("discharged_at").isNull(), "current")
                                  .otherwise("discharged")))

    # --- marts (mirror dim_bed / dim_patient / fct_admission) ---
    dim_bed = stg.groupBy("bed_code").agg(F.first("ward_name").alias("ward_name"))
    dim_patient = stg.groupBy("patient_id").agg(F.max("patient_name").alias("patient_name"))
    fct_admission = stg.select("admission_id", "patient_id", "bed_code", "ward_name",
                               "admitted_at", "discharged_at", "status")

    # Write parquet artifacts (what a real Spark job would emit).
    for name, d in [("dim_bed", dim_bed), ("dim_patient", dim_patient), ("fct_admission", fct_admission)]:
        d.write.mode("overwrite").parquet(os.path.join(OUT, name))

    return {"dim_bed": dim_bed.toPandas(),
            "dim_patient": dim_patient.toPandas(),
            "fct_admission": fct_admission.toPandas()}


def duckdb_marts() -> dict:
    con = duckdb.connect(DUCKDB, read_only=True)
    out = {t: con.execute(f"select * from {t}").df() for t in
           ("dim_bed", "dim_patient", "fct_admission")}
    con.close()
    return out


def normalise(pdf: pd.DataFrame) -> set:
    """Row-set of a mart, with timestamps normalised to ISO strings so the two
    engines' types compare cleanly."""
    pdf = pdf.copy()
    for c in pdf.columns:
        if c.endswith("_at"):  # admitted_at / discharged_at only
            pdf[c] = pd.to_datetime(pdf[c]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return set(tuple(None if pd.isna(v) else v for v in row)
               for row in pdf[sorted(pdf.columns)].itertuples(index=False, name=None))


def main() -> None:
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    spark = (SparkSession.builder.appName("hospital-capstone")
             .master("local[*]")
             .config("spark.driver.bindAddress", "127.0.0.1")
             .config("spark.ui.enabled", "false")
             .config("spark.sql.shuffle.partitions", "8")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")

    print(f"Spark {spark.version} — running the M1 transform on {os.path.basename(RAW)}\n")
    spark_m = build_spark_marts(spark)
    duck_m = duckdb_marts()
    spark.stop()

    print(f"{'mart':<16}{'spark rows':>12}{'duckdb rows':>14}{'identical?':>14}")
    print("-" * 56)
    all_ok = True
    for name in ("dim_bed", "dim_patient", "fct_admission"):
        s, d = spark_m[name], duck_m[name]
        ok = normalise(s) == normalise(d)
        all_ok = all_ok and ok and len(s) == len(d)
        print(f"{name:<16}{len(s):>12}{len(d):>14}{('YES ✅' if ok else 'NO ❌'):>14}")

    print("-" * 56)
    print("\nRESULT:", "Spark output is IDENTICAL to the DuckDB version ✅" if all_ok
          else "MISMATCH ❌")
    print("Same logic, different engine — the transform was portable.")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
