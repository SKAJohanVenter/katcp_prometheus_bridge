from setuptools import setup, find_packages

tests_require = ['asynctest', 'pytest', 'pytest-cov', 'pytest-codestyle', 'pytest-mypy']

setup(
    name='katcp_prometheus_bridge',
    version=0.1,
    packages=find_packages(),
    package_data={'katcp_prometheus_bridge': ['py.typed']},
    author='Johan Venter',
    author_email='a.johan.venter@gmail.com',
    description=('Expose katcp sensors on a /metrics endpoint to '
                 'be consumed by Prometheus'),
    url='',
    license='BSD',
    platforms=['OS Independent'],
    keywords='katcp prometheus monitoring',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        'Operating System :: OS Independent',
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Monitoring",
    ],
    setup_requires=['pytest-runner', ],
    tests_require=tests_require,
    install_requires=['aiokatcp', 'prometheus_client', 'prometheus_async', 'aiohttp'],
    extras_require={'test': tests_require},
    python_requires='>=3.7',
    zip_safe=False
)
