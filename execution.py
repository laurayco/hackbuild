from threading import Thread, RLock, Condition

def string_list(s):return s.split() if isinstance(s,str) else s

class Event:
	def __init__(self):self.handlers=[]
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
		self.to_do = list(map(make_launcher,m))
		name_access = {}#for caching purposes.
		def get_todo(name):
			if name in name_access:
				return name_access[name]
			q=[t for t in self.to_do if t.name==name]
			print(name,"::",q)
			assert len(q)==1
			name_access[name]=q[0]
			return get_todo(name)
		for task in self.to_do:
			task.async = self.async
			task.on_finish.handlers.append(self.finished)
			name_access[task.name]=task
			for dep in task.dependancies:
				get_todo(dep).on_finish.handlers.append(task.is_ready)
		self.start_nodes = [td for td in self.to_do if len(td.dependancies)<1]
		self.pending = [td.name for td in self.to_do]
		self.pending_lock = Condition()
	def finished(self,td):
		with self.pending_lock:
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
		

if __name__=="__main__":
	from time import sleep
	def name_and_delay(n,delay):
		def f():
			print("Function {} takes {} seconds.".format(n,delay))
			sleep(delay)
			print("Exiting function {}".format(n))
		return f

	m,async,wait = [
		('a',name_and_delay("a",.100),""),
		('b',name_and_delay("b",2.000),""),
		('c',name_and_delay("c",1.400),'a b'),
		('d',name_and_delay("d",.700),'b'),
		('e',name_and_delay("e",.830),'a'),
		('f',name_and_delay("f",.450),'c'),
		('g',name_and_delay("g",3.000),"")
	],True,True
	
	print("Starting ordered process...")
	OrderedProcess(m,async).launch(wait)
	print("Ordered process finished","launching." if not wait else "running.")