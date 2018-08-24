# Project 3
'''
Change the rootdir in the main to where are the html files
'''
import os
from pymongo import MongoClient
import tokenizer_html as tok
from pprint import pprint
from _collections import defaultdict
import json
from math import log10, sqrt

global rootdir
global jsonFile
global dbDir
#--------------------------------------------------------------------------------
#Directory to change:
#--------------------------------------------------------------------------------
#Directory of html files
rootDirToIndex = r"C:\Users\yschr\Desktop\CS121Project3"
#File path of the json file
jsonFile = r"C:\Users\yschr\Desktop\CS121Project3\bookkeeping.json"
#Directory of the Database
dbDir = r'C:\data'


class SearchEngine:
	
	# need to add more stop words in the future
	stopWords = {"is","are","were","the","this","that"}
	
	# Constructor
	def __init__(self):
		self.client = MongoClient()
		self.db = self.client['cs121']
		# collections
		self.URLIndex = self.db['URLIndex'] # {folder, file, url}
		self.docIndex = self.db['docIndex'] # {"docID", "term", "termDocFreq"}
		self.index = self.db['index'] # {"term", "postList"}
		
		self.totalDoc = 0
		
		'''
		------------------------------------------------------
		Run 1 time to build the database
		'''
		#print("init search engine")
		if "URLIndex" not in self.db.collection_names():
			self.processUrlFile(jsonFile)
		if "docIndex" not in self.db.collection_names():
			self.processFiles(rootDirToIndex)
		if "index" not in self.db.collection_names():
			self.buildIndex()
		#print("done processing files")

		if "index" in self.db.collection_names():
			self.totalDoc = self.countDocs()
	
	# BUILD INDEXES ---------------------------------------------------------------------------
	def processUrlFile(self, path):
		# processes the bookkeeping.json file in a way that is better than just importing directly to mongodb
		# adds to URLIndex {folder, file, url}
		with open(path) as jsonDataFile:
			data = json.load(jsonDataFile)
			bulk = self.db.URLIndex.initialize_unordered_bulk_op()
			for location, url in data.items():
				folderNum, fileNum = location.split('/')
				#print(folderNum + '|' + fileNum)
				bulk.insert({'folder': folderNum,
					'file': fileNum,
					'url': url})
			bulk.execute()
		
	def tokenizeFile(self, path):
		# tokenizes a webpage file
		# returns wordFreqDict
		t = tok.Tokenizer()
		return t.create_dictionary_from(path)
	
	def insertDocument(self, folderNum, fileNum, wordFreqDict):
		# inserts document into a collection
		record = dict()
		docID = folderNum+"|"+fileNum
		#digit = defaultdict(int)
		bulkIns = False
		bulkDoc = self.docIndex.initialize_unordered_bulk_op()
		
		# item[term, frequency]
		for item in wordFreqDict.items():
			# filter each terms
			if not (len(item[0]) == 1) and item[0] not in self.stopWords:
			#if not (item[0].isalpha() and len(item[0]) == 1) and item[0] not in self.stopWords:
				#if item[0].isdigit():
				#	digit["*digit"] += item[1]
				#else:	
				record = {"term": item[0], "freq": item[1]}
				bulkIns = True		
				bulkDoc.insert({"docID": docID, "term": record["term"], "termDocFreq": record["freq"]})
		'''
		if digit:
			bulkIns = True
			bulkDoc.insert({"docID": docID, "term": "*digit", "termDocFreq": digit["*digit"]})
		'''
		if(bulkIns):
			bulkDoc.execute()
	
	def processFiles(self, path):
		# Iterate over all folders and files in the path
		# adds all to docIndex {docId, term, termDocFreq}
		wordFreqDict = defaultdict(int)
		ignoreList = [".tsv", ".json"]
		for subdirs, dirs, files in os.walk(path):
			for file in files:
				if  not any(sub in file for sub in ignoreList):
					print("Process: " + os.path.join(subdirs, file))
					wordFreqDict = self.tokenizeFile(os.path.join(subdirs, file))
					self.insertDocument(subdirs.split('\\')[-1], file, wordFreqDict)

	def buildIndex(self):
		# build index table {"term", "postList"}
		indexDict = defaultdict(set)
		cursor = self.docIndex.find()
		bulkIndex = self.index.initialize_unordered_bulk_op()
		print("Building index")
		for doc in cursor:
			indexDict[doc["term"]].add(doc["docID"])
		
		for item in indexDict.items():
				bulkIndex.insert({"term": item[0], "postList": sorted(item[1])})
		
		bulkIndex.execute()
		print("Building index done")
	
	# PROCESS SEARCH QUERY ---------------------------------------------------------------------------
	def getAllTermDocList(self, terms):
		# get the postList of each term and return it in a dictionary as {"term": set(postList)}
		postDict= defaultdict(set)
		for term in terms:
			cursor = self.index.find_one({"term": term})
			if cursor:
				postDict[term] = set(cursor["postList"])
		return postDict

	def getUnion(self, postDict):
		# get all docID where a term occurs and return as a set
		postSet = set()
		for term, postList in postDict.items():
			for docID in postList:
				postSet.add(docID)
		return postSet
	
	def getWeightDict(self, terms, allDocID):
		# get the tf-idf weight of each term and save it in a dictionary as {"docID": {"term": int(termDocFreq)}}
		numDocsInCorpus = self.totalDoc
		weightDict = defaultdict(dict)
		
		for term in terms:
			tfCursor = self.docIndex.find({"term": term})
			dfDict = self.index.find_one({"term": term})
			if dfDict:
				docFreq = len(dfDict["postList"])
				for doc in tfCursor:
					if len(terms) > 1:
						weightDict[doc["docID"]].update({term: log10(1 + doc["termDocFreq"]) * log10(numDocsInCorpus / docFreq)})
					else:
						weightDict[doc["docID"]].update({term: log10(1 + doc["termDocFreq"])})

		return weightDict
	
	def getLengthDict(self, weightDict):
		# process the normalized length and save it in a dictionary as {"docID": float(length)}
		lenDict = defaultdict(float)
		for docID, termWeight in weightDict.items():
			total = 0
			for term, weight in termWeight.items():
				total += (weight * weight)
			lenDict[docID] = sqrt(total)
		return lenDict
	
	def getQueryWeightDict(self, allTermDocList, allDocID, terms):
		# process the tf-idf of the query and save it in a dictionary as {"term": float(tf-idf)}
		queryWeightDict = defaultdict(float)
		#total = len(allDocID)
		for term in terms:
			if term in allTermDocList:
				queryWeightDict[term] = log10(1 + terms.count(term)) # * log10(total/len(allTermDocList[term])) # this should evaluate to 1 anyways
		return queryWeightDict
	
	def getScoreDict(self, weightDict, queryWeightDict):
		# process the score of each docID and save it in a dictionary as {"docID": float(score)}
		scoreDict = defaultdict(float)
		for docID, termWeight in weightDict.items():
			for term, weight in termWeight.items():
				scoreDict[docID] += weight * queryWeightDict[term]
		return scoreDict

	def refineScoreDict(self, scoreDict, lenDict):
		for docID, score in scoreDict.items():
			scoreDict[docID] = score / lenDict[docID]
	
	def multiRanked(self, terms, top):
		# dictionary: {"term": set(postList)}
		allTermDocList = self.getAllTermDocList(terms)
		# set of all docID where a term occurs
		allDocID = self.getUnion(allTermDocList)
		# dictionary: {"docID": {"term": float(tf-idf)}}
		weightDict = self.getWeightDict(terms, allDocID)
		# dictionary: {"docID": float(length)}
		lenDict = self.getLengthDict(weightDict)
		# dictionary: {"term": float(tf-idf)}
		queryWeightDict = self.getQueryWeightDict(allTermDocList, allDocID, terms)
		# dictionary: {"docID": float(score)}
		scoreDict = self.getScoreDict(weightDict, queryWeightDict)
		self.refineScoreDict(scoreDict, lenDict)
		# DEBUG
		# for k in sorted(scoreDict.items(), key = lambda i: -i[1])[:top]:
		# 	print("{} -> {}".format(k[0], k[1]))
		return [k[0] for k in sorted(scoreDict.items(), key = lambda i: -i[1])[:top]]	
			
	def monoRanked(self, terms, top):
		term = terms[0]
		scoreDict = defaultdict(int)
		# dictionary: {"term": set(postList)}
		allTermDocList = self.getAllTermDocList(terms)
		# set of all docID where a term occurs
		allDocID = allTermDocList[term]
		# dictionary: {"docID": {"term": float(tf-idf)}}
		weightDict = self.getWeightDict(terms, allDocID)
		for docID, termTfIdf in weightDict.items():
			scoreDict[docID] = termTfIdf[term]
		# DEBUG
		# for k in sorted(scoreDict.items(), key = lambda i: -i[1])[:top]:
		# 	print("{} -> {}".format(k[0], k[1]))
		return [k[0] for k in sorted(scoreDict.items(), key = lambda i: -i[1])[:top]]
	
	def getURL(self, postList):
		print("Displaying top {} documents.".format(len(postList)))
		for docId in postList:
			folder, file = docId.split('|')
			filesFound = self.URLIndex.find_one({'folder': folder, 'file' : file})
			print("{} - {}".format(docId, filesFound['url']))
	
	def rankedQuery(self, string, top = 10):
		# show top result of query
		terms = string.split()
		# put the query to the correct format
		for i in range (len(terms)):
			'''
			if terms[i].isdigit():
				terms[i] = "*digit"
			'''
			terms[i] = terms[i].lower()
		
		if len(set(terms)) > 1:
			self.getURL(self.multiRanked(terms, top))
		else:
			self.getURL(self.monoRanked(terms, top))

	# PRINT/COUNT STATISTICS
	def printData(self, collection):
		# print the database
		cursor = collection.find()
		for doc in cursor:
			pprint(doc)

	def countDocs(self):
		cursor = self.index.find()
		allDocs = set()
		for dbDoc in cursor:
			for doc in dbDoc['postList']:
				allDocs.add(doc)
		return len(allDocs)

	def getTotalSize(self, path):
		total = 0
		for subdirs, dirs, files in os.walk(path):
			for file in files:
				total += os.path.getsize(os.path.join(subdirs, file))
		# convert in kilobytes
		return "%3.2f %s" % (total/1024, "KB")
		
	def printReport(self):
		print("-- Database Report --")
		print("Number of documents indexed:", self.totalDoc)
		print("Number of unique words indexed:", self.index.count())
		print("Total size:", self.getTotalSize(dbDir))
		
	
if __name__ == "__main__":	
	# remember to start server shell> 'mongod'
	se = SearchEngine()
	'''
	------------------------------------------------------
	Print collections
	'''
	#se.printData(se.URLIndex)
	#se.printData(se.index)
	#se.printData(se.docIndex)
	'''
	------------------------------------------------------
	Print the Database Report
	'''
	# se.printReport()
	#print('\n')
	
	print('Enter a search term: (ENTER to exit): ', end='')
	userInput = input().strip()
	while (userInput != ""):
		#se.searchOneTerm(userInput)
		se.rankedQuery(userInput, top=15)
		print('\nEnter a search term: (ENTER to exit): ', end='')
		userInput = input().strip()