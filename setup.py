import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="k8s_service_resolver",
    version="0.1.1",
    author="Serhii Charykov",
    author_email="serhii.charykov@gmail.com",
    description="Domain name + port resolver for Kubernetes Services with TTL cache",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/moznuy/k8s_service_resolver",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires='>=3.6',
    install_requires=[
        'pycares>=3,<4',
    ]
)
