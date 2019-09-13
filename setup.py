from setuptools import setup

setup(name='esme',
      version='0.3',
      description='Evolutionary Scheduling Made Easy',
      classifiers=[
          'Development Status :: 1 - Planning',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6'
      ],
      url='http://github.com/rexvalkering/esme',
      author='Rex Valkering',
      author_email='rexvalkering@gmail.com',
      license='MIT',
      packages=['esme'],
      install_requires=['celery', 'deap', 'numpy', 'progressbar2', 'pyyaml', 'tabulate'],
      zip_safe=False)
