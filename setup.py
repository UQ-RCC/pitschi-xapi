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
            "fastapi==0.74.1",
            "uvicorn==0.16.0",
            "greenlet==1.1.2",
            "pydantic==1.9.0",
            "sqlalchemy==1.4.31",
            "sqlalchemy_json==0.4.0",
            "psycopg2-binary==2.8.6",
            "requests==2.25.1",
            "fastapi-utils==0.2.1",
            "pytz==2022.1",
            "requests-toolbelt==0.9.1",
            "jinja2==3.0.3",
            "python-keycloak-client==0.2.3",
            "cryptography==37.0.4"
    ]
)
