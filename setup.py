from setuptools import setup, find_packages

setup(
    name='table_extraction_tools',
    version='0.1.0',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # List your package dependencies here
        # e.g., 'requests', 'numpy'
    ],
)
