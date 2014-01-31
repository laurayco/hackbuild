from threading import Thread, RLock, Condition, Event
from os import listdir, stat as fstat
from os.path import join as joinpath, basename, splitext, dirname, realpath
from imp import load_source
from sys import modules
import inspect

def string_list(s):return s.split() if isinstance(s,str) else s

class Event:
	def __init__(self,handlers=None):self.handlers=handlers or []
	def trigger(self,*a,**kw):
		for h in self.handlers:
			h(*a,**kw)

def post(f,a,async=False):
	def ff():
		f()
		a()
	def w():
		if async: return Thread(target=ff).start
		return ff
	return w()

class Task:
	async=False
	def __init__(self,name,task,dependancies):
		dependancies = string_list(dependancies)
		self.dependancies = {d:False for d in dependancies}
		self.dependant_lock = RLock()
		self.task,self.name=task,name
		self.on_finish = Event()
	def launch(self):
		def done():
			self.on_finish.trigger(self.name)
		post(self.task,done,self.async)()
	def is_ready(self,signal):
		with self.dependant_lock:
			self.dependancies[signal]=True
			if all(self.dependancies.values()):
				self.launch()

class OrderedProcess:
	def __init__(self,m,async=False):
		# m = [ TaskObject| (name,function,dependancies), <...>]
		self.async = async
		def make_launcher(args):
			if isinstance(args,Task):
				return args
			else:
				t=Task(*args)
				t.async=self.async
				return t
		to_do,name_access = list(map(make_launcher,m)),{}#for caching purposes.
		def get_todo(name):
			if name in name_access:
				return name_access[name]
			q=[t for t in to_do if t.name==name]
			assert len(q)==1
			name_access[name]=q[0]
			return get_todo(name)
		for task in to_do:
			task.async = self.async
			task.on_finish.handlers.append(self.finished)
			name_access[task.name]=task
			for dep in task.dependancies:
				get_todo(dep).on_finish.handlers.append(task.is_ready)
		self.start_nodes = [td for td in to_do if len(td.dependancies)<1]
		self.pending = [td.name for td in to_do]
		self.pending_lock = Condition()
	def finished(self,td):
		with self.pending_lock:
			print("Finished:",td)
			self.pending.remove(td)
			if len(self.pending)<1:
				self.pending_lock.notify_all()
	def launch(self,wait=True):
		if len(self.start_nodes)<1:
			assert len(self.to_do)<1
			return
		print("Launching...")
		for node in self.start_nodes:
			node.launch()
		print("Launched.")
		if wait and self.async:
			with self.pending_lock:
				self.pending_lock.wait()

class ProcessTask(Task):
	def __init__(self,process,name,dependancies):
		Task.__init__(self,name,self.run_process,dependancies)
		self.process=process
	def run_process(self):
		self.process.launch(True)

class DirectoryWatch(Thread):
	MINIMUM_FREQUENCY = 60
	def __init__(self,directory,frequency,ready_fun=None):
		self.frequency,self.frequency_lock=frequency,RLock()
		self.target_directory = directory
		self.modified_times_lock,self.modified_times = RLock(),{}#filename:modified_time
		# notice that the modified_time is arbitrary and that I really don't need
		# to know anything about it, except to compare it.
		self.on_update = Event()
		Thread.__init__(self)
		self.daemon=True
		if ready_fun:
			self.on_update.handlers.append(ready_fun)
		self.scan_files()
		if ready_fun:
			self.on_update.handlers.remove(ready_fun)
	def scan_files(self):
		frequency_adjustment=1.0
		with self.modified_times_lock:
			for fn in listdir(self.target_directory):
				t=fstat(joinpath(self.target_directory,fn)).st_mtime
				if self.modified_times.get(fn,-1)<t:
					self.modified_times[fn]=t
					self.on_update.trigger(joinpath(self.target_directory,fn),t)
					frequency_adjustment += 1.0
				else: self.frequency_adjustment -= 1.0
			frequency_adjustment /= max(len(self.modified_times),1)
		with self.frequency_lock:
			freq = self.frequency - (self.frequency*frequency_adjustment)
			self.frequency = max(self.MINIMUM_FREQUENCY,freq)
	def run(self):
		wait = Event()
		while True:
			self.scan_files()
			wait.wait(self.frequency)

# taken from: https://djangosnippets.org/snippets/542/
class PluginMount(type):
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'plugins'):
            print("Initializing plugin mount:",cls.__name__)
            # This branch only executes when processing the mount point itself.
            # So, since this is a new plugin type, not an implementation, this
            # class shouldn't be registered as a plugin. Instead, it sets up a
            # list where plugins can be registered later.
            cls.plugins = []
        else:
            print("Adding plugin",cls.__name__)
            # This must be a plugin implementation, which should be registered.
            # Simply appending it to the list is all that's needed to keep
            # track of it later.
            cls.plugins.append(cls)
