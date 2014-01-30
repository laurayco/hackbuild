import os, sys

class FileSearch:
	environment_splitter = ';'#change to ':' on linux.
	def __init__(self,search_name=None):
		self.search_name=search_name
	@property
	def environment_name(self):
	    if self.search_name:return self.search_name
	    return type(self).__name__
	@property
	def directories(self):
		search_dirs = os.path.expandvars(self.environment_name).split(self.environment_splitter)
		if len(search_dirs)==1 and search_dirs[0]==self.environment_name: search_dirs = []
		return [
			os.path.join(os.getcwd(),self.environment_name),
			os.getcwd(),
		] + search_dirs
	def files(self):
		for directory in self.directories:
			if not os.path.exists(directory):
				os.makedirs(directory)
			if os.path.isdir(directory):
				for filename in os.listdir(directory):
					if self.accept(os.path.join(directory,filename)):
						yield os.path.join(directory,filename)
	def accept(self,filename):
		return True

class ExtensionSearch(FileSearch):
	def __init__(self,extension,search_name=None):
		FileSearch.__init__(self,search_name)
		self.extension = extension.lower()
	def accept(self,filename):
		return filename.lower().endswith(self.extension)
