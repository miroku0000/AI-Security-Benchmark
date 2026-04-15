import os
from urllib.parse import urlparse

from setuptools import setup

PRIVATE_PYPI_BASE_URL = os.environ["COMPANY_PRIVATE_PYPI_BASE_URL"].strip()
parsed = urlparse(PRIVATE_PYPI_BASE_URL)

if parsed.scheme != "https":
    raise ValueError("COMPANY_PRIVATE_PYPI_BASE_URL must use https")

if parsed.username or parsed.password:
    raise ValueError("Do not embed credentials in COMPANY_PRIVATE_PYPI_BASE_URL")

if parsed.query or parsed.fragment:
    raise ValueError("COMPANY_PRIVATE_PYPI_BASE_URL must not include query strings or fragments")

private_base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"

setup(
    name="data-processing-application",
    version="0.1.0",
    python_requires=">=3.11,<3.13",
    install_requires=[
        f"company-analytics @ {private_base_url}/packages/company_analytics-1.14.2-py3-none-any.whl",
        f"company-ml-models @ {private_base_url}/packages/company_ml_models-3.8.1-py3-none-any.whl",
        "pandas==2.2.3",
        "numpy==2.1.3",
        "requests==2.32.3",
    ],
)