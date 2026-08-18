"""Tests for core.dependencies module."""

import pytest
from fastapi import HTTPException

import core.dependencies as core_dependencies


class TestValidateId:
    """Tests for validate_id function."""

    def test_valid_id(self):
        core_dependencies.validate_id(5, 0, "invalid")

    def test_invalid_id_equal_to_min(self):
        with pytest.raises(HTTPException) as exc_info:
            core_dependencies.validate_id(0, 0, "must be above 0")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "must be above 0"

    def test_invalid_id_below_min(self):
        with pytest.raises(HTTPException) as exc_info:
            core_dependencies.validate_id(-1, 0, "must be above 0")
        assert exc_info.value.status_code == 422


class TestValidateType:
    """Tests for validate_type function."""

    def test_valid_in_range(self):
        core_dependencies.validate_type(5, 1, 10, "invalid")

    def test_valid_at_min(self):
        core_dependencies.validate_type(1, 1, 10, "invalid")

    def test_valid_at_max(self):
        core_dependencies.validate_type(10, 1, 10, "invalid")

    def test_below_min(self):
        with pytest.raises(HTTPException) as exc_info:
            core_dependencies.validate_type(0, 1, 10, "out of range")
        assert exc_info.value.status_code == 422

    def test_above_max(self):
        with pytest.raises(HTTPException) as exc_info:
            core_dependencies.validate_type(11, 1, 10, "out of range")
        assert exc_info.value.status_code == 422


class TestValidatePaginationValues:
    """Tests for validate_pagination_values function."""

    def test_valid_values(self):
        core_dependencies.validate_pagination_values(1, 20)

    def test_page_number_zero(self):
        with pytest.raises(HTTPException) as exc_info:
            core_dependencies.validate_pagination_values(0, 20)
        assert exc_info.value.status_code == 422

    def test_num_records_zero(self):
        with pytest.raises(HTTPException) as exc_info:
            core_dependencies.validate_pagination_values(1, 0)
        assert exc_info.value.status_code == 422

    def test_page_number_negative(self):
        with pytest.raises(HTTPException) as exc_info:
            core_dependencies.validate_pagination_values(-1, 20)
        assert exc_info.value.status_code == 422


class TestValidatePaginationValuesOnQuery:
    """Tests for validate_pagination_values_on_query function."""

    def test_both_none(self):
        assert core_dependencies.validate_pagination_values_on_query() is None

    def test_valid_values(self):
        assert core_dependencies.validate_pagination_values_on_query(1, 20) is None

    def test_page_number_zero(self):
        with pytest.raises(HTTPException) as exc_info:
            core_dependencies.validate_pagination_values_on_query(0, 20)
        assert exc_info.value.status_code == 422

    def test_num_records_zero(self):
        with pytest.raises(HTTPException) as exc_info:
            core_dependencies.validate_pagination_values_on_query(1, 0)
        assert exc_info.value.status_code == 422
