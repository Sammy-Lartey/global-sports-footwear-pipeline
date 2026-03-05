import pandas as pd
import logging

# logging setup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    
    
    logger.info(f"Starting validation on {len(df)} rows")
    
    # Make a copy
    df_clean = df.copy()
    

    # 1. Remove duplicate orders
    if 'order_id' in df_clean.columns:
        before = len(df_clean)
        df_clean = df_clean.drop_duplicates(subset=['order_id'])
        logger.info(f"Removed {before - len(df_clean)} duplicate orders")
    

    # 2. Remove rows missing critical info
    critical_cols = ['order_id', 'brand', 'units_sold']
    for col in critical_cols:
        if col in df_clean.columns:
            before = len(df_clean)
            df_clean = df_clean.dropna(subset=[col])
            logger.info(f"Removed {before - len(df_clean)} rows with missing {col}")
    

    # 3. Convert data types

    # Date columns
    if 'order_date' in df_clean.columns:
        df_clean['order_date'] = pd.to_datetime(df_clean['order_date'], errors='coerce')
    
    # Numeric columns
    numeric_cols = ['size', 'base_price_usd', 'discount_percent', 'final_price_usd', 
                    'units_sold', 'revenue_usd', 'customer_rating']
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # Drop rows where critical numeric fields couldn't be coerced
    critical_numeric = ['units_sold', 'base_price_usd']
    before = len(df_clean)
    df_clean = df_clean.dropna(subset=[c for c in critical_numeric if c in df_clean.columns])
    logger.info(f"Removed {before - len(df_clean)} rows with non-numeric critical values")
    
    # 4. validation
    if 'discount_percent' in df_clean.columns:
        # Remove invalid discounts (negative or >100%)
        invalid = (df_clean['discount_percent'] < 0) | (df_clean['discount_percent'] > 100)
        df_clean = df_clean[~invalid]
        logger.info(f"Removed {invalid.sum()} rows with invalid discounts")
    
    logger.info(f"Validation complete. {len(df_clean)} rows remain")
    return df_clean