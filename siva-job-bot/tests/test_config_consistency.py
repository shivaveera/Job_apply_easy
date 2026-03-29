"""Tests for config consistency (Fixes 8, 9, 11)."""

import pytest
import yaml
from pathlib import Path


class TestExperienceConsistency:
    """Test that answer_profile and qa_overrides agree (Fix 8)."""

    def test_experience_years_match(self):
        profile_path = Path("config/answer_profile.yaml")
        overrides_path = Path("config/qa_overrides.yaml")

        if not profile_path.exists() or not overrides_path.exists():
            pytest.skip("Config files not found")

        with open(profile_path) as f:
            profile = yaml.safe_load(f)
        with open(overrides_path) as f:
            overrides = yaml.safe_load(f)

        profile_years = profile["experience_years"]["total"]
        override_years = overrides["overrides"].get("years of experience", "")

        assert profile_years == override_years, (
            f"Mismatch: answer_profile says {profile_years} years, "
            f"qa_overrides says {override_years} years"
        )

    def test_professional_experience_match(self):
        profile_path = Path("config/answer_profile.yaml")
        overrides_path = Path("config/qa_overrides.yaml")

        if not profile_path.exists() or not overrides_path.exists():
            pytest.skip("Config files not found")

        with open(profile_path) as f:
            profile = yaml.safe_load(f)
        with open(overrides_path) as f:
            overrides = yaml.safe_load(f)

        profile_years = profile["experience_years"]["total"]
        override_years = overrides["overrides"].get("years of professional experience", "")

        assert profile_years == override_years


class TestAnswerProfile:
    """Test answer_profile.yaml structure."""

    def test_profile_has_required_sections(self):
        path = Path("config/answer_profile.yaml")
        if not path.exists():
            pytest.skip("answer_profile.yaml not found")

        with open(path) as f:
            profile = yaml.safe_load(f)

        assert "work_authorization" in profile
        assert "experience_years" in profile
        assert "education" in profile
        assert "salary" in profile
        assert "availability" in profile
        assert "demographics" in profile
        assert "common_answers" in profile

    def test_profile_experience_years_are_strings(self):
        path = Path("config/answer_profile.yaml")
        if not path.exists():
            pytest.skip("answer_profile.yaml not found")

        with open(path) as f:
            profile = yaml.safe_load(f)

        for key, value in profile["experience_years"].items():
            assert isinstance(value, str), f"{key} should be a string, got {type(value)}"


class TestConfigYaml:
    """Test config.yaml structure (Fix 9)."""

    def test_config_has_required_sections(self):
        path = Path("config/config.yaml")
        if not path.exists():
            pytest.skip("config.yaml not found")

        with open(path) as f:
            config = yaml.safe_load(f)

        for section in ["personal", "search", "platforms", "ai", "safety", "database"]:
            assert section in config, f"Missing required section: {section}"

    def test_personal_has_required_fields(self):
        path = Path("config/config.yaml")
        if not path.exists():
            pytest.skip("config.yaml not found")

        with open(path) as f:
            config = yaml.safe_load(f)

        personal = config["personal"]
        required_fields = [
            "name", "first_name", "last_name", "email", "phone",
            "location", "resume_path",
        ]
        for field in required_fields:
            assert field in personal, f"Missing personal field: {field}"
