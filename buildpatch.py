from execution import Task, Event, OrderedProcess, ProcessTask
from romstructure import ProjectManager, RomManager
import ips, json

class BuildManager(OrderedProcess):
	def __init__(self,project,rom_mgr):
		self.rom_mgr = rom_mgr
		self.project = project
		#self.verify()
		entities = []
		for filename in self.project.files():
			entity_type = filename[filename.find(".")+1:]
			entity_type = entity_type[:len(entity_type)-len(".json")]
			print("Loading a",entity_type,"from",filename)
			structure = self.rom_mgr.structure_loader.load(entity_type)
			self.rom_mgr.display_entity(structure.make_entity(json.load(open(filename))))
			print()


if __name__=="__main__":
	project_directory = input("Project Directory: >")
	with open(input("ROM:> "),'rb') as f:
		rom_mgr = RomManager(f.read())
		BuildManager(ProjectManager(project_directory),rom_mgr)