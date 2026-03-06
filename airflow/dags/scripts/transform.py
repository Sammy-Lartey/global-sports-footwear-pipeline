import pandas as pd
import logging

logger = logging.getLogger(__name__)

def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    
    
    logger.info(f"Starting transformation on {len(df)} rows")
    
    df_transformed = df.copy()
    
    # 1. Recalculate derived columns
    if all(col in df_transformed.columns for col in ['base_price_usd', 'discount_percent']):
        df_transformed['final_price_usd'] = df_transformed['base_price_usd'] * (1 - df_transformed['discount_percent'] / 100)
        logger.info("Recalculated final_price_usd")
    
    if all(col in df_transformed.columns for col in ['final_price_usd', 'units_sold']):
        df_transformed['revenue_usd'] = df_transformed['final_price_usd'] * df_transformed['units_sold']
        logger.info("Recalculated revenue_usd")
    
    # 2. Add date features
    if 'order_date' in df_transformed.columns:
        df_transformed['year'] = df_transformed['order_date'].dt.year
        df_transformed['month'] = df_transformed['order_date'].dt.month
        df_transformed['day_of_week'] = df_transformed['order_date'].dt.dayofweek
        logger.info("Added date features")
    
    # 3. Add discount amount
    if all(col in df_transformed.columns for col in ['base_price_usd', 'discount_percent']):
        df_transformed['discount_amount'] = df_transformed['base_price_usd'] * (df_transformed['discount_percent'] / 100)
    
    # 4. Convert column names to camelCase (for Silver layer)
    def to_camel_case(col_name):
        parts = col_name.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])
    
    df_transformed.columns = [to_camel_case(col) for col in df_transformed.columns]
    logger.info("Converted column names to camelCase")
    
    logger.info(f"Transformation complete. {len(df_transformed)} rows, {len(df_transformed.columns)} columns")
    return df_transformed