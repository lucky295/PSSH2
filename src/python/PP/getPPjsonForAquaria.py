#!/usr/bin/python

#import requests
import re
import json
import time
import sys, os, argparse
from DatabaseTools import SequenceStructureDatabase


# preprequisite for this import to work on local Mac:
# set up tunnel:
# ssh -L 3307:192.168.1.47:3306 andrea@rostlab
# have local config file


def main(argv):

	parser = argparse.ArgumentParser()
	parser.add_argument("-s" "--seq", help="fasta sequence to process")
	parser.add_argument("-u", "--uniprotAcc", help="uniprot Accession number of sequence to process")
	parser.add_argument("-m", "--md5", help="md5 sum of sequence to process")
	parser.add_argument("-d", "--details", help="flag to specify whether to give details or just a summary", action='store_true')
	parser.set_defaults(feature=False)
	args = parser.parse_args()

	sequence = ''
	uniprotAcc = ''
	md5 = ''
	mysqlClause = ''
	fastaString = ''
	name = ''
	if (args.seq):
		name = 'usrSequence_'
		timestamp = int(100*time.time())
		name += str(timestamp) 
		sequence = args.seq
		fastaString = ">" + name + " \n"
		fastaString += sequence + "\n"
	elif (args.uniprotAcc):
		uniprotAcc = args.uniprotAcc
		sequenceHandler = SequenceStructureDatabase.SequenceHandler()
		fastaString = sequenceHandler.getFastaSequenceByAccession(uniprotAcc)
		name = uniprotAcc
	elif (args.md5):
		md5 = args.md5
		sequenceHandler = SequenceStructureDatabase.SequenceHandler()
		fastaString = sequenceHandler.getFastaSequenceByMd5(md5)
		name = md5
	else:
		sys.exit(2)

	details = False
	if (args.details):
		details = True
	
	# if we got a sequence really, then retrieve PP result location
	predictionPath = ''
	if (fastaString):
		predictionPath = queryPP(name, fastaString)
	
	# if we got a PP result location, start parsing
	if (predictionPath):
#		isis_json = parse_isis(predictionPath)
#		someNA_json = parse_someNA(predictionPath)
		PHD_json = parse_PHD(predictionPath)
		# ...
	
def queryPP(name, fastaString):
	"""write fasta sequence to a file 
		call ppc_fetch for the file
		return the directory the predictions are stored in"""
	# TODO


def parse_isis(predictionPath):
	# TODO
	
def parse_someNA(predictionPath):
	# TODO
	
	
	
# def parsePHD(phdText):
#     #extract the PHD prediction as a single string
#     rexp = re.compile('PHD htm \|[\sH]*\|')
#     l1 = rexp.findall(phdText)
#     #iterate over all entries in list and remove unwanted characters
#     l2 = l1;
#     for i,el in enumerate(l1):
#         l2[i] = el[10:-1]
#     l2joined = "".join(l2)
#     return "".join(l2joined)
# 
# def getRange(phdStr):
#     #get position ranges for which a tm was predicted
#     rexp = re.compile('[H]+')
#     return [(m.start(0), m.end(0)) for m in rexp.finditer(phdStr)]
# 
# # author: David Scholz, 2015, davidmscholz@gmx.de
# # this script requires the python simplejson package
# # usage:
# # call this script from commandline with two arguments
# # 1: full path to the input file '...'query.phdPred'
# # 2: desired output folder for phdPred.json
# 
# inputDir = sys.argv[1]
# outputDir = sys.argv[2]
# phdFile = open(inputDir+'query.phdPred','r')
# phdText = phdFile.read()
# phdStr = parsePHD(phdText)
# rangeList = getRange(phdStr)
# 
# obj = {'Transmembrane regions (Prediction by PHDhtm)':{'Features':\
#       [{'Name':'PHDhtm','Residues':rangeList}]}}
# JSONstr = json.dumps(obj)
# outFile = open(outputDir+'PHDhtm.json', 'w')
# outFile.write(JSONstr)
# outFile.close()