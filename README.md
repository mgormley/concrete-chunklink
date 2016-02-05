Wrapper of the chunklink.pl script used by CoNLL-2000 for use on
Concrete Communications.

The chunklink.pl script was written by Sabine Buchholz with
modifications by Yuval Krymolowski.  The original script is available
along with a README describing its use.

* http://ilk.uvt.nl/team/sabine/chunklink/chunklink_2-2-2000_for_conll.pl
* http://ilk.uvt.nl/team/sabine/chunklink/README.html

This wrapper was written in order to apply the chunking rules to parse
trees annotated on Concrete data. For more information about Concrete
see the Getting Started docs.

* http://hltcoe.github.io/

# Requirements

This library requires Python 2.7.x and concrete-python 4.3.x or 4.4.x.
To install concrete-python, use pip as below or see
https://github.com/hltcoe/concrete-python for alternate installation
instructions.

    pip install 'concrete>=4.4.0<4.8.0'

# Running the add_chunks.py script

To run the add_chunks.py script you can either pass in two file paths
or two directory paths.

    python concrete_chunklink/add_chunks.py [--chunklink <path/to/chunklink.pl>] <input path> <output path>

If using directories, they must both exists. If using two files, the
input file must exist and the output file will be created or
overwritten.

The script is just a wrapper around a modified version of the
chunklink which reads parses from STDIN. The script
'chunklink_2-2-2000_for_conll.pl' is found in the scripts/
directory. This perl script was created for the CoNLL-2000 shared task
to convert the PTB to chunks. If you are running add_chunks.py without
specifying the path to the chunklink script it will look in the './'
and then './scripts/' to try to find it before failing.

# Installation

For most uses cases, there is no need to install. However, in case you
want to use this library as a module, you can run the following:

    python setup.py install

Doing so will also add the entry point 'add_chunks' to your PATH.
