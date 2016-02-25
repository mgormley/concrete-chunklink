#!/usr/bin/env python
#
# Example usage:
#     python concrete_chunklink/add_chunks.py [--chunklink <path/to/chunklink.pl>] <input path> <output path>
#
'''
'''

import sys
import os
import optparse
import zipfile
import subprocess
import re
import logging
import codecs
import glob
import argparse
import json
from thrift import TSerialization
import concrete
import concrete.util
from concrete.inspect import get_tokenizations
from concrete.inspect import penn_treebank_for_parse
from concrete.util import concrete_uuid
from concrete.util import read_communication_from_file
from concrete.util import write_communication_to_file
from concrete.validate import validate_communication
from operator import attrgetter
import time

whitespace = re.compile(r"\s+")


def add_chunks_to_dir(in_dir, out_dir, chunklink, fail_on_error):
    '''Reads a directory containing Communications, adds chunking information, 
    and writes new files in the output directory containing the modified Communications.
    The directory is not searched recursively for files, only those at the top level are read.
    '''
    if not os.path.isdir(in_dir):
        raise Exception("ERROR: input path is not a directory: " + in_dir)
    if not os.path.isdir(out_dir):
        raise Exception("ERROR: output path is not a directory: " + out_dir)
    
    for in_file in glob.glob(os.path.join(in_dir, "*")):        
        logging.info("Processing: %s" % in_file)
        out_file = os.path.join(out_dir, os.path.basename(in_file))
        add_chunks_to_file(in_file, out_file, chunklink, fail_on_error)

        
def add_chunks_to_file(in_file, out_file, chunklink, fail_on_error):
    '''Reads a Communication file, adds chunking information, and writes a new 
    Communication file containing the annotated version.'''
    # Deserialize
    comm = read_communication_from_file(in_file)
    
    # Add chunks
    num_chunked, num_sents = add_chunks_to_comm(comm, chunklink, fail_on_error)
    logging.info("Chunked %d / %d = %f" % (num_chunked, num_sents,  float(num_chunked) / float(num_sents)))
    
    # Serialize
    write_communication_to_file(comm, out_file)                

    
def add_chunks_to_comm(comm, chunklink, fail_on_error):
    '''Converts the first constituency tree of each tokenization
    to chunks and adds them as a TokenTagging to the communication.
    
    comm - Communication to be annotated.
    chunklink - Path to the modified chunklink perl script.
    '''
    num_sents = 0
    num_chunked = 0
    try:
        for tokenization in get_tokenizations(comm):
            num_sents += 1 
            try:       
                if tokenization.parseList and len(tokenization.parseList) > 0:
                    parse = tokenization.parseList[0]            
                    # Convert concrete Parse to a PTB style parse string to use as stdin for chunklink.
                    ptb_str = '( ' + penn_treebank_for_parse(parse) + ' )\n'
                    ptb_str = ptb_str.encode('ascii', 'replace')
                    logging.debug("PTB string: " + ptb_str)
                    
                    # Run the chunklink script and capture the output.
                    try:
                        # We expect the chunklink script to be a modified version which can read a tree from stdin.
                        p = subprocess.Popen(['perl', chunklink], stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, stdin=subprocess.PIPE)

                        stdouterr = p.communicate(input=ptb_str)
                        chunk_str = stdouterr[0]
                        chunk_err = stdouterr[1]
                        logging.debug("Chunklink stdout:\n" + chunk_str)
                        logging.debug("Chunklink stderr:\n" + chunk_err)
                        chunk_tags = get_chunks(chunk_str)
                        logging.debug("Chunk tags: " + str(chunk_tags))
                        if len(chunk_tags) != len(tokenization.tokenList.tokenList):
                            raise Exception("ERROR: incorrect number of chunks. expected=%d actual=%d" % (len(tokenization.tokenList.tokenList), len(chunk_tags)))

                        metadata = concrete.AnnotationMetadata()
                        metadata.tool = "Chunklink Constituency Converter"
                        metadata.timestamp = long(time.time())
                        # Extract the chunks column and create a TokenTagging from it.
                        chunks = concrete.TokenTagging()
                        chunks.uuid = concrete_uuid.generate_UUID()
                        chunks.metadata = metadata                        
                        chunks.taggingType = "CHUNK"
                        chunks.taggedTokenList = []
                        for i, chunk in enumerate(chunk_tags):
                            tt = concrete.TaggedToken()
                            tt.tokenIndex = i
                            tt.tag = chunk
                            chunks.taggedTokenList.append(tt)
        
                        # Add chunks to the list of TokenTaggings.
                        if not tokenization.tokenTaggingList:
                            tokenization.tokenTaggingList = []
                        tokenization.tokenTaggingList.append(chunks)
                        num_chunked += 1
                    except subprocess.CalledProcessError as e:
                        logging.error("Chunklink failed on tree: %s" % (ptb_str))
                        if fail_on_error: raise e
            except Exception as e:
                logging.exception("Chunking failed on tokenization")
                if fail_on_error: raise e
    except Exception as e:
        logging.exception("Chunking failed on Communication")
        if fail_on_error: raise e
    return num_chunked, num_sents


def get_chunks(chunk_str):
    '''Gets the column of B-I-O tags denoting the chunks 
    from the output of the chunklink script.'''
    global whitespace
    chunks = []
    lines = chunk_str.split("\n")
    for line in lines:        
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        columns = whitespace.split(line)
        chunks.append(columns[3])
    return chunks


def main():
    usage = "%prog [options] <input path> <output path>"
    logging.basicConfig(level=logging.INFO)

    parser = optparse.OptionParser(usage=usage)
    parser.add_option( '--fail_on_error', action="store_true",  dest="fail_on_error", help="Whether to fail on errors.", default=True)
    parser.add_option( '--cont_on_error', action="store_false", dest="fail_on_error", help="Whether to continue on errors.")
    parser.add_option('-c', '--chunklink', help="Path to chunklink perl script")
    (options, args) = parser.parse_args(sys.argv)

    if len(args) != 3:
        parser.print_help()
        sys.exit(1)
    
    in_path = args[1]
    out_path = args[2]
    chunklink = options.chunklink
    if not chunklink:
        # Guess the location of the chunklink perl script
        chunklink = 'chunklink_2-2-2000_for_conll.pl'
        if not os.path.exists(chunklink):
            chunklink = 'scripts/chunklink_2-2-2000_for_conll.pl'
            if not os.path.exists(chunklink):
                raise Exception("Unable to find chunklink script. Specify with option --chunklink")

    if not os.path.exists(in_path):
        raise Exception("Input path doesn't exist: " + in_path)
    if not os.path.exists(chunklink):
        raise Exception("Chunklink script doesn't exist: " + chunklink)

    if options.fail_on_error:
        logging.debug("Exiting on errors.")
    else:
        logging.debug("Not exiting on errors.")
        
    if os.path.isdir(in_path):
        add_chunks_to_dir(in_path, out_path, chunklink, options.fail_on_error)
    else:
        add_chunks_to_file(in_path, out_path, chunklink, options.fail_on_error)

        
if __name__ == "__main__":
    main()
