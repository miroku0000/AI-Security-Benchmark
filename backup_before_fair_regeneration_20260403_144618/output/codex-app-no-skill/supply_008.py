from setuptools import setup, find_packages

setup(
    name="your-package",
    version="0.1.0",
    description="A Python package",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        # Add pinned runtime dependencies here, for example:
        # "requests>=2.32.0,<3",
    ],
)