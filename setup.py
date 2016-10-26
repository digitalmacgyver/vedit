from setuptools import setup

def readme():
    with open( 'README.rst' ) as f:
        return f.read()

setup( name='vedit',
       version='0.0.1',
       description='Library for editing video by wrapping ffmpeg.',
       long_description=readme(),
       url='https://github.com/digitalmacgyver/vedit',
       author='Matthew Hayward',
       author_email='mjhayward@gmail.com',
       license='MIT',
       packages=['vedit'],
       install_requires=['future'],
       classifiers=[
           'Development Status :: 4 - Beta',
           'Programming Language :: Python',
           'Programming Language :: Python :: 2',
           'Programming Language :: Python :: 2.7',
           'Programming Language :: Python :: 3',
           'Environment :: Console',
           'Intended Audience :: Developers',
           'License :: OSI Approved :: MIT License',
           'Topic :: Multimedia :: Video',
           'Operating System :: POSIX',
           'Operating System :: MacOS',
           'Operating System :: Microsoft :: Windows',
           'Operating System :: POSIX :: Linux',
           'Topic :: Multimedia :: Graphics :: Editors',
           'Topic :: Multimedia :: Graphics',
           'Topic :: Multimedia',
           'Topic :: Multimedia :: Sound/Audio :: Mixers',
           'Topic :: Multimedia :: Video :: Conversion',
       ],
       keywords='video ffmpeg',
       include_package_data=True,
       zip_safe=False )
