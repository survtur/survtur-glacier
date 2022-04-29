import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setuptools.setup(
    name="survtur-glacier",
    version="2022.4a9",
    author="Alexander Chzhen",
    author_email="survtur@ya.ru",
    description="GUI to work with AWS Glacier (compatible with FastGlacier for Windows)",
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
