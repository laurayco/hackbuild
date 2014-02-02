from execution import Task, Event, OrderedProcess, ProcessTask
from romstructure import ProjectManager, RomManager
from threading import RLock as Lock
import ips, json, os

class CompileEntityTask(Task):
	def __init__(self,entity,name,build_manager):
		self.entity, self.build_manager, self.name = entity, rom_manager, name
		deps = list(map('allocate-{}'.format,entity.dependancies())) + 'allocate-{}'.format(name)
		super().__init__('compile-{}'.format(name),self.compile_entity,deps)
	def compile_entity(self):
		# locations are the offsets of other entities.
		# constants are things that are already in the ROM and don't change.
		#   not to be confused with structure "enumerations".
		compiled = self.entity.to_bytes(self.rom_manager.get_locations(),self.build_manager.get_constants())
		self.rom_manager.set_data(compiled,self.name)

class AllocateEntityTask(Task):
	def __init__(self,entity,name,build_manager):
		self.entity, self.name, self.build_manager = entity, name, build_manager
		deps = []
		if entity.structure.is_compressed:
			deps = list(map('allocate-{}'.format,map(entity.data.get,entity.dependancies())))
		super().__init__('allocate-{}'.format(name),self.allocate_entry,deps)
	def allocate_entry(self):
		size = self.entity.calculate_size(self.build_manager.get_locations(),self.build_manager.get_constants())
		self.build_manager.allocate(size,self.name)

class PatchExporterTask(Task):
	def __init__(self, build_manager):
		self.build_manager = build_manager
		self.ips = ips.IPS([])#start with no chunks.
		deps = map('compile-{}',list(zip(*build_manager.entities))[0])
		super().__init__('build-patch',self.make_chunks,list(deps))
	def make_chunks(self):
		for entity_name,entity in self.build_manager.entities:
			location, data = self.build_manager.get_patch_info(entity_name)
			# determine best combination of CLR chunks & Regular Chunks
			# in this part.
			# for now, we'll just make it a single regular chunk.
			self.ips.chunks.append(ips.Chunk(location[0],data))


class BuildManager(OrderedProcess):
	def __init__(self,project,rom_mgr):
		self.rom_mgr = rom_mgr
		self.project = project
		self.location_lock = Lock()
		self.data_lock = Lock()
		self.locations, self.data = {},{}
		#self.verify()
		self.entities, tasks = [], []
		for filename in self.project.files():
			entity_type = filename[filename.find(".")+1:]
			entity_type = entity_type[:len(entity_type)-len(".json")]
			entity_name = os.path.splitext(os.path.basename(filename))[0]
			print("Loading a",entity_type,"from",entity_name)
			structure = self.rom_mgr.structure_loader.load(entity_type)
			entity = structure.make_entity(json.load(open(filename)))
			self.entities.append((entity_name,entity))
			tasks.append(AllocateEntityTask(entity,entity_name,self))
			tasks.append(CompileEntityTask(entity,entity_name,self))
		tasks.append(PatchExporterTask(self))
		super().__init__(tasks,True)
	def allocate(self, size, name):
		with self.location_lock:
			# {name:(location,size)}
			self.locations[name] = (self.rom_mgr.find_space(size,self.locations.items()),size)
	def set_data(self, data, name):
		with self.data_lock:
			self.data[name] = data
	def get_patch_info(self,name):
		with self.location_lock:
			with self.data_lock:
				return self.location[name],self.data[name]

if __name__=="__main__":
	project_directory = input("Project Directory: >")
	with open(input("ROM:> "),'rb') as f:
		rom_mgr = RomManager(f.read())
		project_manager = ProjectManager(project_directory)
		BuildManager(project_manager, rom_mgr).launch()