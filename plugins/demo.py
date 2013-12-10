import execution

class SimplePlugin(execution.DemoPlugin):
	@property
	def overriden(self):
		return "SIMPLY."