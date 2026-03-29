"""Tests for ATS platform constructors accepting captcha_solver (Fix 2)."""

import pytest
from unittest.mock import MagicMock

from src.platforms.greenhouse import GreenhousePlatform
from src.platforms.lever import LeverPlatform
from src.platforms.workday import WorkdayPlatform
from src.platforms.indeed import IndeedPlatform
from src.platforms.smartrecruiters import SmartRecruitersPlatform
from src.platforms.icims import ICIMSPlatform
from src.platforms.taleo import TaleoPlatform
from src.platforms.adp import ADPPlatform
from src.platforms.ashby import AshbyPlatform
from src.platforms.universal import UniversalFormFiller


class TestATSPlatformCaptchaSolver:
    """Test that all ATS platforms accept captcha_solver parameter."""

    @pytest.fixture
    def browser(self):
        return MagicMock()

    @pytest.fixture
    def filler(self):
        return MagicMock()

    @pytest.fixture
    def solver(self):
        return MagicMock()

    def test_greenhouse_accepts_captcha_solver(self, browser, filler, solver):
        p = GreenhousePlatform(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver

    def test_lever_accepts_captcha_solver(self, browser, filler, solver):
        p = LeverPlatform(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver

    def test_workday_accepts_captcha_solver(self, browser, filler, solver):
        p = WorkdayPlatform(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver

    def test_indeed_accepts_captcha_solver(self, browser, filler, solver):
        p = IndeedPlatform(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver

    def test_smartrecruiters_accepts_captcha_solver(self, browser, filler, solver):
        p = SmartRecruitersPlatform(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver

    def test_icims_accepts_captcha_solver(self, browser, filler, solver):
        p = ICIMSPlatform(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver

    def test_taleo_accepts_captcha_solver(self, browser, filler, solver):
        p = TaleoPlatform(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver

    def test_adp_accepts_captcha_solver(self, browser, filler, solver):
        p = ADPPlatform(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver

    def test_ashby_accepts_captcha_solver(self, browser, filler, solver):
        p = AshbyPlatform(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver

    def test_universal_accepts_captcha_solver(self, browser, filler, solver):
        p = UniversalFormFiller(browser, filler, {}, captcha_solver=solver)
        assert p.captcha_solver is solver


class TestATSPlatformWithoutCaptcha:
    """Test that platforms work without captcha_solver (backward compat)."""

    @pytest.fixture
    def browser(self):
        return MagicMock()

    def test_greenhouse_without_captcha(self, browser):
        p = GreenhousePlatform(browser, None, {})
        assert p.captcha_solver is None

    def test_workday_without_captcha(self, browser):
        p = WorkdayPlatform(browser, None, {})
        assert p.captcha_solver is None

    def test_indeed_without_captcha(self, browser):
        p = IndeedPlatform(browser, None, {})
        assert p.captcha_solver is None
