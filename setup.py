"""
Setup script for Forensic-LLM
Install with: pip install -e .
Then you can run: forensic-llm
"""

from setuptools import setup, find_packages

setup(
    name="forensic-llm",
    version="1.0.0",
    description="A tool for scraping legal cases from Indian Kanoon and extracting evidence using AI",
    packages=find_packages(),
    py_modules=["forensic_llm_cli"],
    install_requires=[
        "rich>=13.0.0",
        "undetected-chromedriver",
        "beautifulsoup4",
        "selenium",
        "requests",
        "tqdm",
    ],
    entry_points={
        "console_scripts": [
            "forensic-llm=forensic_llm_cli:main",
        ],
    },
    python_requires=">=3.7",
)

