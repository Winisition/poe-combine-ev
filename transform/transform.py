# Databricks notebook source
# Packages

from pyspark.sql import functions as F

# COMMAND ----------

# Get scarab weights

scarab_weights_raw = spark.read.json("/Volumes/workspace/poe_economy/raw_data/Scarab_Weights.json")

tbl_scarab_weights = (
    scarab_weights_raw
    .select(F.explode("scarabs").alias("scarab"))
    .select(
        F.col("scarab.id").alias("id"),
        F.col("scarab.weight")))

total_weight = tbl_scarab_weights.agg(F.sum("weight")).collect()[0][0]

tbl_scarab_probability = (

    tbl_scarab_weights
    .withColumn("probability", F.col("weight") / total_weight)
    .drop('weight')
)

# COMMAND ----------

# Get currency ratios

currency_raw = spark.read.json("/Volumes/workspace/poe_economy/raw_data/Currency.json")

# Unused: prices are already in chaos. Kept in case the price units change.
divine_ratio = (
    currency_raw
    .filter(F.col('id') == 'divine')
    .select("primaryValue")
    .collect()[0][0]
)

primal_lifeforce_ratio = (
    currency_raw
    .filter(F.col('id') == 'primal-lifeforce')
    .select("primaryValue")
    .collect()[0][0]
)


# COMMAND ----------

# Build scarab profit table

scarab_raw = spark.read.json("/Volumes/workspace/poe_economy/raw_data/Scarab.json")

tbl_scarab_joined = (

    scarab_raw
        .select('current_league','id','ingested_at','primaryValue')
        .join(tbl_scarab_probability, on = 'id',how = 'left')
                    
)

tbl_scarab_value = (
    tbl_scarab_joined.withColumn("primaryvalue_probability", F.col("primaryValue")*F.col("probability"))
)

scarab_ev = tbl_scarab_value.agg(F.sum("primaryvalue_probability")).collect()[0][0]
scarab_threshold = scarab_ev / 3

final_scarab_tbl= (

    tbl_scarab_joined
        .withColumn("profit_margin_chaos", F.round(F.lit(scarab_threshold) - F.col('primaryValue'),2))
        .drop("probability")
        .withColumnRenamed('PrimaryValue', 'total_cost')
        .sort(F.col("profit_margin_chaos").desc())
        .withColumn('Action', F.when(F.col('profit_margin_chaos') > 0,'Buy').otherwise("Ignore"))
)

# COMMAND ----------

# Build essence profit table

essence_raw = spark.read.json("/Volumes/workspace/poe_economy/raw_data/Essence.json")

corrupted = 'delirium|horror|hysteria|insanity'
normal = 'deafening'

tbl_essence_joined = (
    essence_raw
    .select('current_league','id','ingested_at','primaryValue')
    .filter(F.col('id').rlike(corrupted) | F.col('id').contains(normal))
    .withColumn('essence_type', F.when(F.col('id').rlike(corrupted), 'corrupted').otherwise('normal'))
    # 50 primal lifeforce = the in-game cost to swap an essence
    .withColumn('lifeforce_cost', F.lit(primal_lifeforce_ratio) * 50)
    .withColumn('total_cost', F.col('primaryValue') + F.col('lifeforce_cost'))
)

essence_ev = (
    tbl_essence_joined
    .groupby('essence_type')
    .agg(F.avg("primaryValue").alias('essence_ev'))
)

final_essence_tbl = (

    tbl_essence_joined
    .join(essence_ev, on = 'essence_type', how = 'left')
    .withColumn('profit_margin_chaos', F.round(F.col('essence_ev') - F.col('total_cost'),2))
    .sort(F.col("profit_margin_chaos").desc())
    .select('current_league','id','ingested_at','total_cost','profit_margin_chaos')
    .sort(F.col("profit_margin_chaos").desc())
    .withColumn('Action', F.when(F.col('profit_margin_chaos') > 0,'Buy').otherwise("Ignore"))
)

# COMMAND ----------

final_scarab_tbl.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("workspace.poe_economy.scarab_ev")
final_essence_tbl.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("workspace.poe_economy.essence_ev")