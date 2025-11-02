"""
Setup configuration for wallclub_core package.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="wallclub_core",
    version="1.0.0",
    author="WallClub Team",
    author_email="tech@wallclub.com.br",
    description="Core shared components for WallClub ecosystem",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wallclub/wallclub_core",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    include_package_data=True,
    zip_safe=False,
)
