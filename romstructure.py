import json, struct

class RomStructure:
	#name:(order,struct-code,None-or-referencing class)
	#  notice: prefix a field-name with "@" to indicate a pointer.
	#          prefix with "@other-field-name@" to indicate an array pointer
	#          with a length defined in other-field-name.
	fields = {}
	def __init__(self,data):
		assert all(k in data for k in self.fields.keys())
		self.data = data
	@classmethod
	def format_string(cls): return "<"+"".join([a[1] for a in sorted(cls.fields.values())])
	@classmethod
	def from_bytes(cls,data,offset=0):
		frmt,offset = cls.format_string(),cls.actual_pointer(offset)
		raw_data = struct.unpack(frmt,data[offset:offset+struct.calcsize(frmt)])
		data = dict((key,raw_data[info[0]]) for key,info in cls.fields.items())
		return cls(data)
	@classmethod
	def to_bytes(cls,data):
		frmt = cls.format_string()
		field_list = [field[1] for field in sorted([(val[0],key) for key,value in cls.fields.items()])]
		return struct.pack(frmt,[data[field] for field in field_list])
	def compile(self): return self.to_bytes(self.data)
	@classmethod
	def actual_pointer(cls,rom_pointer):return rom_pointer&0x01FFFFFF

# a "proto-type" so I can reference them in the field definitions.
class MapHeaderStructure(RomStructure):pass
class ConnectionHeaderStructure(RomStructure):pass
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

class ConnectionHeaderStructure(RomStructure):
	fields = {
		"num_connections":(0,"I",None),
		"@num_connections@connections":(1,"I",MapConnectionStructure)
	}

class MapConnectionStructure(RomStructure):
	fields = {
		"connection_type":(0,"I",None),
		"connection_offset":(1,"I",None),
		"map_bank":(2,"B",None),
		"map_number":(3,"B",None),
		"filler":(4,"H",None)
	}

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
	from pprint import pprint
	rom_fn = input("Rom File Name>")
	BANK_LIST_OFFSET = 0x3526A8
	try: rom = open(rom_fn,'rb').read()
	except:raise
	else:
		while True:
			bank = int(input("Map Bank>"))
			map = int(input("Map Number>"))
			display_structure(MapHeaderStructure.load_map(rom,bank,map,BANK_LIST_OFFSET),False)
