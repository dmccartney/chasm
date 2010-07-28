#!/usr/bin/env python

from distutils.core import setup

setup(name='chasm',
      version='0.1',
      description='parts of subspace in python',
      author='Daniel McCartney / divine.216',
      author_email='div@aswz.org',
      url='http://bitbucket.org/dmccartney/chasm/',
      package_dir = {'' : 'src'},
      packages = ['subspace', 
                   'subspace.core',
                   'subspace.billing',
                    'subspace.billing.client',
                    'subspace.billing.server',
                   'subspace.game',
                    'subspace.game.client',
                    'subspace.game.server',
                    ]
     )