import re
from datetime import datetime



def validate_date_format(date_string: str) -> tuple[bool, str]:
    """
    Validate that a date string is in ISO 8601 format (YYYY-MM-DD).
    
    Args:
        date_string: The date string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if the date is valid, False otherwise
        - error_message: Empty string if valid, error description if invalid
    
    Examples:
        >>> validate_date_format("2025-01-15")
        (True, "")
        >>> validate_date_format("2025-1-15")
        (False, "Invalid date format. Expected ISO 8601 format (YYYY-MM-DD)")
        >>> validate_date_format("invalid")
        (False, "Invalid date format. Expected ISO 8601 format (YYYY-MM-DD)")
    """
    if not date_string:
        return True, ""  # Empty/None dates are valid (optional parameter)
    
    try:
        # Attempt to parse the date string
        parsed_date = datetime.strptime(date_string, "%Y-%m-%d")
        
        # Verify the format matches exactly (prevents dates like "2025-1-5" from passing)
        if date_string != parsed_date.strftime("%Y-%m-%d"):
            return False, "Invalid date format. Expected ISO 8601 format (YYYY-MM-DD)"
        
        return True, ""
    except ValueError:
        return False, "Invalid date format. Expected ISO 8601 format (YYYY-MM-DD)"



def validate_limit_parameter(limit: str) -> tuple[bool, str, int]:
    """
    Validate and convert a limit parameter to integer.
    
    Args:
        limit: The limit string to validate and convert
    
    Returns:
        Tuple of (is_valid, error_message, converted_value)
        - is_valid: True if the limit is valid, False otherwise
        - error_message: Empty string if valid, error description if invalid
        - converted_value: Integer value if valid, None if invalid
    
    Examples:
        >>> validate_limit_parameter("10")
        (True, "", 10)
        >>> validate_limit_parameter("invalid")
        (False, "Invalid limit parameter. Expected positive integer", None)
        >>> validate_limit_parameter("-5")
        (False, "Invalid limit parameter. Expected positive integer", None)
    """
    if not limit:
        return True, "", None  # Empty/None limit is valid (optional parameter)
    
    try:
        limit_int = int(limit)
        if limit_int <= 0:
            return False, "Invalid limit parameter. Expected positive integer", None
        return True, "", limit_int
    except (ValueError, TypeError):
        return False, "Invalid limit parameter. Expected positive integer", None


def validate_account_id_parameters(query_params: dict, tile_name: str) -> tuple[bool, dict, str, str]:
    """
    Validate that exactly one of 340bId or pharmacyId is provided.
    
    This function enforces the mutual exclusivity requirement for account ID parameters.
    Exactly one of 340bId or pharmacyId must be provided, but not both and not neither.
    
    Args:
        query_params: Dictionary of query parameters to validate
        tile_name: Name of the tile for error reporting
    
    Returns:
        Tuple of (is_valid, error_response, id_type, id_value)
        - is_valid: True if validation passes, False otherwise
        - error_response: Error response dict if invalid, empty dict if valid
        - id_type: "340B" or "Pharmacy" if valid, None if invalid
        - id_value: The ID value if valid, None if invalid
    
    Examples:
        >>> validate_account_id_parameters({"340bId": "123"}, "test-tile")
        (True, {}, "340B", "123")
        >>> validate_account_id_parameters({"pharmacyId": "456"}, "test-tile")
        (True, {}, "Pharmacy", "456")
        >>> validate_account_id_parameters({}, "test-tile")
        (False, {"error": "Missing required parameter", ...}, None, None)
        >>> validate_account_id_parameters({"340bId": "123", "pharmacyId": "456"}, "test-tile")
        (False, {"error": "Invalid parameters", ...}, None, None)
    
    Validates: Requirements 10.1, 10.2
    """
    if not query_params:
        return False, {
            "error": MISSING_REQUIRED_PARAMETER,
            "message": EITHER_340BID_OR_PHARMACYID_REQUIRED,
            "tileName": tile_name
        }, None, None
    
    # Extract both parameters
    id_340b = query_params.get('340bId')
    pharmacy_id = query_params.get('pharmacyId')
    
    # Check if neither parameter is provided
    if not id_340b and not pharmacy_id:
        return False, {
            "error": MISSING_REQUIRED_PARAMETER,
            "message": EITHER_340BID_OR_PHARMACYID_REQUIRED,
            "tileName": tile_name
        }, None, None
    
    # Check if both parameters are provided
    if id_340b and pharmacy_id:
        return False, {
            "error": INVALID_PARAMS,
            "message": "Cannot specify both 340bId and pharmacyId. Provide exactly one.",
            "tileName": tile_name
        }, None, None
    
    # Validate 340bId if provided
    if id_340b:
        if not id_340b.strip():
            return False, {
                "error": INVALID_PARAMS,
                "message": "340bId parameter cannot be empty",
                "tileName": tile_name
            }, None, None
        return True, {}, "340B", id_340b.strip()
    
    # Validate pharmacyId (must be the one provided at this point)
    if not pharmacy_id.strip():
        return False, {
            "error": "Invalid parameters",
            "message": "pharmacyId parameter cannot be empty",
            "tileName": tile_name
        }, None, None
    return True, {}, "Pharmacy", pharmacy_id.strip()



def validate_segment_parameter(segment: str) -> tuple[bool, str]:
    """
    Validate that a segment parameter is one of the allowed values.
    
    Args:
        segment: The segment string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if the segment is valid, False otherwise
        - error_message: Empty string if valid, error description if invalid
    
    Examples:
        >>> validate_segment_parameter("340B")
        (True, "")
        >>> validate_segment_parameter("non-340B")
        (True, "")
        >>> validate_segment_parameter("invalid")
        (False, "Invalid segment value. Expected '340B' or 'non-340B'")
    """
    if not segment:
        return True, ""  # Empty/None segment is valid (optional parameter)
    
    allowed_segments = ["340B", "non-340B"]
    if segment not in allowed_segments:
        return False, f"Invalid segment value. Expected '340B' or 'non-340B', got '{segment}'"
    
    return True, ""



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



def validate_query_parameters(query_params: dict, tile_name: str) -> tuple[bool, dict]:
    """
    Validate common query parameters for tile requests.
    
    Args:
        query_params: Dictionary of query parameters to validate
        tile_name: Name of the tile for error reporting
    
    Returns:
        Tuple of (is_valid, error_response_or_empty_dict)
        - is_valid: True if all parameters are valid, False otherwise
        - error_response_or_empty_dict: Error response dict if invalid, empty dict if valid
    
    Validates:
        - from: ISO 8601 date format (YYYY-MM-DD)
        - to: ISO 8601 date format (YYYY-MM-DD)
        - segment: "340B" or "non-340B"
        - limit: Positive integer
        - region: Non-empty string
    """
    if not query_params:
        return True, {}
    
    # Validate date parameters ('from' and 'to')
    for param_name in ('from', 'to'):
        is_valid, error_resp = validate_optional_param(
            query_params, param_name, validate_date_format, "Invalid date format", tile_name
        )
        if not is_valid:
            return False, error_resp
    
    # Validate 'segment' parameter
    is_valid, error_resp = validate_optional_param(
        query_params, 'segment', validate_segment_parameter, "Invalid segment value", tile_name
    )
    if not is_valid:
        return False, error_resp
    
    # Validate 'limit' parameter
    is_valid, error_resp = validate_optional_param(
        query_params, 'limit', validate_limit_parameter, "Invalid limit parameter", tile_name
    )
    if not is_valid:
        return False, error_resp
    
    # Validate 'region' parameter (if present, should be non-empty string)
    region = query_params.get('region')
    if region is not None and not region.strip():
        return False, create_error_response(
            "Invalid region parameter",
            "Region parameter cannot be empty",
            tile_name
        )

    time_period = query_params.get('time-period')
    valid_time_periods = ["quarterly", "monthly", "half-yearly", "yearly"]
    if time_period and time_period not in valid_time_periods:
        return False, create_error_response(
            INVALID_TIME_PERIOD,
            f"'time-period' parameter must be one of {valid_time_periods} but got {time_period}",
            tile_name
        )

    return True, {}
