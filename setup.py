import os
from setuptools import setup, find_packages

setup(
    name='pitschixapi',
    version='0.1',
    description='External api for pitschi',
    author='Hoang Anh Nguyen',
    author_email='uqhngu36@uq.edu.au',
    url='https://github.com/UQ-RCC/pitschi-xapi',
    packages=find_packages(exclude=["test*"]),
    # data_files=[
        # ('conf', ['conf/pitschi.conf'])
    # ],
    zip_safe=False,
    install_requires=[
            "fastapi==0.65.2",
            "uvicorn==0.12.2",
            "sqlalchemy==1.3.20",
            "sqlalchemy_json==0.4.0",
            "psycopg2-binary==2.8.6",
            "requests==2.25.1",
            "fastapi-utils==0.2.1",
            "pytz",
            "requests-toolbelt==0.9.1"
    ]
)
