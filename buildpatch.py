from execution import Task, Event, OrderedProcess, ProcessTask
from buildmgr import Build, Package, PackageManager, PatchBuilder

class FindSpace(Task):
	def __init__(self,pkg,active_build):
		self.package = pkg
		self.build = active_build
		name = FindSpace.task_name(self.package)
		Task.__init__(self,name,self.findspace,"")
	@classmethod
	def task_name(cls,pkg):return "allocate-"+pkg.name
	def findspace(self):
		# sends a request to build.pkgmgr
		# to allocate space for pkg
		# take this space, and reserve with
		# build.reserve(pkg,offset)
		# PLEASE NOTE:
		#    this(build.request) NEEDS to be thread-safe(!)
		#    otherwise ( even assuming there
		#    aren't any thrown-exceptions. )
		#    you could end up with the same
		#    offset being used many times over.
		build.reserve(self.package.name,self.build.request(self.pkg.compute_size()))

class Compile(Task):
	def __init__(self,pkg,active_build):
		self.package = pkg
		self.build = active_build
		name = Compile.task_name(self.package)
		dependancies = [FindSpace.task_name(pkg) for pkg in pkg.references]
		dependancies.append(FindSpace.task_name(pkg))
		Task.__init__(self,name,self.compile_pkg,dependancies)
	@classmethod
	def task_name(cls,pkg):return "compile-"+pkg.name
	def compile_pkg(self):
		# It's a good idea to make the below thread-safe, as well.
		# it would make sense, sense it accesses the same variable
		# as build.reserve, but still.
		locations = {n:self.build.location(n) for n in self.package.references}
		# again, this(build.set) should be thread safe.
		# it's just a good idea to do that in threaded
		# contexts.
		build.set(self.package.name,self.package.assemble(references))

class Link(ProcessTask):
	def __init__(self,build,async=True):
		self.build = build
		pkgs = self.build.packages
		tasks = list(FindSpace(pkg,self.build) for pkg in pkgs)
		tasks.extend(Compile(pkg,self.build) for pkg in pkgs)
		process = OrderedProcess(tasks,async)
		name = Link.task_name(self.build)
		ProcessTask.__init__(self,process,name,"")
	@classmethod
	def task_name(self,build):return "link-"+build.build_name

class MakePatch(Task):
	def __init__(self,pkg_mgr,build,format):
		self.pkg_mgr = pkg_mgr
		self.active_build = build
		self.formats=formats
		name = MakePatch.task_name(self.active_build)
		Task.__init__(self,name,self.make_patches,Link.task_name(self.active_build))
	def make_patches(self):
		builder=MakePatch.get_builder(self.format)
		self.pkg_mgr.output_patch(builder.build(self.active_build))
	@classmethod
	def get_builder(cls,format):pass
	@classmethod
	def task_name(cls,build,format):return "patch-"+format+build.buid_name

class BuildProject(ProcessTask):
	def __init__(self,pkg_mgr,formats):
		self.pkg_mgr = pkg_mgr
		self.active_build = pkg_mgr.make_build()
		link = Link(self.active_build)
		patch = [MakePatch(self.pkg_mgr,self.active_build,fmt) for fmt in formats]
		name = BuildProject.task_name(pkg_mgr)
		ProcessTask.__init__(self,OrderedProcess([link]+patch,True),name,"")
	@classmethod
	def task_name(cls,pkgmgr):return "build-"+pkgmgr.project_name

class BuildProjects(OrderedProcess):
	def __init__(self,f,projects):
		projects=list(map(PackageManager,projects))
		OrderedProcess.__init__(self,[BuildProject(p,f) for p in projects],True)

if __name__=="__main__":
	from sys import argv;argv,formats,i=argv[1:],[],0
	formats,projects={},[]
	def is_set_format_flag(s):
		s=s.lower()
		if s=='-f' or s=='--format':
			return True
	while i < len(argv):
		if is_set_format_flag(argv[i]):
			i+=1
			formats[argv[i]]=True
		else:
			projects.append(argv[i])
		i+=1
	process=BuildProjects(list(formats.keys()),projects)
	process.launch(True)