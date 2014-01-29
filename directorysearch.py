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
	def directories(self):return [
			os.path.join(os.getcwd(),self.environment_name),
			os.getcwd(),
		] + os.path.expandvars(self.environment_name).split(self.environment_splitter)
	def files(self):
		for directory in self.directories:
			for filename in os.listdir(directory):
				if self.accept(filename):
					yield os.path.join(directory,filename)
	def accept(self,filename):return True

class ExtensionSearch(FileSearch):
	def __init__(self,extension,search_name=None):
		FileSearch.__init__(self,search_name)
		self.extension = extension.lower()
	def accept(self,filename): return filename.lower().endswith(self.extension)
