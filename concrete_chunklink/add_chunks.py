#!/usr/bin/env python

"""
"""

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
from concrete.util import concrete_uuid
from concrete.util import read_communication_from_file
from concrete.util import write_communication_to_file
from concrete.validate import validate_communication
from operator import attrgetter
import time


def add_chunks_to_dir(in_dir, out_dir, chunklink):
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
        add_chunks_to_file(in_file, out_file, chunklink)

def add_chunks_to_file(in_file, out_file, chunklink):
    '''Reads a Communication file, adds chunking information, and writes a new 
    Communication file containing the annotated version.'''
    # Deserialize
    comm = read_communication_from_file(in_file)
    
    # Add chunks
    num_chunked, num_sents = add_chunks_to_comm(comm, chunklink)
    logging.info("Chunked %d / %d = %f" % (num_chunked, num_sents,  float(num_chunked) / float(num_sents)))
    
    # Serialize
    write_communication_to_file(comm, out_file)                

def add_chunks_to_comm(comm, chunklink):
    '''Converts the first constituency tree 
    '''
    num_sents = 0
    num_chunked = 0
    try:
        for tokenization in get_tokenizations(comm):
            num_sents += 1 
            try:       
                if tokenization.parseList and len(tokenization.parseList) > 0:
                    parse = tokenization.parseList[0]            
                    # Convert concrete Parse to a PTB style parse string and write to a tmp file.
                    ptb_str = '( ' + penn_treebank_for_parse(parse) + ' )\n'
                    ptb_file = './wsj_0001.mrg'
                    with codecs.open(ptb_file, 'w', 'UTF-8') as ptb_out:
                        ptb_out.write(ptb_str)
                        
                    # Run the chunklink script and capture the output.
                    try:
                        chunk_str = subprocess.check_output(['perl', chunklink, ptb_file], stderr=subprocess.PIPE)            
                        logging.debug("Chunklink output:\n" + chunk_str)
                        chunk_tags = get_chunks(chunk_str)
                        logging.debug("Chunk tags: " + str(chunk_tags))
                        if len(chunk_tags) != len(tokenization.tokenList.tokenList):
                            raise Exception("ERROR: incorrect number of chunks. expected=%d actual=%d" % 
                                            (len(chunks), len(tokenization.tokenList.tokenList)))

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
                        
                    # Clean up the wsj file.
                    os.remove(ptb_file)
            except Exception as e:
                logging.exception("Chunking failed on tokenization")
    except Exception as e:
        logging.exception("Chunking failed on Communication")
    return num_chunked, num_sents

whitespace = re.compile(r"\s+")

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
            

# COPIED FROM concrete-python/scripts/concrete-inspect.py
def get_tokenizations(comm):
    """Returns a flat list of all Tokenization objects in a Communication

    Args:
        comm: A Concrete Communication

    Returns:
        A list of all Tokenization objects within the Communication
    """
    tokenizations = []

    if comm.sectionList:
        for section in comm.sectionList:
            if section.sentenceList:
                for sentence in section.sentenceList:
                    if sentence.tokenization:
                        tokenizations.append(sentence.tokenization)
    return tokenizations

# COPIED FROM concrete-python/scripts/concrete-inspect.py
def penn_treebank_for_parse(parse):
    """Get a Penn-Treebank style string for a Concrete Parse object

    Args:
        parse: A Concrete Parse object

    Returns:
        A string containing a Penn Treebank style parse tree representation
    """
    def _traverse_parse(nodes, node_index, indent=0):
        s = ""
        indent += len(nodes[node_index].tag) + 2
        if nodes[node_index].childList:
            s += "(%s " % nodes[node_index].tag
            for i, child_node_index in enumerate(nodes[node_index].childList):
                if i > 0:
                    s += "\n" + " "*indent
                s += _traverse_parse(nodes, child_node_index, indent)
            s += ")"
        else:
            s += nodes[node_index].tag
        return s

    sorted_nodes = sorted(parse.constituentList, key=attrgetter('id'))
    return _traverse_parse(sorted_nodes, 0)

if __name__ == "__main__":
    usage = "%prog [options] <input path> <output path>"
    logging.basicConfig(level=logging.INFO)

    parser = optparse.OptionParser(usage=usage)
    #parser.add_option('-i', '--in_path', help="Input file")
    #parser.add_option('-o', '--out_path', help="Output file")
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
    if os.path.isdir(in_path):
        add_chunks_to_dir(in_path, out_path, chunklink)
    else:
        add_chunks_to_file(in_path, out_path, chunklink)
