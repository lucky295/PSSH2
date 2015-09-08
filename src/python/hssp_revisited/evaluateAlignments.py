# new version of pythonscript_refactored using hhlib tools to process the structure file
import os, sys
import errno
import gzip
import csv
import subprocess
import logging
import time
import ConfigParser

defaultConfig = """
[pssh2Config]
pssh2_cache="/mnt/project/psshcache/result_cache_2014/"
HHLIB="/usr/share/hhsuite/"
pdbhhrfile='query.uniprot20.pdb.full.hhr'
seqfile='query.fasta'
"""


#default paths
hhMakeModelScript = '/scripts/hhmakemodel.pl'
renumberScript = 'renumberpdb.pl'
bestPdbScript = 'find_best_pdb_for_seqres_md5'
maxclScript = '/mnt/project/aliqeval/maxcluster'

#dparam = '/mnt/project/aliqeval/HSSP_revisited/fake_pdb_dir/'
#md5mapdir = '/mnt/project/pssh/pssh2_project/data/pdb_derived/pdb_redundant_chains-md5-seq-mapping'
#mayadir = '/mnt/home/andrea/software/mayachemtools/bin/ExtractFromPDBFiles.pl'
modeldir = '/mnt/project/psshcache/models'

cleanup = True 
maxTemplate = 5

def add_section_header(properties_file, header_name):
	"""we want to use the bash style config for pypthon, but
	ConfigParser requires at least one section header in a properties file and
	our bash config file doesn't have one, so add a header to it on the fly.
	"""
	yield '[{}]\n'.format(header_name)
	for line in properties_file:
		yield line

def process_hhr(path, workPath, pdbhhrfile):
	""" work out how many models we want to create, so we have to unzip the hhr file and count"""
	
	# read the hhr file in its orignial location
	hhrgzfile = gzip.open(path, 'rb')
	s = hhrgzfile.read()	
	
	# check whether we can write to our desired output directory
	try:
		os.makedirs(workPath)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise
			
	# write an unzipped verion to our work directory
	open(workPath+'/'+pdbhhrfile, 'w').write(s)
	parsefile = open(workPath+'/'+pdbhhrfile, 'rb')
	linelist = parsefile.readlines()
	
	# search from the end of the file until we reach the Number of the last alignment (in the alignment details)
	breaker = False
	i = -1
	while (breaker==False):
		i = i - 1
		if ("No " in linelist[i]) and (len(linelist[i])<10):
			breaker=True
		takenline = linelist[i]
	
	iterationcount = int(float(takenline.split(' ')[1]))
	print('-- '+str(iterationcount)+' matching proteins found!')
		
	hhrgzfile.close()
	parsefile.close()
	return linelist, iterationcount


def tune_seqfile(seqLines, chainCode, workPath):
	"""replace the sequence id in the input sequence file with the pdb code (inlcuding chain) 
	of the structure this sequence refers to"""
	
	outFileName = workPath+'/'+chainCode+'.fas'
	outFileHandle = open(outFileName, 'w')
	outFileHandle.write('>'+chainCode+'\n')	
	outFileHandle.write(seqLines)
	outFileHandle.close()
	return outFileName


def getModelFileName(workPath, pdbhhrfile, model):
	"""utility to make sure the naming is consistent"""
	return workPath+'/'+pdbhhrfile+'.'+str(model).zfill(5)+'.pdb'
	
def evaluateSingle(checksum):
	"""evaluate the alignment for a single md5 """"

	# find the data for this md5 
	# use find_cache_path to avoid having to get the config
	cachePath = pssh2_cache_path+checksum[0:2]+'/'+checksum[2:4]+'/'+checksum
	hhrPath = (cachePath+pdbhhrfile+'.gz')

	# check that we have the necessary input
	if not (os.path.isfile(hhrPath)):
		print('-- hhr does not exist, check md5 checksum!\n-- stopping execution...')
		return
	print('-- hhr file found. Calling hhmakemodel to create pdb model...') 

	# work out how many models we want to create, get unzipped data
	workPath = modeldir+checksum[0:2]+'/'+checksum[2:4]+'/'+checksum
	hhrdata = (process_hhr(hhrPath, checksum, workPath, pdbhhrfile))
	hhrlines, modelcount = hhrdata

	# hhmakemodel call, creating the models
	for model in range(1, modelcount+1):
		print('-- building model for protein '+str(model))
		#  we don't need -d any more since now hhsuite is properly set up at rostlab
		# subprocess.call([ hhPath+hhMakeModelScript, '-i '+workPath+'/'+pdbhhrfile, '-ts '+workPath+'/'+pdbhhrfile+'.'+str(model).zfill(5)+'.pdb', '-d '+dparam,'-m '+str(model)])
		modelFileWithPath = getModelFileName(workPath, pdbhhrfile, model)
		subprocess.call([ hhPath+hhMakeModelScript, '-i '+workPath+'/'+pdbhhrfile, '-ts '+ modelFileWithPath, '-m '+str(model)])

	# now create the things to compare against (pdb file(s) the sequence comes from)
	# make a fake pdb structure using the hhsuite tool
	# -> rename the sequence in the fasta sequence file to the pdbcode, then create the 'true' structure file

	# read the sequence file only once (we will produce fake sequence files with the pdb codes later)
	seqLines = open(cachePath+seqfile, 'r').readlines()
	seqLines.pop(0)

	# work out the pdb structures for this md5 sum
	p = subprocess.Popen([bestPdbScript, '-m ', checksum , '-n', maxTemplate], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = p.communicate()
	pdbChainCodes = out.strip().split(';') # normalize the results from grepping

	# iterate over all chains we found and prepare files to compare agains
	for chain in pdbChainCodes:
		pdbseqfile = tune_seqfile(seqLines, chain, workPath)
		pdbstrucfile = workPath+chain+'.pdb'
		subprocess.call([ renumberScript, pdbseqfile, '-o', pdbstrucfile])

	# iterate over all models and  do the comparison (maxcluster)
	print('-- performing maxcluster comparison')
	for model in range(1, modelcount+1): 

		for chain in pdbChainCodes:
			
			print('-- maxCluster\'d chain '+chain+ ' with model no. '+str(model))
			modelFileWithPath = getModelFileName(workPath, pdbhhrfile, model)
			p = subprocess.Popen([maxclScript, '-gdt', '4', '-e', pdbCode+'Chain'+chain+'CAlphas.pdb', '-p', modelFileWithPath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			out, err = p.communicate()
			

		with open('maxclres.log') as g:
			lines = g.readlines()

		#we have the chain letter currently available in the iteration, so we will just iterate over the result here
		print('-- we got '+str(len(lines))+' lines')
		for lineNo in range(0, len(lines)):
			if '== results for Chain '+chain+' compared to model' in lines[lineNo]:
				brk = False
				it = 0
				while brk == False:
					it = it+1
					if 'GDT=' in lines[lineNo+it]:
						brk = True
						gdt = lines[lineNo+it].replace('GDT=','').strip()
				
				rmsd = 0.000
				tm = 0.000
				if 'GDT= ' not in lines[lineNo+1]:
					rmsd = lines[lineNo+1][26:31]
					tm = lines[lineNo+1][74:-2]
				
				resultArray[h].append((int((lines[lineNo].split(' ')[8])[:-2]), gdt, tm, rmsd))
		h = h +1

		
			
	#create csvfile and writer object
	csvfile = open(csvfilename+'.csv', 'w')
	csvWriter = csv.writer(csvfile, delimiter=',')
	csvWriter.writerow(['md5 checksum', 'Hit code', 'model number', 'avg. GDT', 'avg. TM', 'avg. RMSD', 'Prob.', 'E-value', 'P-value', 'HH score', 'Columns', 'Query HMM', 'Template', 'HMM'])
	
	
	for i in range (modelcount): #iterating over the resultArray for every model
		print(str(i)+' of modelcount = '+str(modelcount))
		avgGDT =0.000
		avgTM = 0.000
		avgRMSD = 0.000
		chainCount = 0
		for j in range(len(pdbChainCodes)): #iterating for every chain
			#print('length of pdbChainCodes = '+str(len(pdbChainCodes)))
			#print('resArr ji1: '+str(resultArray[j][i][1]) + ' / resArr ji3: '+str(resultArray[j][i][3]))
			if not float(resultArray[j][i][1])+float(resultArray[j][i][3])==0.000:
				chainCount += 1
				avgGDT += float(resultArray[j][i][1])
				avgTM += float(resultArray[j][i][2])
				avgRMSD += float(resultArray[j][i][3])
		blitsParseLine = hhrlines[9+i][36:]
		blitsParseLine = blitsParseLine.replace('(',' ')
		blitsParseLine = blitsParseLine.replace(')',' ')
		while '  ' in blitsParseLine:
			blitsParseLine = blitsParseLine.replace('  ', ' ')
		blitsParseLine = blitsParseLine.split(' ')
		#blitsParseLine values: 0 = 
		if avgGDT + avgRMSD == 0.000:
			csvWriter.writerow([checksum, hhrlines[9+i][4:10], str(i+1), 'n/a', 'n/a', 'n/a', blitsParseLine[0], blitsParseLine[1], blitsParseLine[2], blitsParseLine[3],  blitsParseLine[5], blitsParseLine[6], blitsParseLine[7], blitsParseLine[8]])
		else:
			csvWriter.writerow([checksum, hhrlines[9+i][4:10], str(i+1), str(avgGDT/float(chainCount)), str(avgTM/float(chainCount)), str(avgRMSD/float(chainCount)), blitsParseLine[0], blitsParseLine[1], blitsParseLine[2], blitsParseLine[3], blitsParseLine[5], blitsParseLine[6], blitsParseLine[7], blitsParseLine[8]])
	
	csvfile.close()
		

#clean up everything

	if cleanup == True:
		print('-- cleanup in 3 seconds...')
		time.sleep(3)
		print('-- deleting '+pdbhhrfile)
		subprocess.call(['rm', workPath+'/'+pdbhhrfile])
		
		print('-- deleting '+pdbhhrfile[:-4]+'.*.pdb')
		for z in range(1, modelcount+1):
			subprocess.call(['rm', '-f', workPath+'/'+pdbhhrfile[:-3]+str(z)+'.pdb'])
				
		print('-- deleting maxclres.log')
		subprocess.call(['rm', 'maxclres.log'])


	
	
	
def main(argv):
	""" here we initiate the real work"""
	# get config info
	config = ConfigParser.RawConfigParser()
	config.readfp(io.BytesIO(defaultConfig))
	confPath = os.getenv('conf_file', '/etc/pssh2.conf')
	confFileHandle = open(confPath, encoding="utf_8")	
	config.readfp(add_section_header(confFileHandle, 'pssh2Config'))
	pssh2_cache_path = config.get('pssh2Config', 'pssh2_cache')
	hhPath = config.get('pssh2Config', 'HHLIB')
	pdbhhrfile = config.get('pssh2Config', 'pdbhhrfile')
	pdba3mfile = config.get('pssh2Config', 'pdba3mfile')

	# parse command line arguments	
	parser = argparse.ArgumentParser()
	parser.add_argument("-o", "--out", help="name of output file (csv format)")
	parser.add_argument("-m", "--md5", help="md5 sum of sequence to process")
# later add option for different formats
	parser.set_defaults(format=csv)
	args = parser.parse_args()
	csvfilename = args.out
	checksum = args.md5
	evaluateSingle(checksum)
	


if '__name__' == '__main__':
 	main(sys.argv[1:])	




"""
todo:
- automate md5 checksum input (list)
"""
