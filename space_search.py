def find_ranges(l):
	i,start,recent,started=1,l[0],l[0],True
	while i<len(l):
			if l[i]!=recent+1:
				yield range(start,recent+1)
				i+=1
				started=False
				if i<len(l):
					start=recent=l[i-1]
					started=True
				else:break
			else:
				recent=l[i]
				i+=1
	if started:
		yield range(start,recent+1)

ranges = [
	range(0,10),
	range(20,30),
	range(40,50)
]
spaces = sum(map(list,ranges),[])

for r in group(spaces):
	print(set(r))