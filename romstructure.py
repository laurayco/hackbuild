import json, struct, os
import directorysearch
from pyrominfo import RomInfo,gba

def cache_calculations(f):
  def w(*a,**b):
    call = (tuple(a),tuple(b.items()))
    if call in w.cache:return w.cache[call]
    w.cache[call]=f(*a,**b)
    return w.cache[call]
  w.cache={}
  return w

class StructureReference:
	def __init__(self,t,d):
		self.reference = d#will be either a string, or an offset.
		self.target = t#type of RomStructure
	def follow(self,rom):
		return self.target.from_bytes(rom,self.target.actual_pointer(self.reference))

class StructureTableReference(StructureReference):
	def __init__(self,t,d,n):
		StructureReference.__init__(self,t,d)
		self.size = n
	def follow(self,rom):
		for i in range(self.size):
			yield self.target.from_bytes(rom,self.reference + (4*i))

class Reference:
	def __init__(self,location,structure):
		self.location = location
		self.structure = structure
	@property 
	def is_dynamic(self):return isinstance(self.location,str)
	@property
	def is_static(self):return isinstance(self.location,int)
	def fetch(self,project):
		if self.is_static:
			if project.rom is None:
				raise LogicError("Can't decompile a static reference without a ROM.")
			return project.decompile(self.structure,self.location)
		else:
			raise NotImplementedError

class RomEntity:
	def __init__(self,structure,data):
		self.structure = structure
		self.data = data
	def compile(self):
		return self.structure.to_bytes(self.data)
	def dependancies(self):
		for referring_field in self.structure.reference_fields:
			if ReferenceField(self.data[referring_field],self.structure.get_structure(referring_field)).is_dynamic:
				yield referring_field

class RomStructure:
	def __init__(self,fields,constants,games):
		self.fields, self.constants, self.games = fields, constants, games
	def format_string(self):
		return "<"+"".join([a["compile"] for a in sorted(self.fields.values(),key=lambda x:x['order'])])
	def to_bytes(self,data):
		frmt = self.format_string()
		field_list = [field[1] for field in sorted([(val[0],key) for key,value in self.fields.items()])]
		return struct.pack(frmt,[data[field] for field in field_list])
	def from_bytes(self,data,offset=0):
		frmt,offset = self.format_string(),self.actual_pointer(offset)
		raw_data = struct.unpack(frmt,data[offset:offset+struct.calcsize(frmt)])
		data = dict((key,raw_data[info["order"]]) for key,info in self.fields.items())
		return self.make_entity(data)
	def make_entity(self,data):
		return RomEntity(self,data)
	def reference_fields(self):
		for key in self.fields:
			if key[0]=='@':
				yield key
	def get_structure(self,field):return self.fields[field]['reference']
	@classmethod
	def actual_pointer(cls,rom_pointer):return rom_pointer&0x01FFFFFF
	def get_field(self,key,rom=None):
		try:
			reference=self.data[key]
		except KeyError as e:
			print(list(self.data.keys()))
			raise e
		else:
			if key[0]=='@':
				target_datatype = self.structure.fields[key]['reference']
				if target_datatype:
					if key[1:].find('@')>=0:
						length_field = key[1:][:key[1:].find("@")]
						reference = StructureTableReference(target_datatype,reference,self.data[length_field])
					else:
						reference = StructureReference(target_datatype,reference)
					if rom:
						return reference.follow(rom)
			return reference

class StructureLoader(directorysearch.ExtensionSearch):
	def __init__(self,game_code):
		directorysearch.ExtensionSearch.__init__(self,".RomStructure.json","RomStructurePath")
		self.game_code = game_code
	@classmethod
	@cache_calculations
	def create_structure(cls,fn):
		with open(fn) as f:
			data=json.load(f)
			return RomStructure(data['fields'],data.get('constants',{}),data.get('games',[]))
	def load(self,name):
		name += self.extension
		for fn in self.files():
			if fn.lower().endswith(name):
				return self.create_structure(fn)
	@property
	def available_structures(self):
		return map(self.structure_name,self.files())
	def structure_name(self,fn):
		fn = os.path.basename(fn).lower()
		return fn[:-len(self.extension)]
	def accept(self,fn):
		if super().accept(fn):
			return self.game_code in self.create_structure(fn).games

class ProjectManager:
	def __init__(self, rom_data, game_code_assertion=None):
		self.rom = rom_data
		self.rom_info = RomInfo.parseBuffer(self.rom)
		self.game_code = self.rom_info["code"]
		if game_code_assertion:
			assert self.game_code == game_code_assertion
		self.structure_loader = StructureLoader(self.game_code)
	def decompile(self,t,location):
		return self.structure_loader.load(t).from_bytes(self.rom,location)
	def display_entity(self,entity,recurse_level=0):
		for field,info in entity.structure.fields.items():
			data_str = hex(entity.data[field]) if isinstance(entity.data[field],int) else entity.data[field]
			if info['reference']:
				if recurse_level>0:
					ref = Reference(entity.data[field],info['reference'])
					print("\nShowing referenced",info['reference'],"at",data_str)
					self.display_entity(ref.fetch(self),recurse_level-1)
					print("/reference\n")
				else:
					print("Pointer to a",info['reference'],"at",data_str)
			else:print(field,data_str)
		print("="*80)

if __name__=="__main__":
	with open(input("ROM:> "),'rb') as f:
		project_instance = ProjectManager(f.read(),"BPRE")
		while True:
			location = int(input("Map Header Location(hex):> "),16)
			map_entity = project_instance.decompile('pokemonmap',location)
			project_instance.display_entity(map_entity,recurse_level=2)