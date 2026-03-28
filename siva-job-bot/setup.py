"""Setup configuration for siva-job-bot."""

from setuptools import find_packages, setup

setup(
    name="siva-job-bot",
    version="1.0.0",
    description="AI-powered automated job application bot using DeepSeek",
    author="Siva",
    python_requires=">=3.12",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=6.0",
        "openai>=1.30.0",
        "selenium>=4.15.0",
        "webdriver-manager>=4.0.0",
        "undetected-chromedriver>=3.5.0",
        "selenium-stealth>=1.0.6",
        "Levenshtein>=0.25.0",
        "fpdf2>=2.7.0",
    ],
    extras_require={
        "notifications": ["pyTelegramBotAPI>=4.14.0"],
        "dev": ["pytest>=7.0.0"],
    },
    entry_points={
        "console_scripts": [
            "siva-job-bot=run:main",
        ],
    },
)
