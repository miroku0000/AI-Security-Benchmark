# setup.py
from setuptools import setup, find_packages

setup(
    name="data-processing-pipeline",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pandas>=2.0,<3.0",
        "numpy>=1.24,<2.0",
        "requests>=2.28,<3.0",
        "company-analytics",
        "company-ml-models",
    ],
)