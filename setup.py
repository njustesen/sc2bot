from setuptools import setup, find_packages

setup(name='sc2bot',
      version="0.0.1",
      include_package_data=True,
      install_requires=[
          'numpy',
          'sc2',
          'sklearn'
      ],
      packages=find_packages()
)