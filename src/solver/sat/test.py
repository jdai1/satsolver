import copy

x = [{1}, {2}, {3}]

y = copy.deepcopy(x)

y[0].add(5)

print(x)
print(y)