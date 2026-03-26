import pandas as pd
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validates the dataframe and returns two dataframes:
    - df_valid: rows that passed all checks
    - df_rejected: rows that failed, with rejection_reason and rejected_at columns
    """
    logger.info(f"Starting validation on {len(df)} rows")

    df_clean = df.copy()
    rejected_frames = []

    def collect_rejected(mask: pd.Series, reason: str):
        rejected = df_clean[mask].copy()
        if not rejected.empty:
            rejected['rejection_reason'] = reason
            rejected['rejected_at'] = datetime.utcnow()
            rejected_frames.append(rejected)
        return df_clean[~mask].copy()

    # 1. Remove duplicate orders
    if 'order_id' in df_clean.columns:
        dupes = df_clean.duplicated(subset=['order_id'], keep='first')
        before = len(df_clean)
        rejected = df_clean[dupes].copy()
        if not rejected.empty:
            rejected['rejection_reason'] = 'duplicate order_id'
            rejected['rejected_at'] = datetime.utcnow()
            rejected_frames.append(rejected)
        df_clean = df_clean[~dupes].copy()
        logger.info(f"Removed {before - len(df_clean)} duplicate orders")

    # 2. Remove rows missing critical info
    critical_cols = ['order_id', 'brand', 'units_sold']
    for col in critical_cols:
        if col in df_clean.columns:
            mask = df_clean[col].isna()
            before = len(df_clean)
            df_clean = collect_rejected(mask, f'missing {col}')
            logger.info(f"Removed {before - len(df_clean)} rows with missing {col}")

    # 3. Convert data types
    if 'order_date' in df_clean.columns:
        df_clean['order_date'] = pd.to_datetime(df_clean['order_date'], errors='coerce')

    numeric_cols = ['size', 'base_price_usd', 'discount_percent', 'final_price_usd',
                    'units_sold', 'revenue_usd', 'customer_rating']
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    # 4. Drop rows where critical numeric fields couldn't be coerced
    critical_numeric = ['units_sold', 'base_price_usd']
    for col in critical_numeric:
        if col in df_clean.columns:
            mask = df_clean[col].isna()
            before = len(df_clean)
            df_clean = collect_rejected(mask, f'non-numeric value in {col}')
            logger.info(f"Removed {before - len(df_clean)} rows with non-numeric {col}")

    # 5. Remove invalid discounts
    if 'discount_percent' in df_clean.columns:
        mask = (df_clean['discount_percent'] < 0) | (df_clean['discount_percent'] > 100)
        before = len(df_clean)
        df_clean = collect_rejected(mask, 'invalid discount_percent (outside 0-100)')
        logger.info(f"Removed {before - len(df_clean)} rows with invalid discounts")

    # Combine all rejected rows
    if rejected_frames:
        df_rejected = pd.concat(rejected_frames, ignore_index=True)
    else:
        df_rejected = pd.DataFrame()

    logger.info(f"Validation complete. {len(df_clean)} valid rows, {len(df_rejected)} rejected rows")
    return df_clean, df_rejected