from typing import Any, Dict, List, Tuple
from app.schemas.dataset import DataCleanRequest, DataCleanResponse


class CleaningService:
    """Business service responsible for cleaning, sanitizing, and normalizing datasets."""

    @staticmethod
    def sanitize_value(value: Any, strip_whitespace: bool = True) -> Any:
        """Sanitize a single scalar value by trimming or normalizing empty strings."""
        if isinstance(value, str):
            cleaned = value.strip() if strip_whitespace else value
            return None if cleaned == "" else cleaned
        return value

    @classmethod
    def clean_record(
        cls,
        record: Dict[str, Any],
        strip_whitespace: bool,
        impute_nulls: bool,
        replacements: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Clean a single dictionary record and count imputed fields."""
        cleaned_row: Dict[str, Any] = {}
        imputed_counts: Dict[str, int] = {}

        for key, value in record.items():
            sanitized = cls.sanitize_value(value, strip_whitespace)
            if sanitized is None and impute_nulls:
                if key in replacements:
                    sanitized = replacements[key]
                    imputed_counts[key] = imputed_counts.get(key, 0) + 1
            cleaned_row[key] = sanitized

        return cleaned_row, imputed_counts

    @classmethod
    def clean_dataset(cls, request: DataCleanRequest) -> DataCleanResponse:
        """Process an entire batch of dataset records according to cleaning specifications."""
        cleaned_list: List[Dict[str, Any]] = []
        aggregate_null_counts: Dict[str, int] = {}

        for row in request.records:
            cleaned_row, imputed = cls.clean_record(
                row,
                strip_whitespace=request.strip_whitespace,
                impute_nulls=request.impute_nulls,
                replacements=request.null_value_replacements,
            )
            cleaned_list.append(cleaned_row)
            for k, count in imputed.items():
                aggregate_null_counts[k] = aggregate_null_counts.get(k, 0) + count

        return DataCleanResponse(
            cleaned_records=cleaned_list,
            total_processed=len(cleaned_list),
            null_counts_imputed=aggregate_null_counts,
        )
