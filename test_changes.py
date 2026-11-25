from changes import find_removed, looks_like_a_partial_download
cache=[('A','One'),('B','Two'),('C','nan'),('D','Party Horn')]
cur={'A','E'}
new=[('E','Brand New'),('F','party horn')]
r=find_removed(cache,cur,new)
assert r==[('B','Two',None),('C','',None),('D','Party Horn','F')],r
assert find_removed(cache,{'A','B','C','D'},[])==[]
assert looks_like_a_partial_download(100,60) and not looks_like_a_partial_download(1000,10) and not looks_like_a_partial_download(100,30)
print('changes ok')
