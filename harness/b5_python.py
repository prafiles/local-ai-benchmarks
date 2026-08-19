#!/usr/bin/env python3
"""Python, hard tier -- 30 tasks. Each ships a reference solution.

Every task here is chosen so that the obvious answer is wrong. Three levers do
that work, and each task uses at least one:

  * SPEC-EXACT.  The rules come from a real specification (semver precedence,
    gitignore glob semantics, RFC 7233 ranges, unified diff format, banker's
    rounding). These cannot be answered from a memorised LeetCode solution
    because they are not LeetCode problems; they are things with a written
    definition that the answer either matches or does not.

  * TRAP.  The prompt reads like a famous problem and differs in one clause
    (transpositions in edit distance; half-open intervals; duplicates in a
    rotated array; stable ties in top-k). A recalled solution scores zero.

  * SCALE-GATED.  The tests run at a size where the quadratic answer cannot
    finish inside the grader's 90s timeout. Complexity is enforced by the clock,
    not by grepping the source for a banned method, which the b3 tier did and
    which a model can defeat by spelling the same loop differently.

The tests are adversarial on purpose: they cover the edge cases the spec implies
but does not enumerate. A solution that handles the happy path and nothing else
fails, which is the entire point -- on the b3 tier the same models score 95%.
"""

# (id, spec, tests, reference)
T = [

("hpy-001",
 "function `cmp_semver(a, b)` comparing two SemVer 2.0.0 version strings, returning -1, 0 or 1. "
 "Precedence is by major, minor, patch numerically; a version WITH a pre-release sorts BEFORE the "
 "same version without one; pre-release identifiers are compared dot-separated left to right, "
 "numeric identifiers compare numerically and sort before alphanumeric ones, a longer identifier "
 "list wins when all preceding identifiers are equal; build metadata after `+` is ignored entirely.",
 """
c=cmp_semver
assert c('1.0.0','1.0.1')==-1 and c('1.0.1','1.0.0')==1 and c('1.0.0','1.0.0')==0
assert c('1.0.0-alpha','1.0.0')==-1, 'prerelease sorts before release'
assert c('1.0.0','1.0.0+build.9')==0, 'build metadata ignored'
assert c('1.0.0-alpha+a','1.0.0-alpha+b')==0
assert c('1.0.0-alpha','1.0.0-alpha.1')==-1, 'longer identifier list wins'
assert c('1.0.0-alpha.1','1.0.0-alpha.beta')==-1, 'numeric sorts before alphanumeric'
assert c('1.0.0-alpha.beta','1.0.0-beta')==-1
assert c('1.0.0-beta','1.0.0-beta.2')==-1
assert c('1.0.0-beta.2','1.0.0-beta.11')==-1, 'numeric identifiers compare numerically'
assert c('1.0.0-beta.11','1.0.0-rc.1')==-1
assert c('1.0.0-rc.1','1.0.0')==-1
assert c('2.0.0','10.0.0')==-1 and c('1.2.0','1.10.0')==-1
assert c('1.0.0-1','1.0.0-2')==-1 and c('1.0.0-2','1.0.0-10')==-1
""",
 """
def _pre(p):
    out=[]
    for x in p.split('.'):
        out.append((0,int(x),'') if x.isdigit() else (1,0,x))
    return out
def cmp_semver(a,b):
    def parse(v):
        v=v.split('+',1)[0]
        core,_,pre=v.partition('-')
        return [int(x) for x in core.split('.')], (_pre(pre) if pre else None)
    ca,pa=parse(a); cb,pb=parse(b)
    if ca!=cb: return -1 if ca<cb else 1
    if pa is None and pb is None: return 0
    if pa is None: return 1
    if pb is None: return -1
    if pa!=pb: return -1 if pa<pb else 1
    return 0
"""),

("hpy-002",
 "function `gitignore_match(pattern, path)` returning True when a .gitignore pattern matches a "
 "path. `path` is slash-separated and never starts with a slash. Rules: a pattern with no slash "
 "(other than a trailing one) matches at any depth; a pattern containing a slash anywhere except "
 "the end is anchored at the root; a leading slash anchors at the root; a trailing slash means the "
 "pattern only matches a directory, and for this function a path is a directory when it ends with "
 "a slash; `*` never matches a slash; `?` matches one non-slash character; `**/` matches zero or "
 "more leading directories; `/**` at the end matches everything inside; `[abc]` is a character class.",
 """
m=gitignore_match
assert m('*.log','a.log') and m('*.log','deep/nested/a.log'), 'unanchored matches at depth'
assert not m('*.log','a.log.txt')
assert m('build/','build/') and not m('build/','build'), 'trailing slash is dir-only'
assert m('build/','src/build/')
assert m('doc/frotz','doc/frotz') and not m('doc/frotz','a/doc/frotz'), 'inner slash anchors'
assert m('/top','top') and not m('/top','a/top')
assert m('**/foo','foo') and m('**/foo','a/b/foo')
assert m('a/**','a/b') and m('a/**','a/b/c') and not m('a/**','a')
assert m('a/*.c','a/x.c') and not m('a/*.c','a/b/x.c'), 'star does not cross slash'
assert m('?.txt','a.txt') and not m('?.txt','ab.txt') and not m('?.txt','a/txt')
assert m('[abc].py','b.py') and not m('[abc].py','d.py')
assert m('*.log','x/y/z/deep.log')
""",
 """
import re
def _seg(p):
    out=''
    i=0
    while i<len(p):
        ch=p[i]
        if ch=='*': out+='[^/]*'
        elif ch=='?': out+='[^/]'
        elif ch=='[':
            j=p.index(']',i)
            out+=p[i:j+1]; i=j
        else: out+=re.escape(ch)
        i+=1
    return out
def gitignore_match(pattern,path):
    dironly=pattern.endswith('/')
    p=pattern[:-1] if dironly else pattern
    isdir=path.endswith('/')
    if dironly and not isdir: return False
    target=path[:-1] if isdir else path
    anchored=p.startswith('/') or '/' in p
    p=p.lstrip('/')
    if p.startswith('**/'):
        p=p[3:]; anchored=False
    tail_all=p.endswith('/**')
    if tail_all: p=p[:-3]
    rx=''.join(_seg(s) if s!='**' else '.*' for s in [p]) if '/' not in p else \
       '/'.join(_seg(s) for s in p.split('/'))
    if tail_all: rx+='/.+'
    rx=('' if anchored else '(?:.*/)?')+rx
    return re.fullmatch(rx,target) is not None
"""),

("hpy-003",
 "function `parse_range(header, size)` implementing the RFC 7233 Range header for `bytes`. "
 "Return a list of (start, end) inclusive byte offsets, or None if the header is unsatisfiable or "
 "malformed. `bytes=0-499` is the first 500 bytes; `bytes=500-` runs to the end; `bytes=-500` is "
 "the LAST 500 bytes; an end past the last byte is clamped; a suffix length larger than the "
 "resource yields the whole resource; multiple comma-separated ranges are all returned in the "
 "order given; a range whose start is at or past `size` is unsatisfiable; if every range in the "
 "set is unsatisfiable return None, but a set with at least one satisfiable range drops the bad ones.",
 """
p=parse_range
assert p('bytes=0-499',10000)==[(0,499)]
assert p('bytes=500-',1000)==[(500,999)]
assert p('bytes=-500',1000)==[(500,999)], 'suffix form is the LAST n bytes'
assert p('bytes=-5000',1000)==[(0,999)], 'oversize suffix clamps to whole resource'
assert p('bytes=0-99999',1000)==[(0,999)], 'end clamps'
assert p('bytes=0-0,-1',1000)==[(0,0),(999,999)]
assert p('bytes=1000-',1000) is None, 'start at size is unsatisfiable'
assert p('bytes=2000-3000',1000) is None
assert p('bytes=0-1,5000-6000',1000)==[(0,1)], 'partial set drops bad ranges'
assert p('items=0-499',1000) is None and p('bytes=abc',1000) is None
assert p('bytes=-0',1000) is None, 'zero-length suffix is unsatisfiable'
assert p('bytes=5-3',1000) is None
assert p('bytes=0-499, 900-',1000)==[(0,499),(900,999)]
""",
 """
def parse_range(header,size):
    if not isinstance(header,str) or not header.startswith('bytes='): return None
    out=[]; any_bad=False
    for part in header[6:].split(','):
        s=part.strip()
        if '-' not in s: return None
        a,_,b=s.partition('-')
        a=a.strip(); b=b.strip()
        if a=='':
            if not b.isdigit(): return None
            n=int(b)
            if n==0: any_bad=True; continue
            out.append((max(0,size-n),size-1))
        else:
            if not a.isdigit(): return None
            st=int(a)
            if b=='': en=size-1
            elif b.isdigit(): en=min(int(b),size-1)
            else: return None
            if st>=size or st>en: any_bad=True; continue
            out.append((st,en))
    if not out: return None
    return out
"""),

("hpy-004",
 "function `round_money(amount, places)` rounding a `decimal.Decimal` to `places` decimal digits "
 "using banker's rounding (round half to even), returning a Decimal quantized to exactly that many "
 "places. It must not go through float at any point.",
 """
from decimal import Decimal as D
r=round_money
assert r(D('2.5'),0)==D('2') and r(D('3.5'),0)==D('4'), 'half to EVEN, not half up'
assert r(D('-2.5'),0)==D('-2') and r(D('-3.5'),0)==D('-4')
assert r(D('2.675'),2)==D('2.68'), 'exact decimal, not the float 2.67'
assert r(D('1.005'),2)==D('1.00'), 'half to even: 0 is even'
assert r(D('1.015'),2)==D('1.02')
assert str(r(D('1'),2))=='1.00', 'quantized to exactly places digits'
assert str(r(D('1.0000'),2))=='1.00'
assert r(D('0.125'),2)==D('0.12') and r(D('0.135'),2)==D('0.14')
assert r(D('1234567890123456789.5'),0)==D('1234567890123456790')
""",
 """
from decimal import Decimal, ROUND_HALF_EVEN, getcontext
def round_money(amount,places):
    getcontext().prec=60
    q=Decimal(1).scaleb(-places)
    return amount.quantize(q,rounding=ROUND_HALF_EVEN)
"""),

("hpy-005",
 "function `unified_diff(a, b, context=3)` taking two lists of lines and returning a list of "
 "unified-diff output lines with no trailing newlines. Use a longest-common-subsequence diff. "
 "Each hunk header is `@@ -<astart>,<alen> +<bstart>,<blen> @@` with 1-based starts, body lines are "
 "prefixed with a space, `-` or `+`, hunks include up to `context` unchanged lines on each side and "
 "overlapping hunks are merged into one. Return an empty list when the inputs are identical. "
 "Emit no `---`/`+++` file header.",
 """
u=unified_diff
assert u(['a','b'],['a','b'])==[]
r=u(['a','b','c'],['a','x','c'],1)
assert r==['@@ -1,3 +1,3 @@',' a','-b','+x',' c'], r
r=u(['a'],['a','b'],3)
assert r==['@@ -1,1 +1,2 @@',' a','+b'], r
r=u(['x'],[],3)
assert r==['@@ -1,1 +0,0 @@','-x'], r
a=[str(i) for i in range(1,21)]
b=list(a); b[4]='five'; b[15]='sixteen'
r=u(a,b,1)
assert r.count('@@ -')==0 and sum(1 for l in r if l.startswith('@@'))==2, r
r2=u(a,b,10)
assert sum(1 for l in r2 if l.startswith('@@'))==1, 'overlapping hunks must merge'
assert [l for l in r2 if l[0] in '-+']==['-5','+five','-16','+sixteen']
r3=u([],['n'],3); assert r3==['@@ -0,0 +1,1 @@','+n'], r3
""",
 """
def _lcs(a,b):
    n,m=len(a),len(b)
    dp=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n-1,-1,-1):
        for j in range(m-1,-1,-1):
            dp[i][j]=dp[i+1][j+1]+1 if a[i]==b[j] else max(dp[i+1][j],dp[i][j+1])
    ops=[]; i=j=0
    while i<n and j<m:
        if a[i]==b[j]: ops.append((' ',a[i])); i+=1; j+=1
        elif dp[i+1][j]>=dp[i][j+1]: ops.append(('-',a[i])); i+=1
        else: ops.append(('+',b[j])); j+=1
    while i<n: ops.append(('-',a[i])); i+=1
    while j<m: ops.append(('+',b[j])); j+=1
    return ops
def unified_diff(a,b,context=3):
    ops=_lcs(a,b)
    if not any(t!=' ' for t,_ in ops): return []
    keep=[False]*len(ops)
    for k,(t,_) in enumerate(ops):
        if t!=' ':
            for x in range(max(0,k-context),min(len(ops),k+context+1)): keep[x]=True
    out=[]; k=0; ai=bi=1
    idx=[]
    ca=cb=1
    for t,_ in ops:
        idx.append((ca,cb))
        if t!='+': ca+=1
        if t!='-': cb+=1
    while k<len(ops):
        if not keep[k]:
            k+=1; continue
        s=k
        while k<len(ops) and keep[k]: k+=1
        seg=ops[s:k]
        al=sum(1 for t,_ in seg if t!='+')
        bl=sum(1 for t,_ in seg if t!='-')
        ai,bi=idx[s]
        out.append('@@ -%d,%d +%d,%d @@'%(ai if al else ai-1,al,bi if bl else bi-1,bl))
        out.extend(t+v for t,v in seg)
    return out
"""),

("hpy-006",
 "function `damerau(a, b)` returning the unrestricted Damerau-Levenshtein edit distance -- "
 "insertion, deletion, substitution AND transposition of two ADJACENT characters, each cost 1, "
 "where a transposed pair may itself have been edited (the unrestricted, not the optimal-string-"
 "alignment, variant).",
 """
d=damerau
assert d('','')==0 and d('a','')==1 and d('','ab')==2
assert d('ca','abc')==2, 'unrestricted variant: OSA would say 3'
assert d('ab','ba')==1
assert d('kitten','sitting')==3
assert d('sunday','saturday')==3
assert d('teh','the')==1
assert d('abcdef','abcdef')==0
assert d('a cat','an abct')==3, 'the canonical case: the RESTRICTED variant says 4'
assert d('xy','yx')==1 and d('xyz','zyx')==2
""",
 """
def damerau(a,b):
    da={}
    la,lb=len(a),len(b)
    maxd=la+lb
    d=[[0]*(lb+2) for _ in range(la+2)]
    d[0][0]=maxd
    for i in range(0,la+1):
        d[i+1][0]=maxd; d[i+1][1]=i
    for j in range(0,lb+1):
        d[0][j+1]=maxd; d[1][j+1]=j
    for i in range(1,la+1):
        db=0
        for j in range(1,lb+1):
            k=da.get(b[j-1],0); l=db
            if a[i-1]==b[j-1]:
                cost=0; db=j
            else:
                cost=1
            d[i+1][j+1]=min(d[i][j]+cost, d[i+1][j]+1, d[i][j+1]+1,
                            d[k][l]+(i-k-1)+1+(j-l-1))
        da[a[i-1]]=i
    return d[la+1][lb+1]
"""),

("hpy-007",
 "class `LFUCache` with `__init__(self, capacity)`, `get(self, key)` returning -1 when absent and "
 "`put(self, key, value)`. Evict the least frequently used key; break frequency ties by evicting "
 "the least recently used among them. Both operations must be O(1) -- the tests run 200000 "
 "operations and a scan-for-minimum implementation will not finish in time. A capacity of 0 accepts nothing.",
 """
c=LFUCache(2)
c.put(1,1); c.put(2,2)
assert c.get(1)==1
c.put(3,3)
assert c.get(2)==-1, 'key 2 had freq 1, key 1 had freq 2'
assert c.get(3)==3
c.put(4,4)
assert c.get(1)==-1, 'freq tie between 1 and 3 broken by recency'
assert c.get(3)==3 and c.get(4)==4
z=LFUCache(0); z.put(1,1); assert z.get(1)==-1
c2=LFUCache(2); c2.put(1,1); c2.put(1,9)
assert c2.get(1)==9, 'overwrite updates value'
import time
big=LFUCache(1000)
t0=time.time()
for i in range(200000):
    big.put(i%1500,i)
    big.get(i%1500)
assert time.time()-t0 < 20, 'must be O(1) per operation'
""",
 """
class LFUCache:
    def __init__(self,capacity):
        self.cap=capacity
        self.v={}; self.f={}
        self.buckets={}
        self.minf=0
    def _touch(self,key):
        fr=self.f[key]
        b=self.buckets[fr]; del b[key]
        if not b:
            del self.buckets[fr]
            if self.minf==fr: self.minf=fr+1
        self.f[key]=fr+1
        self.buckets.setdefault(fr+1,{})[key]=None
    def get(self,key):
        if key not in self.v: return -1
        self._touch(key)
        return self.v[key]
    def put(self,key,value):
        if self.cap<=0: return
        if key in self.v:
            self.v[key]=value; self._touch(key); return
        if len(self.v)>=self.cap:
            b=self.buckets[self.minf]
            ev=next(iter(b)); del b[ev]
            if not b: del self.buckets[self.minf]
            del self.v[ev]; del self.f[ev]
        self.v[key]=value; self.f[key]=1
        self.buckets.setdefault(1,{})[key]=None
        self.minf=1
"""),

("hpy-008",
 "function `schedule(jobs)` solving weighted interval scheduling: `jobs` is a list of "
 "(start, end, weight) with half-open intervals, so a job ending at t does not conflict with one "
 "starting at t. Return the maximum total weight of a non-overlapping subset. The tests include "
 "100000 jobs, so an O(n^2) inner scan will time out -- sort and binary-search.",
 """
s=schedule
assert s([])==0
assert s([(0,1,5)])==5
assert s([(0,10,1),(0,3,2),(3,6,2),(6,10,2)])==6
assert s([(1,3,50),(2,5,20),(4,6,30)])==80, 'half-open: 3 and 4 do not conflict'
assert s([(0,5,10),(5,10,10)])==20, 'touching intervals do not conflict'
assert s([(0,5,10),(4,10,10)])==10
assert s([(0,1,-5),(1,2,3)])==3, 'a negative-weight job is simply not taken'
import random,time
random.seed(7)
jobs=[]
for _ in range(100000):
    a=random.randint(0,10**6); jobs.append((a,a+random.randint(1,50),random.randint(1,100)))
t0=time.time(); r=s(jobs); assert time.time()-t0<25, 'needs O(n log n)'
assert isinstance(r,int) and r>0
""",
 """
import bisect
def schedule(jobs):
    if not jobs: return 0
    js=sorted(jobs,key=lambda x:x[1])
    ends=[j[1] for j in js]
    dp=[0]*(len(js)+1)
    for i,(s,e,w) in enumerate(js):
        k=bisect.bisect_right(ends,s,0,i)
        dp[i+1]=max(dp[i],dp[k]+w)
    return dp[-1]
"""),

("hpy-009",
 "function `lis_length(a)` returning the length of the longest STRICTLY increasing subsequence. "
 "The tests run 200000 elements, so the O(n^2) dynamic program will time out.",
 """
l=lis_length
assert l([])==0 and l([5])==1
assert l([10,9,2,5,3,7,101,18])==4
assert l([7,7,7,7])==1, 'strictly increasing'
assert l([1,2,2,3])==3
assert l([3,2,1])==1
import random,time
random.seed(3)
a=[random.randint(0,10**9) for _ in range(200000)]
t0=time.time(); r=l(a); assert time.time()-t0<20, 'needs O(n log n)'
assert 1<r<len(a)
assert l(list(range(100000)))==100000
""",
 """
import bisect
def lis_length(a):
    tails=[]
    for x in a:
        i=bisect.bisect_left(tails,x)
        if i==len(tails): tails.append(x)
        else: tails[i]=x
    return len(tails)
"""),

("hpy-010",
 "function `topk(stream, k)` returning the k largest values from an iterable of (value, label) "
 "pairs, as a list ordered by value descending. Ties in value are broken by ARRIVAL ORDER: the "
 "item seen first ranks higher. It must hold at most k+1 items in memory at any time, so it cannot "
 "sort the input -- the tests pass a generator of 500000 items and assert peak memory stays flat.",
 """
t=topk
assert t([],3)==[]
assert t([(1,'a')],3)==[(1,'a')]
assert t([(3,'c'),(1,'a'),(2,'b')],2)==[(3,'c'),(2,'b')]
assert t([(5,'first'),(5,'second')],1)==[(5,'first')], 'ties break by arrival'
assert t([(5,'a'),(5,'b'),(5,'c')],2)==[(5,'a'),(5,'b')]
assert t([(1,'x')],0)==[]
def gen(n):
    import random
    random.seed(11)
    for i in range(n): yield (random.randint(0,10**6), i)
import tracemalloc
tracemalloc.start()
r=t(gen(500000),10)
peak=tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
assert len(r)==10 and r==sorted(r,key=lambda x:-x[0])
assert peak < 2_000_000, 'must not buffer the stream (peak %d bytes)'%peak
""",
 """
import heapq
def topk(stream,k):
    if k<=0: return []
    h=[]; n=0
    for v,lab in stream:
        heapq.heappush(h,(v,-n,lab)); n+=1
        if len(h)>k: heapq.heappop(h)
    out=sorted(h,key=lambda x:(-x[0],-x[1]))
    return [(v,lab) for v,_i,lab in out]
"""),
("hpy-011",
 "function `parse_duration(s)` parsing an ISO-8601 duration into a total number of seconds as a "
 "float, or raising ValueError if it is not a valid duration. The form is "
 "`PnYnMnDTnHnMnS`; a leading `-` negates the whole duration; the `M` before `T` is months and "
 "the one after is minutes; the seconds field may be fractional; any field may be omitted but at "
 "least one must be present; the `T` must be absent when no time fields follow. Use 365 days for a "
 "year and 30 days for a month.",
 """
p=parse_duration
D=86400.0
assert p('PT1S')==1.0 and p('PT1M')==60.0 and p('PT1H')==3600.0
assert p('P1D')==D and p('P1M')==30*D and p('P1Y')==365*D
assert p('P1MT1M')==30*D+60.0, 'M before T is months, after T is minutes'
assert p('PT0.5S')==0.5 and p('PT1.25S')==1.25
assert p('-PT1H')==-3600.0
assert p('P1Y2M3DT4H5M6S')==365*D+2*30*D+3*D+4*3600+5*60+6
assert p('PT36H')==36*3600.0, 'fields need not be normalised'
for bad in ['P','','PT','1D','P1D T1H','PT1D','P1S','PTS','X1D','P-1D','p1d']:
    try:
        p(bad); raise SystemExit('accepted invalid duration %r'%bad)
    except ValueError: pass
""",
 """
import re
_RX=re.compile(r'^(-)?P(?!$)(?:(\\d+(?:\\.\\d+)?)Y)?(?:(\\d+(?:\\.\\d+)?)M)?'
               r'(?:(\\d+(?:\\.\\d+)?)D)?(?:T(?!$)(?:(\\d+(?:\\.\\d+)?)H)?'
               r'(?:(\\d+(?:\\.\\d+)?)M)?(?:(\\d+(?:\\.\\d+)?)S)?)?$')
def parse_duration(s):
    if not isinstance(s,str): raise ValueError('not a string')
    m=_RX.match(s)
    if not m: raise ValueError('bad duration %r'%s)
    neg,y,mo,d,h,mi,sec=m.groups()
    if not any(g is not None for g in (y,mo,d,h,mi,sec)): raise ValueError('empty')
    if 'T' in s and not any(g is not None for g in (h,mi,sec)): raise ValueError('empty T')
    f=lambda x: float(x) if x is not None else 0.0
    tot=f(y)*365*86400+f(mo)*30*86400+f(d)*86400+f(h)*3600+f(mi)*60+f(sec)
    return -tot if neg else tot
"""),

("hpy-012",
 "function `next_fire(expr, after)` returning the next datetime strictly after `after` at which a "
 "5-field cron expression fires (minute hour day-of-month month day-of-week), with seconds and "
 "microseconds zero. Each field supports `*`, a number, `a-b`, `*/s`, `a-b/s` and comma-separated "
 "lists of those. Day-of-week is 0-6 with 0 = Sunday. The day rule is the standard one: when BOTH "
 "day-of-month and day-of-week are restricted (neither is `*`) the expression fires on a day "
 "matching EITHER field, but when only one is restricted only that one applies. Raise ValueError on "
 "a malformed expression.",
 """
from datetime import datetime as DT
n=next_fire
assert n('* * * * *', DT(2024,1,1,0,0))==DT(2024,1,1,0,1), 'strictly after'
assert n('0 * * * *', DT(2024,1,1,0,30))==DT(2024,1,1,1,0)
assert n('*/15 * * * *', DT(2024,1,1,0,0))==DT(2024,1,1,0,15)
assert n('0 0 1 * *', DT(2024,1,15,5,0))==DT(2024,2,1,0,0)
assert n('0 0 29 2 *', DT(2023,3,1,0,0))==DT(2024,2,29,0,0), 'must skip to a leap year'
assert n('0 0 * * 0', DT(2024,1,1,0,0))==DT(2024,1,7,0,0), '0 is Sunday'
assert n('0 0 13 * 5', DT(2024,1,1,0,0))==DT(2024,1,5,0,0), 'BOTH restricted: OR, so Friday the 5th'
assert n('0 0 13 * *', DT(2024,1,1,0,0))==DT(2024,1,13,0,0), 'only DOM restricted'
assert n('0 0 * * 5', DT(2024,1,1,0,0))==DT(2024,1,5,0,0), 'only DOW restricted'
assert n('30 9-17 * * 1-5', DT(2024,1,6,12,0))==DT(2024,1,8,9,30), 'Sat -> Mon'
assert n('0 0 1 1 *', DT(2024,6,1,0,0))==DT(2025,1,1,0,0)
assert n('0 0-4/2 * * *', DT(2024,1,1,0,10))==DT(2024,1,1,2,0)
for bad in ['* * * *','* * * * * *','60 * * * *','* 24 * * *','0 0 0 * *','0 0 * 13 *','0 0 * * 7','a * * * *','*/0 * * * *']:
    try:
        n(bad, DT(2024,1,1)); raise SystemExit('accepted invalid cron %r'%bad)
    except ValueError: pass
""",
 """
from datetime import datetime, timedelta
def _field(spec,lo,hi):
    out=set()
    for part in spec.split(','):
        if not part: raise ValueError('empty field part')
        step=1
        if '/' in part:
            part,_,st=part.partition('/')
            if not st.isdigit() or int(st)==0: raise ValueError('bad step')
            step=int(st)
        if part=='*': a,b=lo,hi
        elif '-' in part.lstrip('-'):
            x,_,y=part.partition('-')
            if not (x.isdigit() and y.isdigit()): raise ValueError('bad range')
            a,b=int(x),int(y)
        else:
            if not part.isdigit(): raise ValueError('bad value')
            a=b=int(part)
            if step!=1: b=hi
        if a<lo or b>hi or a>b: raise ValueError('out of range')
        out.update(range(a,b+1,step))
    if not out: raise ValueError('empty field')
    return out
def next_fire(expr,after):
    parts=expr.split()
    if len(parts)!=5: raise ValueError('need 5 fields')
    mins=_field(parts[0],0,59); hrs=_field(parts[1],0,23)
    doms=_field(parts[2],1,31); mons=_field(parts[3],1,12)
    dows=_field(parts[4],0,6)
    dom_r=parts[2]!='*'; dow_r=parts[4]!='*'
    t=after.replace(second=0,microsecond=0)+timedelta(minutes=1)
    limit=t+timedelta(days=366*8)
    while t<limit:
        if t.month not in mons:
            m=t.month+1; y=t.year
            if m>12: m=1; y+=1
            t=datetime(y,m,1); continue
        wd=(t.weekday()+1)%7
        if dom_r and dow_r: dayok = t.day in doms or wd in dows
        elif dom_r: dayok = t.day in doms
        elif dow_r: dayok = wd in dows
        else: dayok = True
        if not dayok:
            t=datetime(t.year,t.month,t.day)+timedelta(days=1); continue
        if t.hour not in hrs:
            t=datetime(t.year,t.month,t.day,t.hour)+timedelta(hours=1); continue
        if t.minute not in mins:
            t=t+timedelta(minutes=1); continue
        return t
    raise ValueError('no fire time')
"""),

("hpy-013",
 "function `wildcard_match(pattern, s)` returning True when the whole of `s` matches a glob "
 "pattern in which `*` matches any run of characters including empty and `?` matches exactly one "
 "character. No other metacharacters. It must run in time proportional to len(pattern)*len(s) at "
 "worst -- the tests include a 20000-character adversarial case on which naive backtracking "
 "recursion takes exponential time. Do not build a regex.",
 """
w=wildcard_match
assert w('','') and not w('','a') and w('*','') and w('*','anything')
assert w('a?c','abc') and not w('a?c','ac') and not w('a?c','abbc')
assert w('*a*b*','xxaybz') and not w('*a*b*','ba')
assert w('a*','a') and w('*a','a') and not w('a*b','a')
assert w('**','ab') and w('*?*','a') and not w('*?*','')
assert w('?*?','ab') and not w('?*?','a')
import re,time,sys
assert not re.search(r'\\bre\\.|regex|fnmatch', __import__('inspect').getsource(wildcard_match)), 'no regex'
n=20000
t0=time.time()
assert not w('a'*n+'*b', 'a'*n)
assert w('*'*500+'b', 'a'*n+'b')
assert not w(('a*'*400)+'c', 'a'*4000)
assert time.time()-t0 < 20, 'exponential backtracking'
""",
 """
def wildcard_match(pattern,s):
    i=j=0; star=-1; mark=0
    while i<len(s):
        if j<len(pattern) and (pattern[j]==s[i] or pattern[j]=='?'):
            i+=1; j+=1
        elif j<len(pattern) and pattern[j]=='*':
            star=j; mark=i; j+=1
        elif star>=0:
            j=star+1; mark+=1; i=mark
        else:
            return False
    while j<len(pattern) and pattern[j]=='*': j+=1
    return j==len(pattern)
"""),

("hpy-014",
 "function `evaluate(expr)` evaluating an arithmetic expression string and returning a number. "
 "Support integers and decimals, `+ - * / % **`, parentheses, and unary minus and plus. Precedence "
 "from loosest: `+ -`, then `* / %`, then `**`, then unary. `**` is RIGHT-associative and binds "
 "TIGHTER than a unary minus on its left, so `-2**2` is -4 and `2**3**2` is 512. `/` is true "
 "division. Raise ValueError on a malformed expression. Do not call eval or exec.",
 """
e=evaluate
import inspect
src=inspect.getsource(evaluate)
assert 'eval(' not in src and 'exec(' not in src, 'must not shell out to eval'
assert e('1+2*3')==7 and e('(1+2)*3')==9
assert e('2**3**2')==512, 'right-associative'
assert e('-2**2')==-4, 'unary minus is looser than **'
assert e('(-2)**2')==4
assert e('2**-1')==0.5
assert e('7/2')==3.5 and e('7%3')==1
assert e('--3')==3 and e('+-3')==-3
assert e('1.5*2')==3.0
assert e('10-2-3')==5, 'left-associative subtraction'
assert e('100/10/2')==5
assert e(' 1 + 2 ')==3
for bad in ['','1+','(1','1)','1++','*2','1 2','()','1+*2']:
    try:
        e(bad); raise SystemExit('accepted %r'%bad)
    except ValueError: pass
""",
 """
import re
_TOK=re.compile(r'\\s*(\\d+\\.\\d+|\\d+|\\*\\*|[-+*/%()])')
def _lex(s):
    out=[]; i=0
    while i<len(s):
        if s[i].isspace(): i+=1; continue
        m=_TOK.match(s,i)
        if not m: raise ValueError('bad char %r'%s[i])
        out.append(m.group(1)); i=m.end()
    return out
def evaluate(expr):
    toks=_lex(expr)
    pos=[0]
    def peek(): return toks[pos[0]] if pos[0]<len(toks) else None
    def eat(t=None):
        c=peek()
        if c is None or (t is not None and c!=t): raise ValueError('unexpected %r'%c)
        pos[0]+=1; return c
    def atom():
        c=peek()
        if c is None: raise ValueError('unexpected end')
        if c=='(':
            eat('('); v=addsub(); eat(')'); return v
        if c in ('-','+'):
            eat(); return -unary() if c=='-' else unary()
        if re.fullmatch(r'\\d+\\.\\d+|\\d+',c):
            eat(); return float(c) if '.' in c else int(c)
        raise ValueError('unexpected %r'%c)
    def power():
        base=atom()
        if peek()=='**':
            eat('**'); return base**unary()
        return base
    def unary():
        c=peek()
        if c in ('-','+'):
            eat(); v=unary(); return -v if c=='-' else v
        return power()
    def muldiv():
        v=unary()
        while peek() in ('*','/','%'):
            op=eat()
            r=unary()
            if op=='*': v=v*r
            elif op=='/':
                if r==0: raise ValueError('division by zero')
                v=v/r
            else:
                if r==0: raise ValueError('modulo by zero')
                v=v%r
        return v
    def addsub():
        v=muldiv()
        while peek() in ('+','-'):
            op=eat(); r=muldiv()
            v=v+r if op=='+' else v-r
        return v
    if not toks: raise ValueError('empty')
    v=addsub()
    if pos[0]!=len(toks): raise ValueError('trailing %r'%peek())
    return v
"""),

("hpy-015",
 "function `window_medians(a, k)` returning the median of every contiguous window of length k in "
 "`a`, as a list of floats. For an even k the median is the mean of the two middle values. Return "
 "an empty list when k is larger than the input. The tests run 200000 elements with k=1000, so "
 "re-sorting each window will time out.",
 """
w=window_medians
assert w([],3)==[] and w([1,2],3)==[]
assert w([1,3,-1,-3,5,3,6,7],3)==[1.0,-1.0,-1.0,3.0,5.0,6.0]
assert w([1,2,3,4],2)==[1.5,2.5,3.5], 'even k averages the two middles'
assert w([5],1)==[5.0]
assert w([2,2,2,2],2)==[2.0,2.0,2.0]
import random,time
random.seed(5)
a=[random.randint(0,10**6) for _ in range(200000)]
t0=time.time(); r=w(a,1000)
assert time.time()-t0<25, 'must not re-sort each window'
assert len(r)==len(a)-999
import statistics
for i in (0, 1234, len(r)-1):
    assert abs(r[i]-statistics.median(a[i:i+1000]))<1e-9, i
""",
 """
import heapq
def window_medians(a,k):
    n=len(a)
    if k<=0 or k>n: return []
    lo=[]; hi=[]; lazy={}
    losz=hisz=0
    def prune(h,sign):
        while h and lazy.get(sign*h[0],0)>0:
            lazy[sign*h[0]]-=1; heapq.heappop(h)
    out=[]
    for i,x in enumerate(a):
        if not lo or x<=-lo[0]: heapq.heappush(lo,-x); losz+=1
        else: heapq.heappush(hi,x); hisz+=1
        if i>=k:
            old=a[i-k]
            lazy[old]=lazy.get(old,0)+1
            if lo and old<=-lo[0]: losz-=1
            else: hisz-=1
        while losz>hisz+1:
            prune(lo,-1); heapq.heappush(hi,-heapq.heappop(lo)); losz-=1; hisz+=1
        while losz<hisz:
            prune(hi,1); heapq.heappush(lo,-heapq.heappop(hi)); hisz-=1; losz+=1
        prune(lo,-1); prune(hi,1)
        if i>=k-1:
            out.append(float(-lo[0]) if k%2 else (-lo[0]+hi[0])/2.0)
    return out
"""),
("hpy-016",
 "class `RollbackDSU` with `__init__(self, n)`, `find(self, x)`, `union(self, a, b)` returning "
 "True when it merged two distinct sets and False otherwise, `snapshot(self)` returning an opaque "
 "token, and `rollback(self, token)` undoing every union performed since that token was taken. "
 "Snapshots nest, and rolling back to an older token also undoes the newer ones. Union by size or "
 "rank is required; path compression is not allowed because it cannot be undone. `components(self)` "
 "returns the current number of disjoint sets.",
 """
d=RollbackDSU(6)
assert d.components()==6
assert d.union(0,1) is True and d.union(0,1) is False
assert d.find(0)==d.find(1) and d.find(0)!=d.find(2)
s=d.snapshot()
assert d.union(2,3) and d.union(0,2)
assert d.find(1)==d.find(3) and d.components()==3
d.rollback(s)
assert d.find(1)!=d.find(3), 'rollback did not undo'
assert d.find(0)==d.find(1), 'rollback undid too much'
assert d.components()==5
s1=d.snapshot(); d.union(2,3)
s2=d.snapshot(); d.union(4,5)
d.rollback(s1)
assert d.components()==5 and d.find(4)!=d.find(5) and d.find(2)!=d.find(3), 'nested rollback'
import random,time
random.seed(9)
big=RollbackDSU(200000)
t0=time.time()
for _ in range(200000):
    big.union(random.randrange(200000),random.randrange(200000))
tok=big.snapshot()
for _ in range(100000):
    big.union(random.randrange(200000),random.randrange(200000))
big.rollback(tok)
assert time.time()-t0<25
""",
 """
class RollbackDSU:
    def __init__(self,n):
        self.p=list(range(n)); self.sz=[1]*n; self.log=[]; self.n=n
    def find(self,x):
        while self.p[x]!=x: x=self.p[x]
        return x
    def union(self,a,b):
        ra,rb=self.find(a),self.find(b)
        if ra==rb:
            return False
        if self.sz[ra]<self.sz[rb]: ra,rb=rb,ra
        self.log.append((rb,ra,self.sz[ra]))
        self.p[rb]=ra; self.sz[ra]+=self.sz[rb]; self.n-=1
        return True
    def snapshot(self):
        return len(self.log)
    def rollback(self,token):
        while len(self.log)>token:
            rb,ra,osz=self.log.pop()
            self.p[rb]=rb; self.sz[ra]=osz; self.n+=1
    def components(self):
        return self.n
"""),

("hpy-017",
 "class `WildcardTrie` with `add(self, word)`, `remove(self, word)` returning True when the word "
 "was present, and `search(self, pattern)` returning the sorted list of stored words matching a "
 "pattern in which `.` matches exactly one character and every other character is literal. A "
 "pattern matches only whole words. Removing a word must not leave it findable, and adding the "
 "same word twice then removing it once must leave it present. The tests store 20000 words and run "
 "2000 dotted searches, so re-scanning every stored word per search will time out.",
 """
t=WildcardTrie()
for w in ['bad','dad','mad','mat','ma']: t.add(w)
assert t.search('bad')==['bad']
assert t.search('.ad')==['bad','dad','mad']
assert t.search('...')==['bad','dad','mad','mat']
assert t.search('..')==['ma']
assert t.search('b..')==['bad'] and t.search('....')==[]
assert t.search('pad')==[]
assert t.remove('bad') is True and t.remove('bad') is False
assert t.search('.ad')==['dad','mad']
t.add('dad')
assert t.remove('dad') is True and t.search('.ad')==['dad','mad'], 'refcount, not a flag'
u=WildcardTrie(); u.add('')
assert u.search('')==['']
import random,time,string
r=random.Random(4)
big=WildcardTrie()
words={''.join(r.choice('abcdefg') for _ in range(8)) for _ in range(20000)}
for w in words: big.add(w)
t0=time.time()
hits=0
for _ in range(2000):
    p=list(r.choice(sorted(words)))
    p[r.randrange(8)]='.'
    hits+=len(big.search(''.join(p)))
assert time.time()-t0<25, 'must not rescan the dictionary per query'
assert hits>=2000
""",
 """
class _Node:
    __slots__=('kids','cnt')
    def __init__(self): self.kids={}; self.cnt=0
class WildcardTrie:
    def __init__(self): self.root=_Node()
    def add(self,word):
        n=self.root
        for ch in word: n=n.kids.setdefault(ch,_Node())
        n.cnt+=1
    def remove(self,word):
        path=[]; n=self.root
        for ch in word:
            if ch not in n.kids: return False
            path.append((n,ch)); n=n.kids[ch]
        if n.cnt==0: return False
        n.cnt-=1
        if n.cnt==0 and not n.kids:
            for par,ch in reversed(path):
                child=par.kids[ch]
                if child.cnt==0 and not child.kids: del par.kids[ch]
                else: break
        return True
    def search(self,pattern):
        out=[]
        def go(n,i,acc):
            if i==len(pattern):
                if n.cnt: out.append(acc)
                return
            c=pattern[i]
            if c=='.':
                for ch,k in n.kids.items(): go(k,i+1,acc+ch)
            elif c in n.kids:
                go(n.kids[c],i+1,acc+c)
        go(self.root,0,'')
        return sorted(out)
"""),

("hpy-018",
 "function `subtract(base, cuts)` where `base` and `cuts` are lists of HALF-OPEN integer intervals "
 "[start, end). Return the sorted, minimal list of half-open intervals covering every point in "
 "`base` that is not in any interval of `cuts`. Adjacent surviving intervals that touch must be "
 "merged into one; empty intervals must never appear in the output; the inputs may overlap "
 "themselves and need not be sorted.",
 """
s=subtract
assert s([],[])==[] and s([],[(0,5)])==[]
assert s([(0,10)],[])==[(0,10)]
assert s([(0,10)],[(0,10)])==[]
assert s([(0,10)],[(3,5)])==[(0,3),(5,10)]
assert s([(0,10)],[(10,20)])==[(0,10)], 'half-open: [0,10) and [10,20) do not overlap'
assert s([(0,10)],[(9,10)])==[(0,9)]
assert s([(0,5),(5,10)],[])==[(0,10)], 'touching survivors merge'
assert s([(0,5),(5,10)],[(4,6)])==[(0,4),(6,10)]
assert s([(0,10),(2,4)],[(1,2)])==[(0,1),(2,10)], 'overlapping base'
assert s([(0,10)],[(1,3),(2,5),(7,8)])==[(0,1),(5,7),(8,10)]
assert s([(0,10)],[(5,5)])==[(0,10)], 'empty cut is a no-op'
assert s([(3,3)],[])==[], 'empty base yields nothing'
assert s([(0,3),(10,13)],[(1,11)])==[(0,1),(11,13)]
""",
 """
def _norm(xs):
    xs=sorted((a,b) for a,b in xs if a<b)
    out=[]
    for a,b in xs:
        if out and a<=out[-1][1]: out[-1][1]=max(out[-1][1],b)
        else: out.append([a,b])
    return out
def subtract(base,cuts):
    b=_norm(base); c=_norm(cuts)
    out=[]; i=0
    for a,e in b:
        cur=a
        while i<len(c) and c[i][1]<=cur: i+=1
        j=i
        while j<len(c) and c[j][0]<e:
            cs,ce=c[j]
            if cs>cur: out.append([cur,cs])
            cur=max(cur,ce)
            if cur>=e: break
            j+=1
        if cur<e: out.append([cur,e])
    merged=[]
    for a,e in out:
        if merged and a<=merged[-1][1]: merged[-1][1]=max(merged[-1][1],e)
        else: merged.append([a,e])
    return [(a,e) for a,e in merged if a<e]
"""),

("hpy-019",
 "class `TokenBucket` with `__init__(self, capacity, refill_per_sec, clock)` where `clock` is a "
 "zero-argument callable returning a float time, and `take(self, n=1)` returning True when n "
 "tokens were available and consumed, False otherwise. The bucket starts full, refills "
 "continuously and fractionally at `refill_per_sec` (not in whole-token steps), never exceeds "
 "`capacity`, and never goes negative. A failed `take` consumes nothing. A request for more than "
 "`capacity` tokens can never succeed. Time never moves backwards, but the same instant may be "
 "observed repeatedly.",
 """
t=[0.0]
b=TokenBucket(10,1.0,lambda:t[0])
assert b.take(10) is True and b.take(1) is False, 'starts full'
t[0]=0.5
assert b.take(1) is False, 'fractional refill: only 0.5 tokens'
t[0]=1.0
assert b.take(1) is True and b.take(1) is False
t[0]=100.0
assert b.take(10) is True, 'refill clamps at capacity'
assert b.take(1) is False, 'did not accumulate 100 tokens'
t[0]=105.0
assert b.take(6) is False and b.take(5) is True, 'failed take consumes nothing'
b2=TokenBucket(3,1.0,lambda:t[0])
assert b2.take(4) is False, 'more than capacity can never succeed'
t[0]=200.0
assert b2.take(4) is False
t2=[0.0]
b3=TokenBucket(2,4.0,lambda:t2[0])
assert b3.take(2) and not b3.take(1)
t2[0]=0.25
assert b3.take(1) and not b3.take(1)
""",
 """
class TokenBucket:
    def __init__(self,capacity,refill_per_sec,clock):
        self.cap=float(capacity); self.rate=float(refill_per_sec)
        self.clock=clock; self.tokens=float(capacity); self.last=clock()
    def _fill(self):
        now=self.clock()
        if now>self.last:
            self.tokens=min(self.cap,self.tokens+(now-self.last)*self.rate)
            self.last=now
    def take(self,n=1):
        if n>self.cap: return False
        self._fill()
        if self.tokens>=n-1e-12:
            self.tokens-=n
            if self.tokens<0: self.tokens=0.0
            return True
        return False
"""),

("hpy-020",
 "function `transfer_all(accounts, ops)` where `accounts` is a list of starting integer balances "
 "and `ops` is a list of (src, dst, amount). Apply every operation, each in its own thread, using "
 "one `threading.Lock` per account so that a transfer holds both locks while it moves the money. "
 "It must not deadlock when transfers run in both directions between the same pair, and a transfer "
 "whose source lacks the funds at the moment it holds the locks is skipped. Return the final "
 "balance list. There must be exactly one lock per account and both must be held during the move.",
 """
import time, threading
f=transfer_all
assert f([10,10],[])==[10,10]
assert f([10,0],[(0,1,5)])==[5,5]
assert f([1,0],[(0,1,5)])==[1,0], 'insufficient funds is skipped'
import random
r=random.Random(2)
n=8
ops=[]
for _ in range(400):
    a=r.randrange(n); b=r.randrange(n)
    while b==a: b=r.randrange(n)
    ops.append((a,b,r.randint(1,20)))
start=[1000]*n
t0=time.time()
out=f(list(start),ops)
el=time.time()-t0
assert el<30, 'deadlocked or serialised badly (%.1fs)'%el
assert sum(out)==sum(start), 'money was created or destroyed: %s'%out
assert all(x>=0 for x in out)
assert threading.active_count()<50
""",
 """
import threading
def transfer_all(accounts,ops):
    locks=[threading.Lock() for _ in accounts]
    def one(src,dst,amt):
        a,b=(src,dst) if src<dst else (dst,src)
        with locks[a]:
            with locks[b]:
                if accounts[src]>=amt:
                    accounts[src]-=amt; accounts[dst]+=amt
    ts=[threading.Thread(target=one,args=o) for o in ops]
    for t in ts: t.start()
    for t in ts: t.join()
    return accounts
"""),
("hpy-021",
 "function `deep_copy(obj)` returning a deep copy of a structure built from dicts, lists, sets, "
 "tuples and scalars. It must preserve the SHARING graph: two references to the same object in the "
 "input become two references to one copy in the output, and reference cycles are copied rather "
 "than causing infinite recursion. Strings, ints, floats, bools and None are returned as-is. Do not "
 "import or use the `copy` or `pickle` modules.",
 """
import inspect
src=inspect.getsource(deep_copy)
assert 'copy' not in src.replace('deep_copy','').replace('_copy','') or 'import copy' not in src
assert 'pickle' not in src
d=deep_copy
shared=[1,2]
o={'a':shared,'b':shared}
c=d(o)
assert c=={'a':[1,2],'b':[1,2]} and c['a'] is c['b'], 'sharing not preserved'
assert c['a'] is not shared
cyc=[1]; cyc.append(cyc)
cc=d(cyc)
assert cc[0]==1 and cc[1] is cc and cc is not cyc, 'cycle not handled'
dd={}; dd['self']=dd
r=d(dd); assert r['self'] is r and r is not dd
t=(1,[2],3)
ct=d(t); assert ct==t and ct is not t and ct[1] is not t[1]
s={1,2,3}
assert d(s)=={1,2,3} and d(s) is not s
n={'x':None,'y':True,'z':'str'}
assert d(n)==n
deep=[]; cur=deep
for _ in range(3000):
    nxt=[]; cur.append(nxt); cur=nxt
r=d(deep)
assert isinstance(r,list), 'deep nesting must not blow the stack'
both=[shared,shared,{'k':shared}]
cb=d(both); assert cb[0] is cb[1] is cb[2]['k']
""",
 """
def deep_copy(obj):
    memo={}
    def go(o):
        if isinstance(o,(str,int,float,bool,type(None))): return o
        k=id(o)
        if k in memo: return memo[k]
        if isinstance(o,list):
            new=[]; memo[k]=new
            stack=[(o,new)]
            while stack:
                src,dst=stack.pop()
                for item in src:
                    if isinstance(item,list) and id(item) not in memo:
                        sub=[]; memo[id(item)]=sub; dst.append(sub); stack.append((item,sub))
                    else:
                        dst.append(go(item))
            return new
        if isinstance(o,dict):
            new={}; memo[k]=new
            for kk,vv in o.items(): new[go(kk)]=go(vv)
            return new
        if isinstance(o,set):
            new=set(); memo[k]=new
            for item in o: new.add(go(item))
            return new
        if isinstance(o,tuple):
            new=tuple(go(i) for i in o); memo[k]=new; return new
        return o
    return go(obj)
"""),

("hpy-022",
 "function `natural_key(s)` returning a sort key such that `sorted(names, key=natural_key)` orders "
 "strings the way a file manager does: runs of digits compare numerically and everything else "
 "compares as lowercase text, with case used only to break an otherwise exact tie (lowercase "
 "first). Leading zeros do not change the numeric value but a shorter zero-padded run sorts before "
 "a longer one of equal value. The key must be comparable across strings that start with a digit "
 "and strings that do not.",
 """
k=natural_key
S=lambda xs: sorted(xs,key=k)
assert S(['a2','a10','a1'])==['a1','a2','a10']
assert S(['x','x1'])==['x','x1']
assert S(['10','9','1'])==['1','9','10']
S(['a','1']); S(['a1','1a','b'])  # must not raise: keys stay comparable across kinds
assert S(['file2.txt','file10.txt','file1.txt'])==['file1.txt','file2.txt','file10.txt']
assert S(['A1','a1'])==['a1','A1'], 'case only breaks an exact tie, lowercase first'
assert S(['Foo','bar'])==['bar','Foo'], 'primary compare is case-insensitive'
assert S(['a01','a1'])==['a1','a01'], 'equal value, shorter run first'
assert S(['v1.10.0','v1.9.0','v1.2.0'])==['v1.2.0','v1.9.0','v1.10.0']
assert S(['a1b2','a1b10'])==['a1b2','a1b10']
assert k('a')==k('a') and (k('a')<k('b'))
""",
 """
import re
_SP=re.compile(r'(\\d+)')
def natural_key(s):
    parts=_SP.split(s)
    key=[]
    for i,p in enumerate(parts):
        if i%2:
            key.append((1,int(p),len(p),''))
        elif p:
            key.append((0,0,0,p.lower()))
    return (key,tuple((c.isupper(),c) for c in s))
"""),

("hpy-023",
 "two functions `to_base(n, alphabet)` and `from_base(s, alphabet)` converting between an integer "
 "and its representation in an arbitrary positional base given by a string of distinct digit "
 "characters, lowest value first. Zero is the single first character of the alphabet. A negative "
 "number is prefixed with `-`. `from_base` must raise ValueError on an empty string or on a "
 "character not in the alphabet. They must round-trip for any integer including very large ones.",
 """
A='0123456789abcdef'
B='ab'
assert to_base(0,A)=='0' and to_base(255,A)=='ff' and to_base(-255,A)=='-ff'
assert from_base('ff',A)==255 and from_base('-ff',A)==-255 and from_base('0',A)==0
assert to_base(0,B)=='a' and to_base(1,B)=='b' and to_base(2,B)=='ba' and to_base(5,B)=='bab'
assert from_base('bab',B)==5
assert to_base(1,A)=='1'
big=(1<<600)+12345
assert from_base(to_base(big,A),A)==big
assert from_base(to_base(-big,B),B)==-big
assert from_base('00ff',A)==255, 'leading zeros are allowed on input'
for bad in ['','-','xyz','-z']:
    try:
        from_base(bad,A); raise SystemExit('accepted %r'%bad)
    except ValueError: pass
import random
r=random.Random(8)
for _ in range(300):
    v=r.randint(-10**12,10**12)
    for al in (A,B,'zyx'):
        assert from_base(to_base(v,al),al)==v, (v,al)
""",
 """
def to_base(n,alphabet):
    b=len(alphabet)
    if b<2: raise ValueError('base too small')
    if n==0: return alphabet[0]
    neg=n<0; n=abs(n); out=[]
    while n:
        n,r=divmod(n,b); out.append(alphabet[r])
    return ('-' if neg else '')+''.join(reversed(out))
def from_base(s,alphabet):
    if not isinstance(s,str) or not s: raise ValueError('empty')
    b=len(alphabet)
    neg=s.startswith('-')
    body=s[1:] if neg else s
    if not body: raise ValueError('empty')
    idx={c:i for i,c in enumerate(alphabet)}
    v=0
    for ch in body:
        if ch not in idx: raise ValueError('bad digit %r'%ch)
        v=v*b+idx[ch]
    return -v if neg else v
"""),

("hpy-024",
 "function `parse_csv_stream(chunks)` consuming an iterable of string CHUNKS of a CSV document and "
 "yielding each complete row as a list of field strings, as soon as that row is complete. Follow "
 "RFC 4180: fields may be quoted with `\\\"`, a quoted field may contain commas, CRLF and doubled "
 "`\\\"\\\"` meaning one quote; `\\\\r\\\\n`, `\\\\n` and `\\\\r` all end a row outside quotes; a trailing newline "
 "does not produce an extra empty row, but a final row without a newline is still yielded. Chunk "
 "boundaries fall at arbitrary positions, including inside a quoted field, between the two "
 "characters of a CRLF, and between the two characters of an escaped quote. Raise ValueError if the "
 "document ends inside an unterminated quoted field.",
 """
p=parse_csv_stream
L=lambda *c: list(p(iter(c)))
assert L('a,b\\nc,d\\n')==[['a','b'],['c','d']]
assert L('a,b\\nc,d')==[['a','b'],['c','d']], 'final row without newline'
assert L('a,b\\n')==[['a','b']] and L('')==[]
assert L('"a,b",c\\n')==[['a,b','c']]
assert L('"a""b"\\n')==[['a"b']]
assert L('"line1\\nline2",x\\n')==[['line1\\nline2','x']]
assert L('a,b\\r\\nc,d\\r\\n')==[['a','b'],['c','d']]
assert L('a\\rb\\r')==[['a'],['b']]
assert L(',\\n')==[['','']]
assert L('a,\\n')==[['a','']]
assert L('"a"\\r\\n')==[['a']]
assert L('a,b','\\nc,d\\n')==[['a','b'],['c','d']], 'split between rows'
assert L('"a,','b",c\\n')==[['a,b','c']], 'split inside a quoted field'
assert L('a,b\\r','\\nc,d\\n')==[['a','b'],['c','d']], 'split inside CRLF'
assert L('"a"','"b"\\n')==[['a"b']], 'split inside an escaped quote'
assert L('"x','y','z"\\n')==[['xyz']]
import itertools
doc='"a\\nb",c\\nd,"e""f"\\n'
for k in range(1,len(doc)+1):
    got=list(p(doc[i:i+k] for i in range(0,len(doc),k)))
    assert got==[['a\\nb','c'],['d','e"f']], (k,got)
lazy_seen=[]
def gen():
    for c in ['a,b\\n','c,d\\n']:
        lazy_seen.append(c); yield c
it=p(gen()); first=next(it)
assert first==['a','b'] and len(lazy_seen)==1, 'must yield before consuming the whole input'
try:
    L('"unterminated\\n'); raise SystemExit('accepted unterminated quote')
except ValueError: pass
""",
 """
def parse_csv_stream(chunks):
    field=[]; row=[]; inq=False; qpend=False; cr=False; started=False
    for chunk in chunks:
        for ch in chunk:
            if qpend:
                qpend=False
                if ch=='"':
                    field.append('"'); continue
                inq=False
                # fall through to handle ch as an unquoted character
            if inq:
                if ch=='"': qpend=True
                else: field.append(ch)
                continue
            if cr:
                cr=False
                if ch=='\\n':
                    continue
            if ch=='"':
                inq=True; started=True
            elif ch==',':
                row.append(''.join(field)); field=[]; started=True
            elif ch=='\\n' or ch=='\\r':
                row.append(''.join(field)); field=[]
                yield row
                row=[]; started=False
                cr=(ch=='\\r')
            else:
                field.append(ch); started=True
    if qpend: inq=False
    if inq: raise ValueError('unterminated quoted field')
    if field or row or started:
        row.append(''.join(field))
        yield row
"""),

("hpy-025",
 "function `merge_sorted(iterables)` returning an ITERATOR over the merged ascending sequence of "
 "several already-sorted iterables, stable across sources so that equal values come out in source "
 "order. It must be lazy and memory-bounded: it holds at most one pending item per source, so it "
 "works on infinite sources and on 1000 sources of 1000 items without buffering them. Equal values "
 "must not be deduplicated.",
 """
import itertools
m=merge_sorted
assert list(m([]))==[]
assert list(m([[1,2,3]]))==[1,2,3]
assert list(m([[1,3,5],[2,4,6]]))==[1,2,3,4,5,6]
assert list(m([[],[1],[]]))==[1]
assert list(m([[1,1],[1]]))==[1,1,1], 'no dedup'
it=m([itertools.count(0,2),itertools.count(1,2)])
assert [next(it) for _ in range(6)]==[0,1,2,3,4,5], 'must work on infinite sources'
src=[[(1,'a')],[(1,'b')]]
assert [x[1] for x in m(src)]==['a','b'], 'stable across sources'
import tracemalloc
srcs=[list(range(i,i+1000)) for i in range(1000)]
tracemalloc.start()
n=0
for _ in m(srcs): n+=1
peak=tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
assert n==1000*1000
assert peak<3_000_000, 'buffered the inputs (peak %d)'%peak
pulled=[0]
def counted():
    for i in range(100):
        pulled[0]+=1; yield i
it2=m([counted(),counted()])
next(it2); next(it2)
assert pulled[0]<=4, 'not lazy: pulled %d'%pulled[0]
""",
 """
import heapq
def merge_sorted(iterables):
    h=[]
    for i,src in enumerate(iterables):
        it=iter(src)
        try: v=next(it)
        except StopIteration: continue
        h.append((v,i,it))
    heapq.heapify(h)
    def gen():
        while h:
            v,i,it=heapq.heappop(h)
            yield v
            try: heapq.heappush(h,(next(it),i,it))
            except StopIteration: pass
    return gen()
"""),
("hpy-026",
 "function `skyline(buildings)` where each building is (left, right, height) with `right` "
 "exclusive. Return the skyline as a list of [x, height] key points in ascending x, where each "
 "point is the left end of a horizontal segment at that height, consecutive points never repeat a "
 "height, and the last point drops to height 0. The tests include 100000 buildings, so an O(n^2) "
 "sweep will time out.",
 """
s=skyline
assert s([])==[]
assert s([(0,2,3)])==[[0,3],[2,0]]
assert s([(2,9,10),(3,7,15),(5,12,12),(15,20,10),(19,24,8)])==[[2,10],[3,15],[7,12],[12,0],[15,10],[20,8],[24,0]]
assert s([(0,5,3),(0,5,3)])==[[0,3],[5,0]], 'duplicates collapse'
assert s([(0,5,3),(5,10,3)])==[[0,3],[10,0]], 'no repeated height at a join'
assert s([(0,10,5),(2,4,3)])==[[0,5],[10,0]], 'a contained shorter building is invisible'
assert s([(0,2,3),(4,6,3)])==[[0,3],[2,0],[4,3],[6,0]], 'a gap returns to zero'
assert s([(1,2,1),(1,2,2),(1,2,3)])==[[1,3],[2,0]]
import random,time
random.seed(6)
bs=[]
for _ in range(100000):
    a=random.randint(0,10**6); bs.append((a,a+random.randint(1,200),random.randint(1,10**5)))
t0=time.time(); r=s(bs)
assert time.time()-t0<25, 'needs an O(n log n) sweep'
assert r[-1][1]==0 and all(r[i][0]<r[i+1][0] for i in range(len(r)-1))
assert all(r[i][1]!=r[i+1][1] for i in range(len(r)-1))
""",
 """
import heapq
def skyline(buildings):
    if not buildings: return []
    evs=[]
    for l,rr,h in buildings:
        if l>=rr or h<=0: continue
        evs.append((l,-h,rr)); evs.append((rr,0,0))
    if not evs: return []
    evs.sort()
    out=[]; heap=[(0,float('inf'))]
    i=0
    while i<len(evs):
        x=evs[i][0]
        while i<len(evs) and evs[i][0]==x:
            _,nh,rr=evs[i]
            if nh: heapq.heappush(heap,(nh,rr))
            i+=1
        while heap[0][1]<=x: heapq.heappop(heap)
        h=-heap[0][0]
        if not out or out[-1][1]!=h: out.append([x,h])
    return out
"""),

("hpy-027",
 "function `shortest_path(graph, src, dst)` where `graph` maps a node to a list of "
 "(neighbour, weight) with non-negative integer weights, directed. Return (total_cost, path) with "
 "`path` the list of nodes from src to dst inclusive, or (None, []) when dst is unreachable. When "
 "several paths tie on cost, return the one with the FEWEST edges, and among those the "
 "lexicographically smallest node sequence. src == dst costs 0. The tests run a 200000-node graph, "
 "so a scan-for-minimum Dijkstra will time out -- use a heap.",
 """
sp=shortest_path
g={'a':[('b',1),('c',4)],'b':[('c',2),('d',5)],'c':[('d',1)],'d':[]}
assert sp(g,'a','d')==(4,['a','b','c','d'])
assert sp(g,'a','a')==(0,['a'])
assert sp(g,'d','a')==(None,[])
assert sp({'a':[]},'a','z')==(None,[])
tie={'a':[('b',1),('c',1)],'b':[('d',1)],'c':[('d',1)],'d':[]}
assert sp(tie,'a','d')==(2,['a','b','d']), 'lexicographic tiebreak'
few={'a':[('b',2),('c',1)],'c':[('b',1)],'b':[]}
assert sp(few,'a','b')==(2,['a','b']), 'equal cost, fewer edges wins'
z={'a':[('b',0)],'b':[]}
assert sp(z,'a','b')==(0,['a','b'])
import random,time
random.seed(12)
N=200000
big={i:[] for i in range(N)}
for i in range(N-1): big[i].append((i+1,random.randint(1,10)))
for _ in range(200000):
    u=random.randrange(N); v=random.randrange(N)
    big[u].append((v,random.randint(1,100)))
t0=time.time(); c,path=sp(big,0,N-1)
assert time.time()-t0<25, 'needs a heap-based Dijkstra'
assert c is not None and path[0]==0 and path[-1]==N-1
tot=0
for a,b in zip(path,path[1:]):
    tot+=min(w for n,w in big[a] if n==b)
assert tot==c, (tot,c)
""",
 """
import heapq
def shortest_path(graph,src,dst):
    if src==dst and src in graph: return (0,[src])
    INF=float('inf')
    best={src:(0,0)}
    prev={}
    h=[(0,0,src)]
    seen=set()
    while h:
        c,ln,u=heapq.heappop(h)
        if u in seen: continue
        seen.add(u)
        if u==dst: break
        for v,w in sorted(graph.get(u,[])):
            if v in seen: continue
            cand=(c+w,ln+1)
            cur=best.get(v)
            better=cur is None or cand<cur
            if not better and cand==cur:
                old=prev.get(v)
                better = old is not None and u<old
            if better:
                best[v]=cand; prev[v]=u
                heapq.heappush(h,(cand[0],cand[1],v))
    if dst not in best: return (None,[])
    path=[dst]
    while path[-1]!=src: path.append(prev[path[-1]])
    return (best[dst][0],path[::-1])
"""),

("hpy-028",
 "function `backoff_delays(attempts, base, cap, rng)` returning the list of sleep durations for a "
 "retry policy using AWS-style FULL JITTER: the delay for attempt i (counting from 0) is "
 "`rng.uniform(0, min(cap, base * 2**i))`. `attempts` is the number of retries, so the list has "
 "that many entries and an `attempts` of 0 returns an empty list. The exponential term must be "
 "capped BEFORE the jitter is drawn, not after, and `rng.uniform` must be called exactly once per "
 "attempt in order.",
 """
import random
b=backoff_delays
assert b(0,1.0,30.0,random.Random(1))==[]
class Fake:
    def __init__(self): self.calls=[]
    def uniform(self,a,c): self.calls.append((a,c)); return c
f=Fake()
r=b(5,1.0,8.0,f)
assert f.calls==[(0,1.0),(0,2.0),(0,4.0),(0,8.0),(0,8.0)], f.calls
assert r==[1.0,2.0,4.0,8.0,8.0]
f2=Fake(); b(3,0.5,100.0,f2)
assert f2.calls==[(0,0.5),(0,1.0),(0,2.0)]
f3=Fake(); b(3,10.0,5.0,f3)
assert f3.calls==[(0,5.0),(0,5.0),(0,5.0)], 'cap applies before the draw'
class Half:
    def uniform(self,a,c): return (a+c)/2.0
assert b(3,1.0,100.0,Half())==[0.5,1.0,2.0]
rr=random.Random(0)
out=b(20,1.0,60.0,rr)
assert len(out)==20 and all(0<=x<=60 for x in out)
""",
 """
def backoff_delays(attempts,base,cap,rng):
    return [rng.uniform(0,min(cap,base*(2**i))) for i in range(attempts)]
"""),

("hpy-029",
 "function `topo_lex(graph)` where `graph` maps a node to the list of nodes that DEPEND ON it "
 "(its successors). Return the lexicographically smallest topological ordering of all nodes, or "
 "None when the graph has a cycle. Nodes appearing only as a successor are still nodes. The tests "
 "run 200000 nodes, so repeatedly scanning for the smallest ready node will time out -- use a heap.",
 """
t=topo_lex
assert t({})==[]
assert t({'a':[]})==['a']
assert t({'a':['b'],'b':['a']}) is None
assert t({'b':[],'a':[]})==['a','b']
assert t({'a':['c'],'b':['c'],'c':[]})==['a','b','c']
assert t({'c':['a'],'b':[]})==['b','c','a'], 'lexicographically smallest, not any valid order'
assert t({'x':['y']})==['x','y'], 'y appears only as a successor'
assert t({'a':['b'],'b':['c'],'c':['a']}) is None
assert t({'a':[],'b':['a']})==['b','a']
import random,time,heapq
random.seed(13)
N=200000
g={i:[] for i in range(N)}
for _ in range(400000):
    u=random.randrange(N); v=random.randrange(N)
    if u<v: g[u].append(v)
t0=time.time(); r=t(g)
assert time.time()-t0<25, 'needs a heap'
assert r is not None and len(r)==N and sorted(r)==list(range(N))
pos={n:i for i,n in enumerate(r)}
for u,vs in g.items():
    for v in vs: assert pos[u]<pos[v]
""",
 """
import heapq
def topo_lex(graph):
    nodes=set(graph)
    for vs in graph.values(): nodes.update(vs)
    indeg={n:0 for n in nodes}
    for u,vs in graph.items():
        for v in vs: indeg[v]+=1
    h=[n for n in nodes if indeg[n]==0]
    heapq.heapify(h)
    out=[]
    while h:
        u=heapq.heappop(h); out.append(u)
        for v in graph.get(u,[]):
            indeg[v]-=1
            if indeg[v]==0: heapq.heappush(h,v)
    return out if len(out)==len(nodes) else None
"""),

("hpy-030",
 "class `Spreadsheet` with `set(self, cell, value)` and `get(self, cell)`. A value is either a "
 "number or a formula string starting with `=`. A formula is cell references and integer literals "
 "joined by `+`, `-` and `*` with the usual precedence, e.g. `=A1+B2*2`. `get` returns the current "
 "computed number; an unset cell reads as 0. Changing a cell must be visible through every formula "
 "that transitively depends on it. A `set` that would create a reference cycle must raise "
 "ValueError and leave the sheet exactly as it was. `get` must be O(1) amortised -- the tests build "
 "a 5000-deep dependency chain and then read the far end 5000 times.",
 """
import time
s=Spreadsheet()
assert s.get('A1')==0
s.set('A1',5); assert s.get('A1')==5
s.set('B1','=A1+3'); assert s.get('B1')==8
s.set('A1',10); assert s.get('B1')==13, 'dependents must update'
s.set('C1','=A1+B1*2'); assert s.get('C1')==10+13*2
s.set('A1',1); assert s.get('C1')==1+4*2
s.set('D1','=A1-B1'); assert s.get('D1')==1-4
try:
    s.set('A1','=C1'); raise SystemExit('accepted a cycle')
except ValueError: pass
assert s.get('A1')==1 and s.get('C1')==9, 'failed set must not corrupt the sheet'
s2=Spreadsheet(); s2.set('X1','=Y1+1'); assert s2.get('X1')==1, 'unset cell reads 0'
s2.set('Y1',4); assert s2.get('X1')==5
s3=Spreadsheet()
s3.set('A1',1)
for i in range(2,5001): s3.set('A%d'%i,'=A%d+1'%(i-1))
assert s3.get('A5000')==5000
t0=time.time()
for _ in range(5000): s3.get('A5000')
assert time.time()-t0<5, 'get must not re-evaluate the chain'
s3.set('A1',2); assert s3.get('A5000')==5001
""",
 """
import re
_REF=re.compile(r'[A-Z]+\\d+')
_TOK=re.compile(r'\\s*([A-Z]+\\d+|\\d+|[-+*])')
class Spreadsheet:
    def __init__(self):
        self.raw={}; self.val={}; self.deps={}; self.rdeps={}
    def _parse(self,f):
        toks=[]; i=0; body=f[1:]
        while i<len(body):
            if body[i].isspace(): i+=1; continue
            m=_TOK.match(body,i)
            if not m: raise ValueError('bad formula')
            toks.append(m.group(1)); i=m.end()
        return toks
    def _eval(self,toks):
        terms=[]; cur=None; op='+'
        def val(t):
            return self.val.get(t,0) if _REF.fullmatch(t) else int(t)
        i=0; total=0; prod=None
        pending='+'
        while i<len(toks):
            v=val(toks[i]); i+=1
            while i<len(toks) and toks[i]=='*':
                v=v*val(toks[i+1]); i+=2
            total = total+v if pending=='+' else total-v
            if i<len(toks):
                pending=toks[i]; i+=1
        return total
    def _refs(self,toks):
        return {t for t in toks if _REF.fullmatch(t)}
    def set(self,cell,value):
        old_raw=self.raw.get(cell); old_deps=self.deps.get(cell,set())
        if isinstance(value,str) and value.startswith('='):
            toks=self._parse(value); new=self._refs(toks)
        else:
            toks=None; new=set()
        seen=set(); stack=[cell]
        # walk forward from the new dependencies; reaching `cell` is a cycle
        work=list(new)
        while work:
            c=work.pop()
            if c==cell: raise ValueError('cycle')
            if c in seen: continue
            seen.add(c)
            work.extend(self.deps.get(c,()))
        for d in old_deps: self.rdeps.get(d,set()).discard(cell)
        self.raw[cell]=(toks if toks is not None else value)
        self.deps[cell]=new
        for d in new: self.rdeps.setdefault(d,set()).add(cell)
        self._recalc(cell)
    def _recalc(self,cell):
        # The affected set is everything downstream of `cell`, but it has to be
        # evaluated in dependency order, not discovery order: C1 = A1 + B1*2 and
        # B1 = A1 + 3 are both reachable from A1 in one hop, and evaluating C1
        # first reads a stale B1.
        aff=set(); stack=[cell]
        while stack:
            c=stack.pop()
            if c in aff: continue
            aff.add(c); stack.extend(self.rdeps.get(c,()))
        indeg={c:sum(1 for d in self.deps.get(c,()) if d in aff) for c in aff}
        ready=[c for c in aff if indeg[c]==0]
        done=0
        while ready:
            c=ready.pop()
            r=self.raw.get(c,0)
            self.val[c]=self._eval(r) if isinstance(r,list) else r
            done+=1
            for d in self.rdeps.get(c,()):
                if d in aff:
                    indeg[d]-=1
                    if indeg[d]==0: ready.append(d)
        assert done==len(aff)
    def get(self,cell):
        return self.val.get(cell,0)
"""),
]


def tasks():
    return [(tid, spec, tests) for tid, spec, tests, _ref in T]


VERIFY_DRIVER = """
import json, subprocess
bad = []
for tid, ref, tests in CASES:
    p = "/tmp/%s.py" % tid
    open(p, "w").write(ref + "\\n\\n" + tests)
    r = subprocess.run(["python", p], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()
        bad.append((tid, tail[-1][:160] if tail else "nonzero exit"))
print(json.dumps(bad))
"""


def verify_source():
    cases = [(tid, ref, tests) for tid, _s, tests, ref in T]
    return "CASES = " + repr(cases) + "\n" + VERIFY_DRIVER


if __name__ == "__main__":
    print("hard python tasks: %d" % len(T))
