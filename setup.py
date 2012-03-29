from setuptools import setup, find_packages

description="""
Ligthweight connection pooler for PostgreSQL.
"""

long_description = """
* **Documentation**: TODO
* **Project page**: TODO
"""


setup(
    name="pgbouncer-ng",
    version=':versiontools:pgbouncerlib:',
    url='https://github.com/niwibe/pgbouncer-ng',
    license='BSD',
    platforms=['OS Independent'],
    description = description.strip(),
    long_description = long_description.strip(),
    author = 'Andrei Antoukh',
    author_email = 'niwi@niwi.be',
    maintainer = 'Andrei Antoukh',
    maintainer_email = 'niwi@niwi.be',
    packages = ['pgbouncerlib'],
    include_package_data = True,
    scripts = ['pgbouncer-ng'],
    install_requires=[
        'distribute',
    ],
    setup_requires = [
        'versiontools >= 1.8',
    ],
    data_files=[
        ('/etc', ['pgbouncerng.ini']),
    ],
    zip_safe = False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Operating System :: POSIX',
    ]
)
