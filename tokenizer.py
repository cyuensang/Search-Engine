# Project 3

import sys
import re
from collections import defaultdict
from string import punctuation, whitespace
import time # used for measuring execution time
import traceback

# consts
PUNCTUATION_WHITESPACE = whitespace + punctuation
DELIMITERS = re.compile(r"[^a-zA-Z0-9]+") # pattern to match non-alphanumeric characters only
CHUNK_SIZE = 1024

# functions

def addTokens(wordFreqDict, line, prev=""):
	punctStripLine = DELIMITERS.sub(" ", prev + line) # replace all delimiters w/ spaces
	punctStripLine = punctStripLine.lstrip(PUNCTUATION_WHITESPACE)
	lineSplit = punctStripLine.split(" ")
	
	for word in lineSplit[:-1]:
		wordFreqDict[word.lower()] += 1

	# handle case of last token being cut off in the middle
	newPrev = ""
	lastToken = lineSplit[-1].strip(PUNCTUATION_WHITESPACE)
	if len(lastToken) > 0:
		newPrev = lastToken
	return newPrev

def processWordFreq(fileName):
	wordFreqDict = defaultdict(int) # maps tokens to frequency of each token in filename
	try:
		with open(fileName, 'r', encoding="utf8") as f: # add arg: encoding="utf8" to open function to handle UTF-8
			prev = ""
			while True:
				chunk = f.read(CHUNK_SIZE) # process file in chunks of 1024 characters
				if not chunk:
					prev = prev.strip(PUNCTUATION_WHITESPACE) # handle case where last token was too long to fit within CHUNK_SIZE
					if len(prev) > 0:
						wordFreqDict[prev.lower()] += 1
					break
				prev = addTokens(wordFreqDict, chunk, prev) # to handle if last token was cut off in the middle
	except FileNotFoundError:
		print("Error: File \'{}\' was not found.".format(fileName))
		traceback.print_exc()
		return None
	except UnicodeDecodeError:
		print("Error: file contains unicode characters that couldn't be processed")
		traceback.print_exc()
		return None
	except:
		print("Error while processing file \'{}\'".format(fileName))
		traceback.print_exc()
		return None
	

	return wordFreqDict

def printWordFreq(wordFreqDict):
	if wordFreqDict == None or len(wordFreqDict) == 0:
		print("No words in dict")
		return
	sortedWordFreq = sorted(sorted(wordFreqDict.items(), key=lambda pair: pair[0]), key=lambda pair: pair[1], reverse=True)
	for k, v in sortedWordFreq:
		print("{} - {}".format(k.encode('ascii', 'replace').decode('ascii'), v))
		# encode as ascii bytes to handle Unicode Characters
		# .decode to suppress byte b' prefix

if __name__ == "__main__":
	# Arguments
	# 0 - script name
	# 1 - file to get word frequencies from
	if len(sys.argv) >= 2:
		start = time.time()
		wordFreqDict = processWordFreq(sys.argv[1])
		if (wordFreqDict != None):
			printWordFreq(wordFreqDict)
			end = time.time()
			print("{} seconds taken.".format(end - start))
	else:
		print("Error: No file name provided")

