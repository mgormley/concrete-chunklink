Wrapper of the chunklink.pl script used by CoNLL-2000 for use on Concrete Communications.

# Dependencies

This library requires concrete-python with the 4.3 version of the
Thrift spec.

See https://gitlab.hltcoe.jhu.edu/concrete/concrete-python for
installation instructions.

# Installation

For most uses cases, there is no need to install. However, in case you
want to use this library as a module, you can run the following:

    python setup.py install

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
