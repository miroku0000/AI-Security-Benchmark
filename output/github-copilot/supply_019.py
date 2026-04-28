I found an old packaging file under `deprecated/`; I’m checking it for conventions and then I’ll add the production dependency definition at the repo root.

I’m writing a root `requirements.txt` that keeps the private index as the primary source and falls back to public PyPI for open-source dependencies.

`apply_patch` couldn’t create the file here, so I’m falling back to a direct file write and then checking the final content.

--index-url ${COMPANY_PYPI_URL}
--extra-index-url https://pypi.org/simple

company-analytics
company-ml-models
pandas
numpy
requests