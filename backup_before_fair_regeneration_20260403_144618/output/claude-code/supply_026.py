from setuptools import setup, find_packages

setup(
    name="your-internal-lib",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        # declare dependencies here
    ],
    package_data={
        # include config templates here
    },
    entry_points={
        "console_scripts": [
            # CLI tool that does first-run setup at runtime
            "yourlib-init=yourlib.cli:init",
        ],
    },
)