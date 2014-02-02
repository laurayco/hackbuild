import os, sys
from functools import partial
from os import listdir as ldir
from os.path import join as path

class FileSearch:
	environment_splitter = ';'#change to ':' on linux.
	def __init__(self,search_name=None):
		self.search_name=search_name
		self.constraints = []
	@property
	def environment_name(self):
	    if self.search_name:return self.search_name
	    return type(self).__name__
	@property
	def directories(self):
		search_dirs = os.path.expandvars(self.environment_name).split(self.environment_splitter)
		if len(search_dirs)==1 and search_dirs[0]==self.environment_name: search_dirs = []
		return [
			path(os.getcwd(),self.environment_name),
			os.getcwd(),
		] + search_dirs
	def files(self):
		for directory in self.directories:
			if not os.path.exists(directory):
				os.makedirs(directory)
			if os.path.isdir(directory):
				yield from filter(self.accept,map(partial(path,directory),ldir(directory)))
	def accept(self,filename):return all(f(filename) for f in self.constraints)

class DirectorySearch(FileSearch):#exclusively searches a single directory.
	def __init__(self,search_name=None,directory = os.getcwd()):
		self.directory = directory
		super().__init__(search_name)
	@property
	def directories(self): return [self.directory]

def extension_search(*extensions):
	def check_ext(ext):
		ext = ext.lower()
		def func(fn):
			return fn.lower().endswith(ext)
		return func#lambda fn:fn.lower().endswith(ext)
	return list(map(check_ext,extensions))