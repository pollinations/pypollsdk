from setuptools import find_packages, setup

setup(
    name="pypollsdk",
    version=0.1,
    description="Description here",
    license="Apache 2.0",
    packages=find_packages(),
    package_data={},
    scripts=[],
    install_requires=[
        "supabase==0.5.8",
        "python-dotenv==0.20.0",
        "pytest==7.1.2",
        "wget==3.2",
        "httpx==0.21.3",
    ],
    extras_require={
        "test": ["pytest", "pylint!=2.5.0", "black", "mypy", "flake8", "pytest-cov"],
    },
    entry_points={
        "console_scripts": [],
    },
    classifiers=[],
    tests_require=["pytest"],
    setup_requires=["pytest-runner"],
    keywords="",
)
