from threading import RLock as Lock
rom execution import PluginSet
from os import listdir, environ
from os.path import isdir

def find_ranges(l):
	i,start,recent,started=1,l[0],l[0],True
	while i<len(l):
			if l[i]!=recent+1:
				yield range(start,recent+1)
				i+=1
				started=False
				if i<len(l):
					start=recent=l[i-1]
					started=True
				else:break
			else:
				recent=l[i]
				i+=1
	if started:
		yield range(start,recent+1)

class Build:
	align_width=4
	def __init__(self,pkg_mgr):
		self.build_name = "build::{}".format(pkg_mgr.get_build_number())
		self.packages = list(map(pkg_mgr.load_package,pkg_mgr.packages))
		self.available_space = pkg_mgr.freespace()
		self.location_lock,self.blob_lock = Lock(),Lock()
		self.locations,self.blobs = {},{}
	def reserve(self,pkg,size):
		with self.location_lock:
			size = size + size%Build.align_width
			def chunk_range(chunk):
				csize = chunk['size'] + chunk['size']%Build.align_width
				return range(chunk['position'],chunk['position']+csize)
			for space_chunk in available_space:
				rng = chunk_range(space_chunk)
				if len(rng)<size:
					continue
				space_set = set(rng)
				for chunk in self.locations.values():
					space_set = space_set - set(chunk_range(chunk))
				#use the thing with the lowest amount of space.
				#that still has as much as we need.
				remaining_spaces=[s for s in find_ranges(list(space_set)) if len(s)>=size]
				if len(remaining_spaces)<1:
					continue
				remaining_spaces.sort(key=lambda r:len(r))
				self.locations[pkg]={'position':remaining_spaces[0][0],'size':size}
				break
	def location(self,pkg):
		with self.location_lock:
			return self.locations[pkg]
	def set(self,pkg,blob):
		with self.blob_lock:
			self.blobs[pkg]=blob

class Package:
	def __init__(self,data,references):
		self.data=data
		self.references=references
	def calculate_space(self):
		return len(self.data['raw_data']) + Build.align_size * len(self.references)
	def assemble(self,reference_locations):
		total_data,location = b'',0
		def make_ptr(loc):
			return b'08000000'
		for ref in self.references:
			loc = reference_locations[ref['name']]
			total_data+=self.data[:ref['location']] + make_ptr(loc)
		return total_data

class PatchBuilder:
	def __init__(self):
		pass
	def build(self,active_build):
		return b'LOLIMADEAPATCH???'

class PackageManager:
	ExtendedTypes = PluginSet(Package)
	PROJECT_LIST_DIRECTORY = environ.get("HackingProjects","./projects")
	def __init__(self,project_name):
		self.project_name = project_name
		self.base_directory = self.PROJECT_LIST_DIRECTORY + "/" + project_name
	def load_package(self,pkg_name):
		return self.determine_pkg_type(pkg_name).load(open(pkg_name))
	def freespace(self):
		return []
	@property
	def packages(self):
		r=[]
		for pkg_type in listdir(self.base_directory):
			if not isdir(self.base_directory+"/"+pkg_type):continue
			for pkg_name in listdir(self.base_directory+"/"+pkg_type):
				r.append(pkg_type+"/"+pkg_name)
		return r
	def get_build_number(self):return 0
	def make_build(self):
		return Build(self)
