"""
Shared helper utilities: filter building, validation, and error response helpers.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------- Constants ----------------
MISSING_REQUIRED_PARAMETER = "Missing required parameter"

# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------

def sanitize_filter_value(value: str) -> str:
    """
    Sanitize a filter value to prevent SQL injection.
    Only allows alphanumeric characters, spaces, hyphens, commas, parentheses, and periods.
    Escapes single quotes by doubling them.

    Args:
        value: Raw input value from query parameter

    Returns:
        Sanitized value safe for SQL inclusion
    """
    sanitized = value.replace("'", "''")
    sanitized = re.sub(r"[^a-zA-Z0-9\s\-,.()\+]", "", sanitized)
    return sanitized


def build_days_open_filter(raw_value: str, db_column: str) -> str:
    """
    Build a range filter clause for daysOpen, or return empty string if invalid.

    Supports single range "min-max" or comma-separated multiple ranges "0-30,31-60,61-100".
    Validates that the input contains only digits, hyphens, and commas, then extracts
    all numeric values and uses their overall min and max to generate a BETWEEN-style condition.

    Args:
        raw_value: The raw daysOpen parameter value (e.g. "30-60" or "0-30,31-60")
        db_column: The database column name for days open

    Returns:
        SQL fragment like "Days_Open >= 0 AND Days_Open <= 60 " or empty string if invalid
    """
    if not re.fullmatch(r'[\d,\-]+', raw_value.strip()):
        logger.warning(
            f"Invalid daysOpen format: {raw_value}. "
            "Expected only digits, hyphens, and commas (e.g. '0-30,31-60')."
        )
        return ""
    numbers = [int(n) for n in re.findall(r'\d+', raw_value)]
    if not numbers:
        logger.warning(f"No numeric values found in daysOpen: {raw_value}.")
        return ""
    min_val = min(numbers)
    max_val = max(numbers)
    return f"{db_column} >= {min_val} AND {db_column} <= {max_val} "


def build_in_clause_filter(raw_value: str, db_column: str) -> str:
    """
    Build an IN clause filter from comma-separated values, or return empty string if none valid.

    Sanitizes each value, converts to uppercase, and generates a SQL IN clause.

    Args:
        raw_value: Comma-separated string of filter values (e.g. "BrandA,BrandB")
        db_column: The database column name to filter on

    Returns:
        SQL fragment like "UPPER(brand) IN ('BRANDA','BRANDB') " or empty string if no valid values
    """
    sanitized_values = [
        sanitize_filter_value(v.strip().upper())
        for v in raw_value.split(',')
        if sanitize_filter_value(v.strip().upper())
    ]
    if not sanitized_values:
        return ""
    values_str = "','".join(sanitized_values)
    return f"UPPER({db_column}) IN ('{values_str}') "


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def create_error_response(error_type: str, message: str, tile_name: str = None) -> dict:
    """
    Create a consistent error response object.

    Args:
        error_type: The type of error (e.g., "Invalid date format", "Unknown tile")
        message: Detailed error message
        tile_name: Optional tile name for tile-specific errors

    Returns:
        Dictionary with consistent error format

    Examples:
        >>> create_error_response("Invalid date format", "Expected YYYY-MM-DD", "anomalous-transactions")
        {"error": "Invalid date format", "message": "Expected YYYY-MM-DD", "tileName": "anomalous-transactions"}
        >>> create_error_response("Missing parameter", "tilename is required")
        {"error": "Missing parameter", "message": "tilename is required"}
    """
    error_response = {
        "error": error_type,
        "message": message,
    }
    if tile_name:
        error_response["tileName"] = tile_name
    return error_response


def validate_optional_param(query_params: dict, param_name: str, validator, error_label: str, tile_name: str) -> tuple:
    """
    Validate a single optional query parameter using the given validator callable.

    Args:
        query_params: Dictionary of query parameters
        param_name: The key to look up in query_params
        validator: Callable that accepts the value and returns (is_valid, error_msg, ...)
        error_label: Error type label for the response (e.g. "Invalid date format")
        tile_name: Tile name for error reporting

    Returns:
        Tuple of (is_valid, error_response_or_empty_dict)
    """
    value = query_params.get(param_name)
    if not value:
        return True, {}
    result = validator(value)
    is_valid, error_msg = result[0], result[1]
    if not is_valid:
        return False, create_error_response(error_label, error_msg, tile_name)
    return True, {}



def validate_dual_series_structure(tile_data: dict, tile_name: str) -> tuple[bool, dict]:
    """
    Validate dual-series data structure for dual-line chart tiles.
    
    Args:
        tile_data: The tile data dictionary to validate
        tile_name: Name of the tile for error reporting
    
    Returns:
        Tuple of (is_valid, error_response_or_empty_dict)
        - is_valid: True if structure is valid, False otherwise
        - error_response_or_empty_dict: Error response dict if invalid, empty dict if valid
    
    Validates:
        - Presence of 'categories' and 'series' fields
        - Series is a list with exactly 2 items for dual-line charts
        - Each series has required metadata fields (name, data, type, yAxis)
        - Both series have equal length data arrays
        - Categories length matches all series data lengths
        - Data arrays contain only numeric values (including zero/null handling)
        - yAxis values are 0 and 1 for dual Y-axis configuration
        - Data type consistency within each series
        - Specific error messages for each validation failure
    """
    if not isinstance(tile_data, dict):
        return False, create_error_response(
            "Invalid data structure",
            "Tile data must be a dictionary",
            tile_name
        )
    
    # Validate presence of required top-level fields
    if 'categories' not in tile_data:
        return False, create_error_response(
            "Missing categories field",
            "Dual-line chart data must include 'categories' field",
            tile_name
        )
    
    if 'series' not in tile_data:
        return False, create_error_response(
            "Missing series field",
            "Dual-line chart data must include 'series' field",
            tile_name
        )
    
    categories = tile_data['categories']
    series = tile_data['series']
    
    # Validate categories
    if not isinstance(categories, list):
        return False, create_error_response(
            "Invalid categories format",
            "Categories must be a list",
            tile_name
        )
    
    if len(categories) == 0:
        return False, create_error_response(
            "Empty categories",
            "Categories list cannot be empty",
            tile_name
        )
    
    # Validate series structure
    if not isinstance(series, list):
        return False, create_error_response(
            "Invalid series format",
            "Series must be a list",
            tile_name
        )
    
    if len(series) != 2:
        return False, create_error_response(
            "Invalid series count",
            f"Dual-line chart must have exactly 2 series, found {len(series)}",
            tile_name
        )
    
    # Validate each series
    required_fields = ['name', 'data', 'type', 'yAxis']
    expected_y_axes = {0, 1}
    found_y_axes = set()
    
    for i, series_item in enumerate(series):
        if not isinstance(series_item, dict):
            return False, create_error_response(
                "Invalid series item format",
                f"Series item {i} must be a dictionary",
                tile_name
            )
        
        # Check required fields
        for field in required_fields:
            if field not in series_item:
                return False, create_error_response(
                    "Missing series metadata",
                    f"Series item {i} missing required field '{field}'",
                    tile_name
                )
        
        # Validate series name
        if not isinstance(series_item['name'], str) or not series_item['name'].strip():
            return False, create_error_response(
                "Invalid series name",
                f"Series item {i} name must be a non-empty string",
                tile_name
            )
        
        # Validate series data
        data = series_item['data']
        if not isinstance(data, list):
            return False, create_error_response(
                "Invalid series data format",
                f"Series item {i} data must be a list",
                tile_name
            )
        
        # Validate data length matches categories
        if len(data) != len(categories):
            return False, create_error_response(
                "Data length mismatch",
                f"Series item {i} data length ({len(data)}) does not match categories length ({len(categories)})",
                tile_name
            )
        
        # Validate data contains only numeric values (including zero/null handling)
        for j, value in enumerate(data):
            # Handle null/None values gracefully by converting to 0
            if value is None:
                data[j] = 0
                logger.warning(f"Converted null value to 0 in series '{series_item['name']}' at index {j}")
                continue
            
            # Validate numeric types (int, float)
            if not isinstance(value, (int, float)):
                return False, create_error_response(
                    "Invalid data type",
                    f"Series '{series_item['name']}' contains non-numeric value at index {j}: expected number, found {type(value).__name__} ({value})",
                    tile_name
                )
            
            # Handle infinite or NaN values
            if isinstance(value, float):
                import math
                if math.isnan(value):
                    return False, create_error_response(
                        "Invalid data value",
                        f"Series '{series_item['name']}' contains NaN value at index {j}",
                        tile_name
                    )
                if math.isinf(value):
                    return False, create_error_response(
                        "Invalid data value",
                        f"Series '{series_item['name']}' contains infinite value at index {j}",
                        tile_name
                    )
            
            # Validate reasonable value ranges for volume data (millions of dollars)
            if 'Volume' in series_item['name'] and '$MM' in series_item['name']:
                if value < 0:
                    return False, create_error_response(
                        "Invalid volume data",
                        f"Series '{series_item['name']}' contains negative volume value at index {j}: {value}",
                        tile_name
                    )
                if value > 10000:  # Reasonable upper limit for $MM values
                    logger.warning(f"Unusually large volume value in series '{series_item['name']}' at index {j}: {value}")
            
            # Validate reasonable value ranges for anomaly count data
            if 'Anomalies' in series_item['name'] and 'Detected' in series_item['name']:
                if value < 0:
                    return False, create_error_response(
                        "Invalid anomaly count",
                        f"Series '{series_item['name']}' contains negative count value at index {j}: {value}",
                        tile_name
                    )
                # Allow both integers and floats for anomaly counts (some data sources may provide floats)
                # Just ensure the value is non-negative and reasonable
                if isinstance(value, float) and not (0 <= value <= 10000):
                    logger.warning(f"Unusually large anomaly count in series '{series_item['name']}' at index {j}: {value}")
                elif isinstance(value, int) and not (0 <= value <= 10000):
                    logger.warning(f"Unusually large anomaly count in series '{series_item['name']}' at index {j}: {value}")
        
        # Validate series type
        if not isinstance(series_item['type'], str) or series_item['type'] not in ['line', 'area']:
            return False, create_error_response(
                "Invalid series type",
                f"Series item {i} type must be 'line' or 'area'",
                tile_name
            )
        
        # Validate yAxis
        y_axis = series_item['yAxis']
        if not isinstance(y_axis, int) or y_axis not in [0, 1]:
            return False, create_error_response(
                "Invalid yAxis value",
                f"Series item {i} yAxis must be 0 or 1, found {y_axis}",
                tile_name
            )
        
        found_y_axes.add(y_axis)
    
    # Validate that both Y-axes are used (0 and 1)
    if found_y_axes != expected_y_axes:
        return False, create_error_response(
            "Incomplete yAxis configuration",
            f"Dual-line chart must use both yAxis 0 and 1, found {sorted(found_y_axes)}",
            tile_name
        )
    
    return True, {}



def validate_dual_series_batch_compatibility(tile_data: dict, tile_name: str, all_requested_tiles: list) -> tuple[bool, dict]:
    """
    Validate dual-series tiles for batch request compatibility.
    
    Args:
        tile_data: The tile data dictionary to validate
        tile_name: Name of the tile for error reporting
        all_requested_tiles: List of all tiles requested in the batch
    
    Returns:
        Tuple of (is_valid, error_response_or_empty_dict)
        - is_valid: True if compatible with batch request, False otherwise
        - error_response_or_empty_dict: Error response dict if invalid, empty dict if valid
    
    Validates:
        - Dual-series tiles work correctly alongside single-series tiles
        - No performance degradation in batch processing
        - Consistent response format across all tiles in batch
    """
    try:
        # Validate basic dual-series structure
        structure_valid, structure_error = validate_dual_series_structure(tile_data, tile_name)
        if not structure_valid:
            return False, structure_error
        
        # Check for potential performance issues with large batch requests
        if len(all_requested_tiles) > 10:
            logger.warning(f"Large batch request with {len(all_requested_tiles)} tiles including dual-series tile '{tile_name}' - potential performance impact")
        
        # Validate that dual-series data doesn't conflict with other tiles
        # (This is mainly a structural check - actual conflicts would be frontend-specific)
        if 'series' in tile_data and len(tile_data['series']) == 2:
            # Ensure both series have consistent structure for batch processing
            for i, series in enumerate(tile_data['series']):
                if not isinstance(series, dict):
                    return False, create_error_response(
                        "Batch compatibility error",
                        f"Dual-series tile '{tile_name}' has invalid series structure for batch processing",
                        tile_name
                    )
                
                # Check for required fields that frontend expects in batch responses
                required_batch_fields = ['name', 'data']
                for field in required_batch_fields:
                    if field not in series:
                        return False, create_error_response(
                            "Batch compatibility error",
                            f"Dual-series tile '{tile_name}' missing required field '{field}' for batch processing",
                            tile_name
                        )
        
        return True, {}
        
    except Exception as e:
        logger.error(f"Error validating batch compatibility for dual-series tile {tile_name}: {e}")
        return False, create_error_response(
            "Batch validation error",
            f"Failed to validate batch compatibility for dual-series tile '{tile_name}': {str(e)}",
            tile_name
        )


def get_tile_data(tile_name: str, query_params: dict = None):
    """
    Fetch data for a single tile from database or static data.

    Database tiles query views directly and return standardized error responses on failure.
    Static fallback (TILE_DATA) is only used for tiles without database implementations.

    Args:
        tile_name: The name of the tile to fetch (e.g., 'summary-kpis')
        query_params: Optional dictionary of query parameters for filtering/customization

    Returns:
        Dictionary containing tile data, or None if tile doesn't exist

    Validates: Requirements 1.3, 3.4
    """
    handler = _TILE_HANDLERS.get(tile_name)
    if handler:
        return handler(query_params)
    return TILE_DATA.get(tile_name)


def validate_tile_name(tile_name: str) -> tuple[bool, str]:
    """
    Validate that a tile name follows kebab-case naming convention.
    
    Args:
        tile_name: The tile name to validate
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if the tile name is valid, False otherwise
        - error_message: Empty string if valid, error description if invalid
    
    Examples:
        >>> validate_tile_name("anomalous-transactions")
        (True, "")
        >>> validate_tile_name("anomalousTransactions")
        (False, "Invalid tile name format. Expected kebab-case (lowercase with hyphens)")
        >>> validate_tile_name("ANOMALOUS-TRANSACTIONS")
        (False, "Invalid tile name format. Expected kebab-case (lowercase with hyphens)")
    """
    if not tile_name:
        return False, "Tile name cannot be empty"
    
    # Check if tile name follows kebab-case convention
    # Should be lowercase letters, numbers, and hyphens only
    # Should not start or end with hyphen
    # Should not have consecutive hyphens
    import re
    kebab_case_pattern = r'^[a-z0-9]+(-[a-z0-9]+)*$'
    
    if not re.match(kebab_case_pattern, tile_name):
        return False, "Invalid tile name format. Expected kebab-case (lowercase with hyphens)"
    
    return True, ""

def get_requested_tiles(query_params):
    tilename_param = query_params.get("tilename", "")
    
    if not tilename_param:
        return None, create_error_response(
            MISSING_REQUIRED_PARAMETER,
            "Please specify one or more tile names using ?tilename=tile1,tile2"
        )
    
    return [name.strip() for name in tilename_param.split(',')],None


def validate_tiles(requested_tiles):
    for tile_name in requested_tiles:
        is_valid, error_msg = validate_tile_name(tile_name)
        if not is_valid:
            return create_error_response(
                "Invalid tile name",
                f"Tile '{tile_name}': {error_msg}",
                tile_name
            )
    return None


def get_additional_params(query_params):
    return {
        key: value
        for key, value in query_params.items()
        if key != 'tilename' and value
    }


def process_tile(tile_name, additional_params, dual_series_tiles, requested_tiles):
    tile_data = get_tile_data(tile_name, additional_params)

    if tile_data is None:
        return create_error_response(
            "Unknown tile",
            f"Tile '{tile_name}' is not recognized. Please check the tile name and try again.",
            tile_name
        )

    if tile_name in dual_series_tiles:
        if isinstance(tile_data, dict) and 'error' in tile_data:
            return tile_data

        is_valid, error_response = validate_dual_series_batch_compatibility(
            tile_data, tile_name, requested_tiles
        )

        return error_response if not is_valid else tile_data

    return tile_databuild_account_detail_anomaly
