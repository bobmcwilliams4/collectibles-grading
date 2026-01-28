#!/usr/bin/env python3
"""
Collectibles Grading System - Setup Script
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path, 'r') as f:
        requirements = [
            line.strip() for line in f
            if line.strip() and not line.startswith('#')
        ]

setup(
    name="collectibles-grading",
    version="1.0.0",
    author="ECHO_PRIME",
    description="AI-Powered Comic Book Grading System with Multi-Model Consensus",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/echo-prime/collectibles-grading",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-asyncio>=0.23.3",
            "pytest-cov>=4.1.0",
            "black>=24.1.0",
            "isort>=5.13.2",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
        "gpu": [
            "torch>=2.1.0+cu121",
            "torchvision>=0.16.0+cu121",
        ],
    },
    entry_points={
        "console_scripts": [
            "grading-server=run_server:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Image Recognition",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords=[
        "comic-grading",
        "cgc",
        "ai-grading",
        "collectibles",
        "computer-vision",
        "image-analysis"
    ],
    include_package_data=True,
    package_data={
        "": [
            "config/*.json",
            "static_export/templates/*.html",
        ],
    },
)
