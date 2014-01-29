import json, struct, os
import directorysearch

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

class RomEntity:
	def __init__(self,structure,data):
		self.structure = structure
		self.data = data
	def compile(self):
		return self.structure.to_bytes(self.data)

class RomStructure:
	def __init__(self,fields,constants):
		self.fields, self.constants = fields, constants
	def format_string(self): return "<"+"".join([a[1] for a in sorted(self.fields.values())])
	def to_bytes(self,data):
		frmt = self.format_string()
		field_list = [field[1] for field in sorted([(val[0],key) for key,value in self.fields.items()])]
		return struct.pack(frmt,[data[field] for field in field_list])
	def from_bytes(self,data,offset=0):
		frmt,offset = self.format_string(),self.actual_pointer(offset)
		raw_data = struct.unpack(frmt,data[offset:offset+struct.calcsize(frmt)])
		data = dict((key,raw_data[info[0]]) for key,info in self.fields.items())
		return self.make_entity(data)
	def make_entity(self,data):
		return RomEntity(self,data)
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
				target_datatype = self.structure.fields[key]['referencing']
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
	def __init__(self):
		directorysearch.ExtensionSearch.__init__(self,".RomStructure.json","RomStructurePath")
	def load(self,name):
		name += self.extension
		fn = ""
		for fn in self.files:
			if fn.endswith(name):break
		with open(fn) as f:
			data=json.load(f)
			return RomStructure(data['fields'],data.get('constants',{}))
	@property
	def available_structures(self):return map(self.structure_name,self.files())
	def structure_name(self,fn):
		print(fn)
		fn = os.path.basename(fn).lower()
		return fn[:-len(self.extension)]

# a "proto-type" so I can reference them in the field definitions.
class MapHeaderStructure(RomStructure):pass

class MapConnectionStructure(RomStructure):
	fields = {
		"connection_type":(0,"I",None),
		"connection_offset":(1,"I",None),
		"map_bank":(2,"B",None),
		"map_number":(3,"B",None),
		"filler":(4,"H",None)
	}

class ConnectionHeaderStructure(RomStructure):
	fields = {
		"num_connections":(0,"I",None),
		"@num_connections@connections":(1,"I",MapConnectionStructure)
	}

class MapConnectionStructure(RomStructure):pass
class MapDataStructure(RomStructure):pass
class MapScriptStructure(RomStructure):pass
class EventDataStructure(RomStructure):pass

class MapHeaderStructure(RomStructure):
	fields = {
		"@map_data":(0,"I",MapDataStructure),
		"@event_data":(1,"I",EventDataStructure),
		"@map_scripts":(2,"I",MapScriptStructure),
		"@connections":(3,"I",ConnectionHeaderStructure),
		"music":(4,"H",None),
		"map_index":(5,"H",None),
		"label_index":(6,"B",None),
		"flash":(7,"B",None),
		"weather":(8,"B",None),
		"map_type":(9,"B",None),
		"unknown":(10,"H",None),
		"show_label":(11,"B",None),
		"battle_type":(12,"B",None)
	}
	@classmethod
	def load_map(cls,rom,bank,map,bank_offset):
		load_pointer=lambda offset:cls.actual_pointer(struct.unpack("<I",rom[offset:offset+4])[0])
		map_pointer = load_pointer(load_pointer(bank_offset + bank * 4) + map * 4)
		return cls.from_bytes(rom,map_pointer)

def display_structure(structure,recurse=True):
	print("{} object:".format(type(structure).__name__))
	for field, value in structure.data.items():
		is_pointer = field[0]=='@'
		field_info = structure.fields[field]
		desc = field_info[2].__name__ if field_info[2] and issubclass(field_info[2],RomStructure) else field
		if is_pointer:
			field=field[1:]
			is_table = field.find('@')
			if is_table>=0: is_table,field = field[:is_table],field[is_table+1:]
			else: is_table = False
			if is_table:
				desc = "pointer to a table of {}'s with {} entries @{}.".format(desc, structure.data[is_table],hex(value))
			else:
				desc = "pointer to a {} @{}.".format(desc,hex(value))
			print("{:>20}:\t{}".format(field,desc))
		else: print("{:>20}:\t{}".format(desc,value))


if __name__=="__main__":
	structure_loader = StructureLoader()
	for structure_name in structure_loader.available_structures:
		print("Found structure type:",structure_name)