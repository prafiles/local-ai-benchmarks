#!/usr/bin/env python3
"""Python category — 50 tasks. Each ships a reference solution.

verify() execs every (reference + tests) pair; any task whose own reference
fails its assertions is a broken task, not a model failure.
"""

# (id, spec, tests, reference)
T = [
("py-001", "class `LRUCache` with `__init__(self, capacity)`, `get(self, key)` returning -1 when "
 "absent, `put(self, key, value)`. Both must be O(1).",
 """
c=LRUCache(2); c.put(1,1); c.put(2,2)
assert c.get(1)==1
c.put(3,3); assert c.get(2)==-1
c.put(4,4); assert c.get(1)==-1 and c.get(3)==3 and c.get(4)==4
import inspect,re
assert not re.search(r'\\.index\\(|\\.remove\\(', inspect.getsource(LRUCache)), 'O(n) list ops'
""",
 """
class _N:
    __slots__=('k','v','p','n')
    def __init__(s,k=0,v=0): s.k=k; s.v=v; s.p=None; s.n=None
class LRUCache:
    def __init__(self,capacity):
        self.cap=capacity; self.m={}
        self.h=_N(); self.t=_N(); self.h.n=self.t; self.t.p=self.h
    def _pop(self,x): x.p.n=x.n; x.n.p=x.p
    def _push(self,x):
        x.n=self.h.n; x.p=self.h; self.h.n.p=x; self.h.n=x
    def get(self,key):
        if key not in self.m: return -1
        x=self.m[key]; self._pop(x); self._push(x); return x.v
    def put(self,key,value):
        if key in self.m:
            x=self.m[key]; x.v=value; self._pop(x); self._push(x); return
        if len(self.m)>=self.cap:
            last=self.t.p; self._pop(last); del self.m[last.k]
        x=_N(key,value); self.m[key]=x; self._push(x)
"""),
("py-002", "function `topo_sort(graph)` where graph maps node -> list of dependencies. Return a "
 "list ordering every node after its dependencies, or None on a cycle.",
 """
r=topo_sort({'a':[],'b':['a'],'c':['b']}); assert r.index('a')<r.index('b')<r.index('c')
assert topo_sort({'a':['b'],'b':['a']}) is None
assert topo_sort({})==[]
assert sorted(topo_sort({'x':[],'y':[]}))==['x','y']
""",
 """
def topo_sort(graph):
    st={}; out=[]
    def go(n):
        c=st.get(n,0)
        if c==1: return False
        if c==2: return True
        st[n]=1
        for d in graph.get(n,[]):
            if not go(d): return False
        st[n]=2; out.append(n); return True
    for n in graph:
        if not go(n): return None
    return out
"""),
("py-003", "function `parse_csv(text)` parsing CSV with a header row into a list of dicts, "
 "handling double-quoted fields containing commas and doubled quotes as an escaped quote.",
 """
t='name,note\\nalice,"hello, world"\\nbob,"say ""hi"" now"'
assert parse_csv(t)==[{'name':'alice','note':'hello, world'},{'name':'bob','note':'say "hi" now'}]
""",
 """
import csv,io
def parse_csv(text): return [dict(r) for r in csv.DictReader(io.StringIO(text))]
"""),
("py-004", "class `TokenBucket` with `__init__(self, capacity, refill_per_sec, now)` and "
 "`allow(self, now)` returning True if a token was consumed. Tokens refill continuously with "
 "elapsed time and never exceed capacity. Do not call time.time.",
 """
b=TokenBucket(2,1.0,0.0)
assert b.allow(0.0) is True and b.allow(0.0) is True and b.allow(0.0) is False
assert b.allow(1.0) is True and b.allow(1.0) is False
b2=TokenBucket(3,1.0,0.0); assert b2.allow(100.0) is True
b2.allow(100.0); b2.allow(100.0); assert b2.allow(100.0) is False
""",
 """
class TokenBucket:
    def __init__(self,capacity,refill_per_sec,now):
        self.cap=capacity; self.r=refill_per_sec; self.t=now; self.tok=float(capacity)
    def allow(self,now):
        self.tok=min(self.cap,self.tok+(now-self.t)*self.r); self.t=now
        if self.tok>=1: self.tok-=1; return True
        return False
"""),
("py-005", "function `lcs_len(a, b)` returning the length of the longest common subsequence.",
 """
assert lcs_len('abcde','ace')==3 and lcs_len('abc','abc')==3
assert lcs_len('abc','def')==0 and lcs_len('','x')==0
""",
 """
def lcs_len(a,b):
    m=[[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(1,len(a)+1):
        for j in range(1,len(b)+1):
            m[i][j]=m[i-1][j-1]+1 if a[i-1]==b[j-1] else max(m[i-1][j],m[i][j-1])
    return m[len(a)][len(b)]
"""),
("py-006", "function `normalize(path)` normalizing a POSIX path: collapse duplicate slashes, "
 "resolve '.' and '..', keep a leading '/' if absolute. Return '/' for an empty absolute result "
 "and '.' for an empty relative result. Do not use os.path.",
 """
assert normalize('/a//b/../c/')=='/a/c'
assert normalize('a/./b/../../c')=='c'
assert normalize('/..')=='/' and normalize('')=='.' and normalize('/a/b/c')=='/a/b/c'
""",
 """
def normalize(path):
    absolute=path.startswith('/'); out=[]
    for p in path.split('/'):
        if p=='' or p=='.': continue
        if p=='..':
            if out and out[-1]!='..': out.pop()
            elif not absolute: out.append('..')
        else: out.append(p)
    s='/'.join(out)
    return ('/'+s) if absolute else (s or '.')
"""),
("py-007", "function `merge_dicts(a, b)` deeply merging b into a and returning a NEW dict without "
 "mutating either. Nested dicts merge recursively; other values in b overwrite.",
 """
a={'x':{'y':1,'z':2},'k':1}; b={'x':{'z':9,'w':3},'n':5}
assert merge_dicts(a,b)=={'x':{'y':1,'z':9,'w':3},'k':1,'n':5}
assert a=={'x':{'y':1,'z':2},'k':1} and b=={'x':{'z':9,'w':3},'n':5}
""",
 """
def merge_dicts(a,b):
    out=dict(a)
    for k,v in b.items():
        if k in out and isinstance(out[k],dict) and isinstance(v,dict): out[k]=merge_dicts(out[k],v)
        else: out[k]=dict(v) if isinstance(v,dict) else v
    return out
"""),
("py-008", "decorator `retry(times)` retrying the wrapped function up to `times` total attempts on "
 "exception, re-raising the last one if all fail. Preserve __name__. Do not sleep.",
 """
c={'n':0}
@retry(3)
def flaky():
    c['n']+=1
    if c['n']<3: raise ValueError('boom')
    return 'ok'
assert flaky()=='ok' and c['n']==3 and flaky.__name__=='flaky'
d={'n':0}
@retry(2)
def always(): d['n']+=1; raise KeyError('no')
try: always(); assert False
except KeyError: pass
assert d['n']==2
""",
 """
import functools
def retry(times):
    def deco(fn):
        @functools.wraps(fn)
        def w(*a,**k):
            last=None
            for _ in range(times):
                try: return fn(*a,**k)
                except Exception as e: last=e
            raise last
        return w
    return deco
"""),
("py-009", "function `group_by(items, key)` returning a dict mapping key(item) to the list of "
 "items, preserving input order.",
 """
assert group_by([1,2,3,4], lambda x:'odd' if x%2 else 'even')=={'odd':[1,3],'even':[2,4]}
assert group_by([],lambda x:x)=={}
""",
 """
def group_by(items,key):
    out={}
    for it in items: out.setdefault(key(it),[]).append(it)
    return out
"""),
("py-010", "function `chunk(lst, size)` splitting a list into consecutive sublists of length size, "
 "final chunk possibly shorter. Raise ValueError if size < 1.",
 """
assert chunk([1,2,3,4,5],2)==[[1,2],[3,4],[5]]
assert chunk([],3)==[] and chunk([1,2,3],3)==[[1,2,3]]
try: chunk([1],0); assert False
except ValueError: pass
""",
 """
def chunk(lst,size):
    if size<1: raise ValueError('size must be >= 1')
    return [lst[i:i+size] for i in range(0,len(lst),size)]
"""),
("py-011", "function `is_balanced(s)` returning True if (), [] and {} in the string are balanced "
 "and correctly nested, ignoring other characters.",
 """
assert is_balanced('a(b[c]{d})e') is True and is_balanced('([)]') is False
assert is_balanced('(') is False and is_balanced('') is True
""",
 """
def is_balanced(s):
    pairs={')':'(',']':'[','}':'{'}; st=[]
    for ch in s:
        if ch in '([{': st.append(ch)
        elif ch in pairs:
            if not st or st.pop()!=pairs[ch]: return False
    return not st
"""),
("py-012", "function `roman_to_int(s)` converting a Roman numeral to an integer.",
 """
assert roman_to_int('III')==3 and roman_to_int('IX')==9
assert roman_to_int('MCMXCIV')==1994 and roman_to_int('LVIII')==58
""",
 """
def roman_to_int(s):
    v={'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}; t=0
    for i,ch in enumerate(s):
        if i+1<len(s) and v[ch]<v[s[i+1]]: t-=v[ch]
        else: t+=v[ch]
    return t
"""),
("py-013", "function `int_to_roman(n)` converting an integer 1..3999 to a Roman numeral.",
 """
assert int_to_roman(3)=='III' and int_to_roman(9)=='IX'
assert int_to_roman(1994)=='MCMXCIV' and int_to_roman(58)=='LVIII'
""",
 """
def int_to_roman(n):
    vals=[(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),
          (40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
    out=[]
    for v,sym in vals:
        while n>=v: out.append(sym); n-=v
    return ''.join(out)
"""),
("py-014", "function `flatten(nested)` flattening an arbitrarily nested list into a flat list, "
 "preserving order.",
 """
assert flatten([1,[2,[3,[4]]],5])==[1,2,3,4,5] and flatten([])==[]
assert flatten([[],[1],[]])==[1]
""",
 """
def flatten(nested):
    out=[]
    for x in nested:
        if isinstance(x,list): out.extend(flatten(x))
        else: out.append(x)
    return out
"""),
("py-015", "function `binary_search(arr, target)` returning the index of target in a sorted list "
 "or -1.",
 """
assert binary_search([1,3,5,7,9],7)==3 and binary_search([1,3,5,7,9],4)==-1
assert binary_search([],1)==-1 and binary_search([2],2)==0
""",
 """
def binary_search(arr,target):
    lo,hi=0,len(arr)-1
    while lo<=hi:
        m=(lo+hi)//2
        if arr[m]==target: return m
        if arr[m]<target: lo=m+1
        else: hi=m-1
    return -1
"""),
("py-016", "function `word_freq(text, n)` returning the n most frequent lowercase words as "
 "(word, count) tuples sorted by count descending then alphabetically. Words are letter runs.",
 """
assert word_freq('the cat the dog THE bird cat',2)==[('the',3),('cat',2)]
assert word_freq('b a b a c',3)==[('a',2),('b',2),('c',1)]
""",
 """
import re
from collections import Counter
def word_freq(text,n):
    c=Counter(re.findall(r'[a-z]+',text.lower()))
    return sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))[:n]
"""),
("py-017", "function `dedupe(items)` removing duplicates while preserving first-appearance order. "
 "Must work with unhashable items too.",
 """
assert dedupe([3,1,3,2,1])==[3,1,2]
assert dedupe([{'a':1},{'a':1},{'b':2}])==[{'a':1},{'b':2}]
assert dedupe([])==[]
""",
 """
def dedupe(items):
    out=[]
    for it in items:
        if it not in out: out.append(it)
    return out
"""),
("py-018", "function `transpose(matrix)` returning the transpose of a list of equal-length rows. "
 "Empty input returns [].",
 """
assert transpose([[1,2,3],[4,5,6]])==[[1,4],[2,5],[3,6]]
assert transpose([])==[] and transpose([[1]])==[[1]]
""",
 """
def transpose(matrix):
    return [list(r) for r in zip(*matrix)] if matrix else []
"""),
("py-019", "function `rotate(lst, k)` rotating a list right by k positions, handling k larger than "
 "the list and negative k. Return a new list.",
 """
assert rotate([1,2,3,4,5],2)==[4,5,1,2,3]
assert rotate([1,2,3],4)==[3,1,2] and rotate([1,2,3],-1)==[2,3,1]
assert rotate([],3)==[]
""",
 """
def rotate(lst,k):
    if not lst: return []
    k%=len(lst)
    return lst[-k:]+lst[:-k] if k else list(lst)
"""),
("py-020", "function `fib_memo(n)` returning the nth Fibonacci number (fib_memo(0)==0) using "
 "memoization so fib_memo(200) returns quickly.",
 """
assert fib_memo(0)==0 and fib_memo(1)==1 and fib_memo(10)==55
assert fib_memo(200)==280571172992510140037611932413038677189525
""",
 """
import functools
@functools.lru_cache(maxsize=None)
def fib_memo(n): return n if n<2 else fib_memo(n-1)+fib_memo(n-2)
"""),
("py-021", "function `primes_upto(n)` returning all primes <= n using a sieve.",
 """
assert primes_upto(10)==[2,3,5,7] and primes_upto(1)==[]
assert len(primes_upto(100))==25
""",
 """
def primes_upto(n):
    if n<2: return []
    s=[True]*(n+1); s[0]=s[1]=False
    for i in range(2,int(n**0.5)+1):
        if s[i]:
            for j in range(i*i,n+1,i): s[j]=False
    return [i for i,v in enumerate(s) if v]
"""),
("py-022", "function `parse_query(qs)` parsing a URL query string into a dict; repeated keys become "
 "a list; percent-encoding and '+' as space must be decoded.",
 """
assert parse_query('a=1&b=2')=={'a':'1','b':'2'}
assert parse_query('a=1&a=2')=={'a':['1','2']}
assert parse_query('q=hello+world%21')=={'q':'hello world!'}
assert parse_query('')=={}
""",
 """
from urllib.parse import parse_qs
def parse_query(qs):
    d=parse_qs(qs)
    return {k:(v[0] if len(v)==1 else v) for k,v in d.items()}
"""),
("py-023", "function `deep_get(obj, path, default=None)` reading a dotted path out of nested dicts "
 "and lists, returning default when any step is missing. List indices appear as digits.",
 """
o={'a':{'b':[{'c':7}]}}
assert deep_get(o,'a.b.0.c')==7
assert deep_get(o,'a.x.y','zz')=='zz'
assert deep_get(o,'a.b.9.c') is None
""",
 """
def deep_get(obj,path,default=None):
    cur=obj
    for p in path.split('.'):
        try:
            if isinstance(cur,list): cur=cur[int(p)]
            else: cur=cur[p]
        except Exception: return default
    return cur
"""),
("py-024", "function `human_bytes(n)` formatting a byte count using binary units B, KiB, MiB, GiB, "
 "TiB with one decimal place except plain bytes.",
 """
assert human_bytes(512)=='512 B'
assert human_bytes(2048)=='2.0 KiB'
assert human_bytes(1048576)=='1.0 MiB'
assert human_bytes(0)=='0 B'
""",
 """
def human_bytes(n):
    units=['B','KiB','MiB','GiB','TiB']; f=float(n); i=0
    while f>=1024 and i<len(units)-1: f/=1024; i+=1
    return f'{int(f)} {units[i]}' if i==0 else f'{f:.1f} {units[i]}'
"""),
("py-025", "function `parse_duration(s)` turning strings like '1h30m', '45s', '2d' into total "
 "seconds as an int. Raise ValueError on unparseable input.",
 """
assert parse_duration('45s')==45 and parse_duration('1h30m')==5400
assert parse_duration('2d')==172800
try: parse_duration('abc'); assert False
except ValueError: pass
""",
 """
import re
def parse_duration(s):
    mult={'s':1,'m':60,'h':3600,'d':86400}
    parts=re.findall(r'(\\d+)([smhd])',s)
    if not parts or ''.join(a+b for a,b in parts)!=s: raise ValueError('bad duration')
    return sum(int(a)*mult[b] for a,b in parts)
"""),
("py-026", "generator `sliding_window(it, n)` yielding tuples of the last n items as it advances. "
 "Yields nothing if the iterable is shorter than n.",
 """
assert list(sliding_window([1,2,3,4],2))==[(1,2),(2,3),(3,4)]
assert list(sliding_window([1],3))==[]
assert list(sliding_window(iter([1,2,3]),3))==[(1,2,3)]
""",
 """
from collections import deque
def sliding_window(it,n):
    d=deque(maxlen=n)
    for x in it:
        d.append(x)
        if len(d)==n: yield tuple(d)
"""),
("py-027", "context manager class `Timer` with attribute `elapsed` set on exit, using a clock "
 "function injected as `__init__(self, clock)`.",
 """
seq=iter([10.0,12.5])
t=Timer(lambda: next(seq))
with t: pass
assert t.elapsed==2.5
""",
 """
class Timer:
    def __init__(self,clock): self.clock=clock; self.elapsed=None
    def __enter__(self): self.t0=self.clock(); return self
    def __exit__(self,*a): self.elapsed=self.clock()-self.t0; return False
"""),
("py-028", "function `safe_divide(a, b, default=None)` returning a/b, or default on division by "
 "zero, without raising.",
 """
assert safe_divide(6,3)==2 and safe_divide(1,0) is None
assert safe_divide(1,0,0)==0
""",
 """
def safe_divide(a,b,default=None):
    try: return a/b
    except ZeroDivisionError: return default
"""),
("py-029", "function `levenshtein(a, b)` returning the edit distance between two strings.",
 """
assert levenshtein('kitten','sitting')==3
assert levenshtein('','abc')==3 and levenshtein('same','same')==0
""",
 """
def levenshtein(a,b):
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1):
            cur.append(min(prev[j]+1,cur[j-1]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]
"""),
("py-030", "function `run_length_encode(s)` returning a list of (char, count) pairs, and "
 "`run_length_decode(pairs)` inverting it.",
 """
assert run_length_encode('aaabbc')==[('a',3),('b',2),('c',1)]
assert run_length_decode([('a',3),('b',2)])=='aaabb'
assert run_length_encode('')==[]
""",
 """
def run_length_encode(s):
    out=[]
    for ch in s:
        if out and out[-1][0]==ch: out[-1]=(ch,out[-1][1]+1)
        else: out.append((ch,1))
    return out
def run_length_decode(pairs): return ''.join(c*n for c,n in pairs)
"""),
("py-031", "function `merge_sorted(a, b)` merging two sorted lists into one sorted list without "
 "using sorted() or .sort().",
 """
assert merge_sorted([1,3,5],[2,4])==[1,2,3,4,5]
assert merge_sorted([],[1])==[1] and merge_sorted([],[])==[]
""",
 """
def merge_sorted(a,b):
    i=j=0; out=[]
    while i<len(a) and j<len(b):
        if a[i]<=b[j]: out.append(a[i]); i+=1
        else: out.append(b[j]); j+=1
    out.extend(a[i:]); out.extend(b[j:]); return out
"""),
("py-032", "function `find_duplicates(items)` returning the items appearing more than once, in "
 "order of first appearance, each listed once.",
 """
assert find_duplicates([1,2,3,2,1,1])==[1,2]
assert find_duplicates([1,2,3])==[]
""",
 """
from collections import Counter
def find_duplicates(items):
    c=Counter(items); seen=set(); out=[]
    for x in items:
        if c[x]>1 and x not in seen: seen.add(x); out.append(x)
    return out
"""),
("py-033", "function `matrix_spiral(m)` returning the elements of a rectangular matrix in "
 "clockwise spiral order starting top-left.",
 """
assert matrix_spiral([[1,2,3],[4,5,6],[7,8,9]])==[1,2,3,6,9,8,7,4,5]
assert matrix_spiral([[1,2]])==[1,2] and matrix_spiral([])==[]
""",
 """
def matrix_spiral(m):
    m=[list(r) for r in m]; out=[]
    while m:
        out+=m.pop(0)
        m=[list(r) for r in zip(*m)][::-1]
    return out
"""),
("py-034", "function `validate_ipv4(s)` returning True only for a dotted quad with each octet "
 "0-255 and no leading zeros.",
 """
assert validate_ipv4('192.168.0.1') is True
assert validate_ipv4('256.1.1.1') is False
assert validate_ipv4('01.1.1.1') is False
assert validate_ipv4('1.1.1') is False
""",
 """
def validate_ipv4(s):
    parts=s.split('.')
    if len(parts)!=4: return False
    for p in parts:
        if not p.isdigit() or (len(p)>1 and p[0]=='0'): return False
        if not 0<=int(p)<=255: return False
    return True
"""),
("py-035", "function `count_paths(m, n)` returning the number of unique paths across an m x n grid "
 "moving only right or down.",
 """
assert count_paths(3,7)==28 and count_paths(1,1)==1 and count_paths(2,2)==2
""",
 """
import math
def count_paths(m,n): return math.comb(m+n-2,m-1)
"""),
("py-036", "function `apply_patch(text, replacements)` applying a list of (old, new) string "
 "replacements left to right, returning the result. Raise KeyError if an old string is absent.",
 """
assert apply_patch('hello world',[('world','there')])=='hello there'
try: apply_patch('abc',[('zz','y')]); assert False
except KeyError: pass
""",
 """
def apply_patch(text,replacements):
    for old,new in replacements:
        if old not in text: raise KeyError(old)
        text=text.replace(old,new)
    return text
"""),
("py-037", "function `partition(items, pred)` returning a tuple (matching, not_matching) "
 "preserving order.",
 """
assert partition([1,2,3,4],lambda x:x%2==0)==([2,4],[1,3])
assert partition([],lambda x:True)==([],[])
""",
 """
def partition(items,pred):
    a=[];b=[]
    for x in items: (a if pred(x) else b).append(x)
    return a,b
"""),
("py-038", "function `natural_sort(names)` sorting strings so embedded numbers compare "
 "numerically ('f10' after 'f9').",
 """
assert natural_sort(['f10','f9','f1'])==['f1','f9','f10']
assert natural_sort(['a','b'])==['a','b']
""",
 """
import re
def natural_sort(names):
    def key(s): return [int(t) if t.isdigit() else t for t in re.split(r'(\\d+)',s)]
    return sorted(names,key=key)
"""),
("py-039", "function `moving_average(xs, n)` returning the list of averages over each consecutive "
 "window of n values. Returns [] if shorter than n.",
 """
assert moving_average([1,2,3,4],2)==[1.5,2.5,3.5]
assert moving_average([1],3)==[]
""",
 """
def moving_average(xs,n):
    return [sum(xs[i:i+n])/n for i in range(len(xs)-n+1)] if len(xs)>=n else []
"""),
("py-040", "function `invert_dict(d)` mapping each value back to the list of keys that had it, "
 "keys sorted.",
 """
assert invert_dict({'a':1,'b':2,'c':1})=={1:['a','c'],2:['b']}
assert invert_dict({})=={}
""",
 """
def invert_dict(d):
    out={}
    for k,v in d.items(): out.setdefault(v,[]).append(k)
    return {k:sorted(v) for k,v in out.items()}
"""),
("py-041", "class `EventBus` with `on(event, fn)`, `off(event, fn)` and `emit(event, *args)` "
 "calling handlers in registration order. emit on an unknown event is a no-op.",
 """
b=EventBus(); seen=[]
f=lambda x: seen.append(('f',x)); g=lambda x: seen.append(('g',x))
b.on('e',f); b.on('e',g); b.emit('e',1)
assert seen==[('f',1),('g',1)]
b.off('e',f); b.emit('e',2)
assert seen[-1]==('g',2) and len(seen)==3
b.emit('nope',9)
""",
 """
class EventBus:
    def __init__(self): self.h={}
    def on(self,event,fn): self.h.setdefault(event,[]).append(fn)
    def off(self,event,fn):
        if event in self.h and fn in self.h[event]: self.h[event].remove(fn)
    def emit(self,event,*args):
        for fn in list(self.h.get(event,[])): fn(*args)
"""),
("py-042", "function `parse_ini(text)` parsing INI-style text into a dict of section -> dict of "
 "key/value. Lines starting with ';' or '#' are comments.",
 """
t='[a]\\nx = 1\\n; c\\n[b]\\ny=2\\n'
assert parse_ini(t)=={'a':{'x':'1'},'b':{'y':'2'}}
assert parse_ini('')=={}
""",
 """
def parse_ini(text):
    out={}; cur=None
    for line in text.splitlines():
        s=line.strip()
        if not s or s[0] in ';#': continue
        if s.startswith('[') and s.endswith(']'): cur=s[1:-1]; out.setdefault(cur,{})
        elif '=' in s and cur is not None:
            k,v=s.split('=',1); out[cur][k.strip()]=v.strip()
    return out
"""),
("py-043", "function `topk(items, k)` returning the k largest values in descending order without "
 "fully sorting the input (use heapq).",
 """
assert topk([5,1,9,3,7],3)==[9,7,5]
assert topk([1],5)==[1] and topk([],3)==[]
""",
 """
import heapq
def topk(items,k): return heapq.nlargest(k,items)
"""),
("py-044", "function `strip_comments(code)` removing Python '#' comments from each line but not "
 "those inside single or double quoted strings.",
 """
assert strip_comments('x=1 # hi')=='x=1 '
assert strip_comments('s = "a # b"')=='s = "a # b"'
assert strip_comments('# all')==''
""",
 """
def strip_comments(code):
    out=[]
    for line in code.split('\\n'):
        q=None; res=''
        for i,ch in enumerate(line):
            if q:
                res+=ch
                if ch==q: q=None
            elif ch in '"\\'':
                q=ch; res+=ch
            elif ch=='#': break
            else: res+=ch
        out.append(res)
    return '\\n'.join(out)
"""),
("py-045", "function `batched_dict(d, n)` splitting a dict into a list of dicts of at most n items "
 "each, preserving insertion order.",
 """
r=batched_dict({'a':1,'b':2,'c':3},2)
assert r==[{'a':1,'b':2},{'c':3}]
assert batched_dict({},2)==[]
""",
 """
def batched_dict(d,n):
    items=list(d.items())
    return [dict(items[i:i+n]) for i in range(0,len(items),n)]
"""),
("py-046", "function `is_anagram(a, b)` returning True if two strings are anagrams ignoring case "
 "and non-letter characters.",
 """
assert is_anagram('Listen','Silent') is True
assert is_anagram('a gentleman','elegant man') is True
assert is_anagram('abc','abd') is False
""",
 """
def is_anagram(a,b):
    f=lambda s: sorted(c for c in s.lower() if c.isalpha())
    return f(a)==f(b)
"""),
("py-047", "function `coin_change(coins, amount)` returning the fewest coins summing to amount, "
 "or -1 if impossible.",
 """
assert coin_change([1,5,10],12)==3
assert coin_change([2],3)==-1 and coin_change([1],0)==0
""",
 """
def coin_change(coins,amount):
    INF=float('inf'); dp=[0]+[INF]*amount
    for a in range(1,amount+1):
        for c in coins:
            if c<=a: dp[a]=min(dp[a],dp[a-c]+1)
    return -1 if dp[amount]==INF else dp[amount]
"""),
("py-048", "function `mask_secrets(text)` replacing the value of any key that looks like a secret "
 "(containing 'password', 'token' or 'key', case-insensitive) in `k=v` pairs with '***', leaving "
 "other pairs alone.",
 """
assert mask_secrets('user=ann password=hunter2')=='user=ann password=***'
assert mask_secrets('API_KEY=abc')=='API_KEY=***'
assert mask_secrets('host=db')=='host=db'
""",
 """
import re
def mask_secrets(text):
    return re.sub(r'(\\w*(?:password|token|key)\\w*)\\s*=\\s*\\S+',
                  lambda m: m.group(1)+'=***', text, flags=re.I)
"""),
("py-049", "function `interval_overlap(a, b)` returning the overlapping [start, end] of two "
 "intervals or None when they do not overlap. Touching endpoints count as overlapping.",
 """
assert interval_overlap([1,5],[3,8])==[3,5]
assert interval_overlap([1,2],[2,3])==[2,2]
assert interval_overlap([1,2],[5,6]) is None
""",
 """
def interval_overlap(a,b):
    s=max(a[0],b[0]); e=min(a[1],b[1])
    return [s,e] if s<=e else None
"""),
("py-050", "function `stable_hash(obj)` returning the same hex string for equal nested "
 "dict/list/str/int structures regardless of dict key insertion order.",
 """
h1=stable_hash({'a':1,'b':[1,2]}); h2=stable_hash({'b':[1,2],'a':1})
assert h1==h2 and isinstance(h1,str)
assert stable_hash({'a':1})!=stable_hash({'a':2})
""",
 """
import hashlib,json
def stable_hash(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
"""),
]

PROMPT = ("Write a Python {}\n\nOutput only the code, no explanation.")


def tasks():
    return [(tid, "Write a Python " + spec + "\n\nOutput only the code, no explanation.", tests)
            for tid, spec, tests, _ref in T]


# Runs each case from a FILE via subprocess, exactly as the real grader does.
# exec() would break inspect.getsource(), which some tasks rely on.
VERIFY_DRIVER = """
import json, subprocess
bad = []
for tid, ref, tests in CASES:
    p = "/tmp/%s.py" % tid
    open(p, "w").write(ref + "\\n\\n" + tests)
    r = subprocess.run(["python", p], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()
        bad.append((tid, tail[-1][:120] if tail else "nonzero exit"))
print(json.dumps(bad))
"""


def verify_source():
    cases = [(tid, ref, tests) for tid, _s, tests, ref in T]
    return "CASES = " + repr(cases) + "\n" + VERIFY_DRIVER


if __name__ == "__main__":
    print(f"python tasks: {len(T)}")
    open("/tmp/pyverify.py", "w").write(verify_source())
    print("wrote /tmp/pyverify.py")
