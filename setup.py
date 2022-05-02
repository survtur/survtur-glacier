import setuptools
import sys

sys.path.append("./src/")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

import survtur_glacier

setuptools.setup(
    name="survtur-glacier",
    version=survtur_glacier.__version__,
    author="Alexander Chzhen",
    author_email="survtur@ya.ru",
    description="GUI to work with AWS Glacier cold storage",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/survtur/survtur-glacier",
    # project_urls={},
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "boto3",
        "PyQt5"
    ],
    package_data={"": ['*.ini']},
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'survtur-glacier = survtur_glacier:start',
        ],
    },
)
