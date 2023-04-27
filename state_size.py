from itertools import combinations_with_replacement

alpha = "_abcde"

seen = set()
for i in list(combinations_with_replacement(alpha, 5)):
	w = ''.join(i)
	if "".join(sorted(w)) == w:
		seen.add(w)

seen.remove('_____')
print(len(seen))

