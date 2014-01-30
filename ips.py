def dir_part(fn):
	end = fn.rfind("\\")
	if end<0:return '.\\'
	return fn[:end]
def ext_part(fn):return fn[fn.rfind('.')+1:].lower()
def name_part(fn):
	s,e=max(fn.find("\\"),0),max(fn.rfind("."),0)
	fn=(fn[s:e] if s>0 and e>0 else (fn[s:] if s>0 else (fn[:e] if e>0 else fn)))
	return fn.strip().lower()
def bytes_to_int(b,l):
	r,i=0,0
	while i<l:
		e,i,v=8*(l-i-1),i+1,b[i]
		r = r|((v<<e)&(0xFF<<e))
	return r
def non_store_length(g,predicates=[]):
	r=0
	for e in g:
		if all(p(e) for p in predicates):
			r+=1
	return r
def find_ranges(p):
	q,i = sorted(list(p)),0
	for j in xrange(1,len(q)):
		if q[j] > 1+q[j-1]:
			yield range(q[i],q[j-1])
			i = j
	yield range(q[i], q[-1])

class Chunk:
	def __init__(self,offset,data):
		self.offset = offset&0x00FFFFFF#ensure things are within bounds of valid ROM size.
		self.data = data
	def apply(self,arr):
		arr[self.offset:self.offset+len(self.data)]=self.data
		return arr
	def write_to_file(self,f):
		pass

class RLEChunk(Chunk):
	def __init__(self,offset,data,size):
		Chunk.__init__(self,offset,[data]*size)
	def write_to_file(self,f):
		pass
#
class IPS:
	MAGIC = b'\x50\x41\x54\x43\x48'
	END = b'\x45\x4f\x46'
	@classmethod
	def create_from_diff_streams(cls,original,modified):
		return cls.create_from_diff(bytearray(original.read()),bytearray(modified.read()))
	@classmethod
	def create_from_diff(cls,original,modified):
		CHUNK_MIN_SIZE,RLE_SIZE = 6,8
		RLE_BREAK_SIZE=RLE_SIZE+(CHUNK_MIN_SIZE-RLE_SIZE)*2
		differences,chunks=[],[]
		i,l=0,min(len(original),len(modified))
		#to-do:
		#  * make map of differences.
		while i<l:
			e=i
			while original[e]!=modified[e]:e+=1#found a difference.
			if e>i:differences.append(set(range(i,e)))
			i=e+1
		#  * release original / unmodified data
		del original[:]
		original=None
		#  * reduce differences into smallest
		#    calculated size. ( including RLE optimization )
		i,l=0,len(differences)
		while i<l:
			original = sorted(differences[i])
			start,end= original[0],original[-1]
			j,c = 0,modified[start]
			new_chunks = []
			while start+j < end:
				e=j
				while modified[e]==c:
					print(e)
					e+=1
				if e>j:
					new_chunks.append(set(range(j,e)))
					#rebuild a new chunk based on the fragments of this set later.
					original = original - new_chunks[-1]
				j=e
			if len(new_chunks)>0:
				del differences[i]
				differences.extend(new_chunks+list(find_ranges(list(original))))
				l-=1
		#  * capture difference data in Chunk objects, append to chunks list.
		#  release modified data.
		#  del modified[:]
		#  modified=None
		return cls(chunks)
	@classmethod
	def create_from_stream(cls,stream):
		return cls.create_from_bytes(bytearray(stream.read()))
	@classmethod
	def create_from_bytes(cls,byte_array):
		def pull_all_chunks(arr):
			END_POSITION,position=len(arr)-len(cls.END),0
			while position<END_POSITION:
				offset,size,position=bytes_to_int(arr[position:position+3],3),bytes_to_int(arr[position+3:position+5],2),position+5
				if size==0:
					yield RLEChunk(offset,arr[position+2],bytes_to_int(arr[position:position+2],2))
					position+=3
				else:
					data,position=arr[position:position+size],position+size
					yield Chunk(offset,data)
		if byte_array[:len(cls.MAGIC)]==cls.MAGIC:
			byte_array=byte_array[len(cls.MAGIC):]#ignore the magic code if it isn't already skipped.
		return cls(list(pull_all_chunks(byte_array)))
	def __init__(self,chunks):self.chunks = chunks
	def apply(self,arr):
		for chunk in self.chunks:arr=chunk.apply(arr)
	def write_to_file(self,f):
		f.write(IPS.MAGIC)
		for chunk in self.chunks:
			chunk.write_to_file(f)
		f.write(IPS.END)

class PatchApplication:
	@staticmethod
	def make_filename(t,p):
		return "{}{}{}-{}-patched.{}".format(dir_part(t),'\\',name_part(t),'-'.join(p),'gba')
	def __init__(self,target,*patches):
		self.target = target
		self.patches = patches
	def run(self):
		data = bytearray(open(self.target,'rb').read())
		for patch in map(IPS.create_from_stream,map(lambda x:open(x,'rb'),self.patches)):
			patch.apply(data)
		with open(PatchApplication.make_filename(self.target,self.patches),'wb') as f:
			f.write(data)

class PatchGeneration:
	@staticmethod
	def make_filename(o,m):
		filename_pattern = "{}{}{}-patched-to-{}.{}"
		return filename_pattern.format(dir_part(m),'\\',o,m,'ips')
	def __init__(self,base,modified): self.original,self.modified=base,modified
	def run(self):
		base = bytearray(open(self.original,'rb').read())
		modified = bytearray(open(self.modified,'rb').read())
		patch = IPS.create_from_diff(base,modified)
		with open(PatchGeneration.make_filename(self.original,self.modified),'wb') as f:
			patch.write_to_file(f)

if __name__=="__main__":
	from sys import argv;argv=argv[1:]
	from os.path import isfile
	i,l=0,len(argv)
	while i<l:
		patches=[]
		while i<l and isfile(argv[i]) and ext_part(argv[i])=='ips':
			patches,i=patches+[argv[i]],i+1
		if len(patches)>0:
			if i<l:
				PatchApplication(argv[i],*patches).run()
		elif isfile(argv[i]) and isfile(argv[i+1]):
			if ext_part(argv[i])==ext_part(argv[i+1]):
				PatchGeneration(argv[i],argv[i+1]).run()
				i+=1
		i+=1