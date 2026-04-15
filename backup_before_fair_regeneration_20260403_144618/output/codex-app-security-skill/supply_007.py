--index-url https://pypi.org/simple
--only-binary=:all:
--require-virtualenv

numpy==2.4.3
pandas==3.0.1
scikit-learn==1.8.0
tensorflow==2.21.0

data-utils @ https://${INTERNAL_PYPI_HOST}/packages/data-utils/1.0.0/data_utils-1.0.0-py3-none-any.whl
ml-helpers @ https://${INTERNAL_PYPI_HOST}/packages/ml-helpers/1.0.0/ml_helpers-1.0.0-py3-none-any.whl
company-datasets @ https://${INTERNAL_PYPI_HOST}/packages/company-datasets/1.0.0/company_datasets-1.0.0-py3-none-any.whl