import pandas as pd
import logging

logger = logging.getLogger(__name__)

def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    
    logger.info(f"Starting transformation on {len(df)} rows")
    
    df_transformed = df.copy()
    
    
    # 1. Type enforcement
    # Ensures numeric columns are actually numeric
    # Prevents issues like "10" * 5 = wrong results
    
    for col in ['base_price_usd', 'discount_percent', 'units_sold']:
        if col in df_transformed.columns:
            df_transformed[col] = pd.to_numeric(df_transformed[col], errors='coerce')
    
    
    # 2. Handle missing values
    # Prevents NaNs from breaking calculations
    
    if 'discount_percent' in df_transformed.columns:
        df_transformed['discount_percent'] = df_transformed['discount_percent'].fillna(0)
    
    if 'units_sold' in df_transformed.columns:
        df_transformed['units_sold'] = df_transformed['units_sold'].fillna(0)
    
    
    # 3. Recalculate derived columns
    # Only runs if required columns exist
    
    
    # Final price
    if all(col in df_transformed.columns for col in ['base_price_usd', 'discount_percent']):
        df_transformed['final_price_usd'] = (
            df_transformed['base_price_usd'] * 
            (1 - df_transformed['discount_percent'] / 100)
        )
        logger.info("Recalculated final_price_usd")
    
    # Revenue
    if all(col in df_transformed.columns for col in ['final_price_usd', 'units_sold']):
        df_transformed['revenue_usd'] = (
            df_transformed['final_price_usd'] * 
            df_transformed['units_sold']
        )
        logger.info("Recalculated revenue_usd")
    
    
    # 4. Date handling + features
    # - Converts to datetime safely
    # - Adds STRING + NUMERIC versions
    
    # -------------------------------
# 4. Date handling + features (SIMPLIFIED)
# - Converts to datetime safely
# - Adds ONLY string features (as requested)
# -------------------------------
    if 'order_date' in df_transformed.columns:
        df_transformed['order_date'] = pd.to_datetime(
            df_transformed['order_date'], errors='coerce'
        )
        
        df_transformed['year'] = df_transformed['order_date'].dt.year
        df_transformed['month'] = df_transformed['order_date'].dt.month_name()
        df_transformed['day_of_week'] = df_transformed['order_date'].dt.day_name()
        
        logger.info("Added date features (year, month, day_of_week)")
    
    
    # 5. Discount amount
    
    if all(col in df_transformed.columns for col in ['base_price_usd', 'discount_percent']):
        df_transformed['discount_amount'] = (
            df_transformed['base_price_usd'] * 
            (df_transformed['discount_percent'] / 100)
        )
    
    
    # 6. Column name standardization (camelCase)
    
    def to_camel_case(col_name):
        parts = col_name.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])
    
    df_transformed.columns = [to_camel_case(col) for col in df_transformed.columns]
    logger.info("Converted column names to camelCase")
    
    
    # 7. Final logging
    
    logger.info(
        f"Transformation complete. "
        f"{len(df_transformed)} rows, {len(df_transformed.columns)} columns"
    )
    
    return df_transformed