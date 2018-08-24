import sys  # library for the command line
import re   # library for regular expression
from collections import defaultdict # library for default dictionary
import traceback

#pattern = re.compile('\W')
pattern = re.compile(r"[^</>a-zA-Z0-9]+") # matches non-alphanumeric chars and chars for tags
DELIMITERS = re.compile(r"[^a-zA-Z0-9]+") # pattern to match non-alphanumeric characters only
tagLeftPattern = re.compile("<")
tagRightPattern = re.compile(">")
tagMatch = re.compile("</?\w*>")
tagBounds = re.compile(r"[</>]")
'''
"<body>", "</body>", "<title>", "</title>", "<h1>", "</h1>", "<h2>", "</h2>", "<h3>", "</h3>", "<b>", "</b>",
"<strong>", "</strong>"
'''
importantTags = set(["title", "h1", "h2", "h3", "b", "strong"]) # does not include body
importantWordWeight = 9 # set to 9 not 10 so elements in important tags get a value of 1+9=10

class Tokenizer:
	def __init__(self):
		self.tagHierarchy = [] # form: ("opening tag name", defaultdict(int))
		# assumed to be in body tag unless otherwise stated
	
	def getCurrentTag(self):
		if len(self.tagHierarchy) == 0:
			return ("body", None)
		
		return self.tagHierarchy[len(self.tagHierarchy) - 1]

	def parse_from(self, filename):
		try:
			with open(filename, 'r', encoding="utf8") as f: # add arg: encoding="utf8" to open function to handle UTF-8
				for line in f:
				# create a list of string separated by anything that is not a-z & A-Z & 0-9.
					line = tagLeftPattern.sub(" <", line)
					line = tagRightPattern.sub("> ", line)
					for word in (pattern.split(line)):
					# filter out empty string because regex.split create empty string when multiple matches
					# are adjacent to one another, an empty string is inserted into the array.
						if word:
							yield word.lower()
		except FileNotFoundError:
			print("Error: File \'{}\' was not found.".format(filename))
			traceback.print_exc()
			return None
		except UnicodeDecodeError:
			print("Error: file contains unicode characters that couldn't be processed")
			traceback.print_exc()
			return None
		except:
			print("Error while processing file \'{}\'".format(filename))
			traceback.print_exc()
			return None				
					

	def create_dictionary_from(self, filename):
		str_dict = defaultdict(int)
		
		for word in self.parse_from(filename):
			# print(word)
			if tagMatch.match(word) != None: # match tags as long as you haven't reached the closing body tag
				if len(word) >= 2: # if not just punctuation
					isClosing = word[1] == "/"
					tag = tagBounds.sub("", word).strip()
					# print("tag: " + tag)
					currOpeningTag, wordsInCurrTag = self.getCurrentTag()
					if (isClosing):
						if tag == currOpeningTag and tag in importantTags: # found non-"body" valid closing tag
							# print("**CLOSING**: {}".format(tag))
							if (tag in importantTags): # give words in important tags 10 times the frequency
								for token, freq in wordsInCurrTag.items():
									str_dict[token] += freq * importantWordWeight
							self.tagHierarchy.pop()
					else:
						if (tag in importantTags): # since we prestart w/ body tag anyways
							self.tagHierarchy.append((tag, defaultdict(int)))
			else:
				word = DELIMITERS.sub(" ", word.strip("</>"))
				wordArr = word.split(" ")
				
				currOpeningTag, wordsInCurrTag = self.getCurrentTag()
				
				if (currOpeningTag == "body"):					
					for token in wordArr:
						if len(token) > 0:
							str_dict[token] += 1
				else:
					for token in wordArr:
						if len(token) > 0:
							wordsInCurrTag[token] += 1
							str_dict[token] += 1
			
		return str_dict


	def print_dictionary(self, d):
		# sorted first in decreasing order for the frequency (-i[1]) then in alphabetical order (i[0])
		print("n# of tokens:", len(d))
		for (k, v) in sorted(d.items(), key = (lambda i: (-i[1] ,i[0]))):
			print(k + " -", v)


if __name__ == '__main__':
	# Arguments
	# 0 - script name
	# 1 - file to get word frequencies from
	if len(sys.argv) >= 2:
		tok = Tokenizer()
		wordFreqDict = tok.create_dictionary_from(sys.argv[1])
		if (wordFreqDict != None):
			tok.print_dictionary(wordFreqDict)
	else:
		print("Error: No file name provided")