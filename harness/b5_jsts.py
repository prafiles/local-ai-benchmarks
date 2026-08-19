#!/usr/bin/env python3
"""JS (15) and TS (15), hard tier. JS runs under node; TS must typecheck under
`tsc --strict` and then run.

The TS half is deliberately weighted toward TYPE-LEVEL work, because that is
where the b3 tier was blindest: there, TypeScript tasks were JavaScript tasks
with annotations, and every model scored 89-98%. Here several tasks are solvable
only by a correct conditional or template-literal type, and the tests use
`@ts-expect-error` on the cases that MUST fail to compile -- so a solution that
types everything as `any` fails, because the expected error never arrives and
tsc reports the unused directive as an error of its own.
"""

# ---------------------------------------------------------------- JS (15)
# (id, spec, tests, reference) -- solution exports via module.exports
JS = [

("hjs-001",
 "`deepEqual(a, b)` implementing SameValueZero structural equality: NaN equals NaN, +0 equals -0, "
 "Date compares by time value, RegExp by source and flags, Map and Set compare by contents "
 "irrespective of insertion order, arrays and plain objects compare by own enumerable keys, and "
 "objects containing reference CYCLES must be compared without infinite recursion. Values of "
 "different types are never equal.",
 "const {deepEqual}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(deepEqual(NaN,NaN),true);\n"
 "a.strictEqual(deepEqual(0,-0),true);\n"
 "a.strictEqual(deepEqual(new Date(5),new Date(5)),true);\n"
 "a.strictEqual(deepEqual(new Date(5),new Date(6)),false);\n"
 "a.strictEqual(deepEqual(/a/gi,/a/gi),true);\n"
 "a.strictEqual(deepEqual(/a/g,/a/i),false);\n"
 "a.strictEqual(deepEqual(new Set([1,2]),new Set([2,1])),true);\n"
 "a.strictEqual(deepEqual(new Set([1]),new Set([1,2])),false);\n"
 "a.strictEqual(deepEqual(new Map([['a',1],['b',2]]),new Map([['b',2],['a',1]])),true);\n"
 "a.strictEqual(deepEqual(new Map([['a',1]]),new Map([['a',2]])),false);\n"
 "a.strictEqual(deepEqual({a:1,b:[1,2]},{b:[1,2],a:1}),true);\n"
 "a.strictEqual(deepEqual([1,2],{0:1,1:2}),false);\n"
 "a.strictEqual(deepEqual(1,'1'),false);\n"
 "const x={v:1};x.self=x;const y={v:1};y.self=y;\n"
 "a.strictEqual(deepEqual(x,y),true);\n"
 "const p={v:1};p.self=p;const q={v:2};q.self=q;\n"
 "a.strictEqual(deepEqual(p,q),false);\n"
 "console.log('OK');",
 "function sv(a,b){return a===b?(a!==0||1/a===1/b||true):(a!==a&&b!==b);}\n"
 "function deepEqual(a,b,seen){seen=seen||new Map();\n"
 "if(typeof a!=='object'||typeof b!=='object'||a===null||b===null)"
 "return a===b||(a!==a&&b!==b);\n"
 "const prev=seen.get(a);if(prev&&prev.has(b))return true;\n"
 "if(!prev)seen.set(a,new Set([b]));else prev.add(b);\n"
 "if(Object.getPrototypeOf(a)!==Object.getPrototypeOf(b))return false;\n"
 "if(a instanceof Date)return a.getTime()===b.getTime();\n"
 "if(a instanceof RegExp)return a.source===b.source&&a.flags===b.flags;\n"
 "if(a instanceof Set){if(a.size!==b.size)return false;\n"
 " const used=new Set();\n"
 " for(const v of a){let hit=false;\n"
 "  for(const w of b){if(used.has(w))continue;if(deepEqual(v,w,seen)){used.add(w);hit=true;break;}}\n"
 "  if(!hit)return false;}return true;}\n"
 "if(a instanceof Map){if(a.size!==b.size)return false;\n"
 " const used=new Set();\n"
 " for(const [k,v] of a){let hit=false;\n"
 "  for(const [k2,v2] of b){if(used.has(k2))continue;\n"
 "   if(deepEqual(k,k2,seen)&&deepEqual(v,v2,seen)){used.add(k2);hit=true;break;}}\n"
 "  if(!hit)return false;}return true;}\n"
 "if(Array.isArray(a)!==Array.isArray(b))return false;\n"
 "const ka=Object.keys(a),kb=Object.keys(b);if(ka.length!==kb.length)return false;\n"
 "for(const k of ka){if(!Object.prototype.hasOwnProperty.call(b,k))return false;\n"
 " if(!deepEqual(a[k],b[k],seen))return false;}\n"
 "return true;}\n"
 "module.exports={deepEqual};"),

("hjs-002",
 "`pLimit(n)` returning a function that takes a zero-argument function returning a promise and "
 "returns a promise, running at most n of them concurrently. Queued jobs start in the order they "
 "were submitted; a rejected job rejects only its own promise and must not stop the queue or leave "
 "a concurrency slot permanently occupied.",
 "const {pLimit}=require('./sol.js');const a=require('assert');\n"
 "(async()=>{\n"
 " const limit=pLimit(2);let cur=0,peak=0;const order=[];\n"
 " const mk=(id,ms,fail)=>()=>new Promise((res,rej)=>{cur++;peak=Math.max(peak,cur);\n"
 "  order.push(id);setTimeout(()=>{cur--;fail?rej(new Error('x'+id)):res(id);},ms);});\n"
 " const ps=[limit(mk(1,40)),limit(mk(2,10)),limit(mk(3,10,true)),limit(mk(4,10)),limit(mk(5,10))];\n"
 " const out=await Promise.allSettled(ps);\n"
 " a.strictEqual(peak,2,'peak concurrency '+peak);\n"
 " a.deepStrictEqual(order,[1,2,3,4,5],'start order '+order);\n"
 " a.strictEqual(out[0].value,1);a.strictEqual(out[2].status,'rejected');\n"
 " a.strictEqual(out[4].value,5,'queue stalled after a rejection');\n"
 " const l1=pLimit(1);const seen=[];\n"
 " await Promise.all([l1(async()=>{seen.push('a')}),l1(async()=>{seen.push('b')})]);\n"
 " a.deepStrictEqual(seen,['a','b']);\n"
 " console.log('OK');})().catch(e=>{console.error(e);process.exit(1);});",
 "function pLimit(n){let active=0;const q=[];\n"
 "const next=()=>{if(active>=n||!q.length)return;const job=q.shift();active++;\n"
 " Promise.resolve().then(job.fn).then(job.res,job.rej).finally(()=>{active--;next();});};\n"
 "return fn=>new Promise((res,rej)=>{q.push({fn,res,rej});next();});}\n"
 "module.exports={pLimit};"),

("hjs-003",
 "`debounce(fn, wait, options)` where options may set `leading` and `trailing`, both defaulting to "
 "trailing only. The returned function has `.cancel()` discarding a pending call and `.flush()` "
 "invoking it immediately, and returns the result of the most recent actual invocation. With both "
 "leading and trailing true, a single isolated call fires ONCE (leading only), and a burst of two "
 "or more fires twice. `this` and the latest arguments must reach the trailing call.",
 "const {debounce}=require('./sol.js');const a=require('assert');\n"
 "const sleep=ms=>new Promise(r=>setTimeout(r,ms));\n"
 "(async()=>{\n"
 " let calls=[];const f=(...x)=>{calls.push(x);return x[0];};\n"
 " let d=debounce(f,30);d(1);d(2);d(3);\n"
 " a.deepStrictEqual(calls,[]);await sleep(60);\n"
 " a.deepStrictEqual(calls,[[3]],'trailing uses latest args');\n"
 " calls=[];d=debounce(f,30,{leading:true,trailing:false});d(1);d(2);\n"
 " a.deepStrictEqual(calls,[[1]]);await sleep(60);a.deepStrictEqual(calls,[[1]]);\n"
 " calls=[];d=debounce(f,30,{leading:true,trailing:true});d(1);await sleep(60);\n"
 " a.deepStrictEqual(calls,[[1]],'isolated call fires once, not twice');\n"
 " calls=[];d=debounce(f,30,{leading:true,trailing:true});d(1);d(2);await sleep(60);\n"
 " a.deepStrictEqual(calls,[[1],[2]],'a burst fires twice');\n"
 " calls=[];d=debounce(f,30);d(9);d.cancel();await sleep(60);\n"
 " a.deepStrictEqual(calls,[],'cancel');\n"
 " calls=[];d=debounce(f,30);d(7);a.strictEqual(d.flush(),7);\n"
 " a.deepStrictEqual(calls,[[7]]);await sleep(60);a.deepStrictEqual(calls,[[7]]);\n"
 " const obj={n:5,m:debounce(function(){return this.n;},10)};\n"
 " obj.m();await sleep(30);\n"
 " console.log('OK');})().catch(e=>{console.error(e);process.exit(1);});",
 "function debounce(fn,wait,options){options=options||{};\n"
 "const leading=!!options.leading;const trailing=options.trailing!==undefined?!!options.trailing:!leading?true:!!options.trailing;\n"
 "let t=null,lastArgs=null,lastThis=null,result,invokedLeading=false,pending=false;\n"
 "function invoke(){result=fn.apply(lastThis,lastArgs);lastArgs=null;lastThis=null;pending=false;return result;}\n"
 "function later(){t=null;if(trailing&&pending&&!(invokedLeading&&!pending))invoke();invokedLeading=false;}\n"
 "function d(...args){lastArgs=args;lastThis=this;\n"
 " if(t===null){if(leading){invokedLeading=true;pending=false;invoke();lastArgs=args;lastThis=this;}else{pending=true;}\n"
 "  t=setTimeout(later,wait);return result;}\n"
 " pending=true;clearTimeout(t);t=setTimeout(later,wait);return result;}\n"
 "d.cancel=function(){if(t!==null)clearTimeout(t);t=null;pending=false;invokedLeading=false;lastArgs=null;};\n"
 "d.flush=function(){if(t!==null){clearTimeout(t);t=null;if(pending)invoke();}invokedLeading=false;return result;};\n"
 "return d;}\n"
 "module.exports={debounce};"),

("hjs-004",
 "`jsonPointer` exporting `get(doc, pointer)` and `set(doc, pointer, value)` implementing RFC 6901. "
 "The empty pointer refers to the whole document; tokens are separated by `/`; `~1` decodes to `/` "
 "and `~0` to `~`, in that order; a numeric token indexes an array and `-` on set appends to one. "
 "`get` returns undefined for a missing location and THROWS for a pointer that does not start with "
 "`/` and is not empty. `set` returns the document and creates missing intermediate objects.",
 "const {get,set}=require('./sol.js').jsonPointer||require('./sol.js');const a=require('assert');\n"
 "const doc={foo:['bar','baz'],'':0,'a/b':1,'c%d':2,'e^f':3,'m~n':4,' ':7,'k\"l':6};\n"
 "a.deepStrictEqual(get(doc,''),doc);\n"
 "a.deepStrictEqual(get(doc,'/foo'),['bar','baz']);\n"
 "a.strictEqual(get(doc,'/foo/0'),'bar');\n"
 "a.strictEqual(get(doc,'/'),0,'empty key');\n"
 "a.strictEqual(get(doc,'/a~1b'),1,'~1 decodes to slash');\n"
 "a.strictEqual(get(doc,'/m~0n'),4,'~0 decodes to tilde');\n"
 "a.strictEqual(get(doc,'/e^f'),3);\n"
 "a.strictEqual(get(doc,'/nope'),undefined);\n"
 "a.strictEqual(get(doc,'/foo/9'),undefined);\n"
 "a.throws(()=>get(doc,'foo'),'must throw on a pointer with no leading slash');\n"
 "const d2={a:{b:1}};set(d2,'/a/b',9);a.strictEqual(d2.a.b,9);\n"
 "set(d2,'/x/y',5);a.deepStrictEqual(d2.x,{y:5},'creates intermediates');\n"
 "const d3={arr:[1,2]};set(d3,'/arr/-',3);a.deepStrictEqual(d3.arr,[1,2,3],'- appends');\n"
 "set(d3,'/arr/0',9);a.deepStrictEqual(d3.arr,[9,2,3]);\n"
 "const d4={};set(d4,'/a~1b',1);a.strictEqual(d4['a/b'],1);\n"
 "console.log('OK');",
 "function dec(t){return t.split('~1').join('/').split('~0').join('~');}\n"
 "function toks(p){if(p==='')return [];\n"
 "if(p[0]!=='/')throw new Error('invalid pointer');\n"
 "return p.slice(1).split('/').map(dec);}\n"
 "function get(doc,pointer){let cur=doc;\n"
 "for(const t of toks(pointer)){\n"
 " if(cur===null||typeof cur!=='object')return undefined;\n"
 " if(Array.isArray(cur)){const i=Number(t);\n"
 "  if(!/^\\d+$/.test(t)||i>=cur.length)return undefined;cur=cur[i];}\n"
 " else{if(!Object.prototype.hasOwnProperty.call(cur,t))return undefined;cur=cur[t];}}\n"
 "return cur;}\n"
 "function set(doc,pointer,value){const ts=toks(pointer);\n"
 "if(!ts.length)return value;let cur=doc;\n"
 "for(let i=0;i<ts.length-1;i++){const t=ts[i];\n"
 " if(cur[t]===undefined||cur[t]===null||typeof cur[t]!=='object')cur[t]={};\n"
 " cur=cur[t];}\n"
 "const last=ts[ts.length-1];\n"
 "if(Array.isArray(cur)&&last==='-')cur.push(value);\n"
 "else if(Array.isArray(cur))cur[Number(last)]=value;\n"
 "else cur[last]=value;\n"
 "return doc;}\n"
 "module.exports={get,set,jsonPointer:{get,set}};"),

("hjs-005",
 "`deepMerge(target, ...sources)` merging plain objects recursively and returning a NEW object "
 "without mutating any input. Arrays are replaced, not concatenated. A source value of undefined "
 "does not overwrite; a source value of null does. It must be immune to prototype pollution: the "
 "keys `__proto__`, `constructor` and `prototype` are skipped entirely, and merging them must "
 "never alter Object.prototype. Non-plain objects such as Date are copied by reference.",
 "const {deepMerge}=require('./sol.js');const a=require('assert');\n"
 "const t={a:1,n:{x:1,y:2}};const s={n:{y:9,z:3},b:2};\n"
 "const r=deepMerge(t,s);\n"
 "a.deepStrictEqual(r,{a:1,n:{x:1,y:9,z:3},b:2});\n"
 "a.deepStrictEqual(t,{a:1,n:{x:1,y:2}},'must not mutate target');\n"
 "a.notStrictEqual(r.n,t.n);\n"
 "a.deepStrictEqual(deepMerge({a:[1,2]},{a:[3]}),{a:[3]},'arrays replace');\n"
 "a.deepStrictEqual(deepMerge({a:1},{a:undefined}),{a:1},'undefined does not overwrite');\n"
 "a.deepStrictEqual(deepMerge({a:1},{a:null}),{a:null},'null does overwrite');\n"
 "a.deepStrictEqual(deepMerge({a:1},{b:2},{c:3}),{a:1,b:2,c:3});\n"
 "const evil=JSON.parse('{\"__proto__\":{\"pwned\":1}}');\n"
 "deepMerge({},evil);\n"
 "a.strictEqual({}.pwned,undefined,'prototype pollution');\n"
 "a.strictEqual(Object.prototype.pwned,undefined);\n"
 "const evil2=JSON.parse('{\"constructor\":{\"prototype\":{\"pwned2\":1}}}');\n"
 "deepMerge({},evil2);a.strictEqual({}.pwned2,undefined);\n"
 "const d=new Date(1);const rr=deepMerge({},{d});a.strictEqual(rr.d,d,'Date by reference');\n"
 "console.log('OK');",
 "const BAD=new Set(['__proto__','constructor','prototype']);\n"
 "function isPlain(v){return v!==null&&typeof v==='object'&&!Array.isArray(v)&&"
 "(Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null);}\n"
 "function copy(dst,src){for(const k of Object.keys(src)){if(BAD.has(k))continue;\n"
 " const v=src[k];if(v===undefined)continue;\n"
 " if(isPlain(v)){const base=isPlain(dst[k])?dst[k]:{};const n={};copy(n,base);copy(n,v);dst[k]=n;}\n"
 " else dst[k]=v;}}\n"
 "function deepMerge(target,...sources){\n"
 "if(!isPlain(target))return target;\n"
 "const out={};copy(out,target);\n"
 "for(const s of sources){if(isPlain(s))copy(out,s);}\n"
 "return out;}\n"
 "module.exports={deepMerge};"),

("hjs-006",
 "class `Emitter` with `on(event, fn)` returning an unsubscribe function, `once(event, fn)`, "
 "`off(event, fn)`, and `emit(event, ...args)` returning the number of listeners actually invoked. "
 "A listener added DURING an emit must not be invoked by that same emit, and a listener removed "
 "during an emit must not be invoked afterwards in that emit. `once` listeners are removed before "
 "they run, so a `once` handler that re-emits the same event does not recurse. Listeners run in "
 "registration order and a throwing listener must not prevent the rest from running -- collect and "
 "rethrow the first error after the emit completes.",
 "const {Emitter}=require('./sol.js');const a=require('assert');\n"
 "const e=new Emitter();const log=[];\n"
 "const off1=e.on('x',v=>log.push('a'+v));\n"
 "e.on('x',v=>log.push('b'+v));\n"
 "a.strictEqual(e.emit('x',1),2);a.deepStrictEqual(log,['a1','b1']);\n"
 "off1();log.length=0;a.strictEqual(e.emit('x',2),1);a.deepStrictEqual(log,['b2']);\n"
 "const e2=new Emitter();const l2=[];\n"
 "e2.on('y',()=>{l2.push('first');e2.on('y',()=>l2.push('late'));});\n"
 "e2.emit('y');a.deepStrictEqual(l2,['first'],'listener added during emit ran');\n"
 "e2.emit('y');a.deepStrictEqual(l2,['first','first','late']);\n"
 "const e3=new Emitter();const l3=[];\n"
 "const h=()=>l3.push('h');\n"
 "e3.on('z',()=>{e3.off('z',h);});e3.on('z',h);\n"
 "e3.emit('z');a.deepStrictEqual(l3,[],'removed during emit still ran');\n"
 "const e4=new Emitter();let n=0;\n"
 "e4.once('w',()=>{n++;if(n<3)e4.emit('w');});\n"
 "e4.emit('w');a.strictEqual(n,1,'once recursed');\n"
 "const e5=new Emitter();const l5=[];\n"
 "e5.on('q',()=>{throw new Error('boom');});e5.on('q',()=>l5.push('ran'));\n"
 "a.throws(()=>e5.emit('q'),/boom/);a.deepStrictEqual(l5,['ran'],'later listener skipped');\n"
 "a.strictEqual(new Emitter().emit('none'),0);\n"
 "console.log('OK');",
 "class Emitter{constructor(){this.m=new Map();}\n"
 "on(ev,fn){if(!this.m.has(ev))this.m.set(ev,[]);this.m.get(ev).push(fn);\n"
 " return()=>this.off(ev,fn);}\n"
 "once(ev,fn){const w=(...a)=>{this.off(ev,w);return fn(...a);};w._orig=fn;\n"
 " return this.on(ev,w);}\n"
 "off(ev,fn){const l=this.m.get(ev);if(!l)return;\n"
 " const i=l.findIndex(f=>f===fn||f._orig===fn);if(i>=0)l.splice(i,1);}\n"
 "emit(ev,...args){const l=this.m.get(ev);if(!l||!l.length)return 0;\n"
 " const snap=l.slice();let n=0,err=null;\n"
 " for(const f of snap){const cur=this.m.get(ev);\n"
 "  if(!cur||cur.indexOf(f)===-1)continue;\n"
 "  n++;try{f(...args);}catch(e){if(!err)err=e;}}\n"
 " if(err)throw err;return n;}}\n"
 "module.exports={Emitter};"),

("hjs-007",
 "`singleFlight(loader)` returning a function `load(key)` that calls the async `loader(key)` at "
 "most once for concurrent callers of the same key -- all of them receive the same promise. Once a "
 "call settles, the entry is dropped so a later call re-runs the loader. A rejection is delivered "
 "to every waiter and must not be cached. Expose `load.inflight` as the current number of pending "
 "keys.",
 "const {singleFlight}=require('./sol.js');const a=require('assert');\n"
 "(async()=>{\n"
 " let n=0;const load=singleFlight(async k=>{n++;await new Promise(r=>setTimeout(r,20));\n"
 "  if(k==='bad')throw new Error('nope');return k+n;});\n"
 " const [x,y]=await Promise.all([load('a'),load('a')]);\n"
 " a.strictEqual(n,1,'loader ran twice');a.strictEqual(x,y);\n"
 " const z=await load('a');a.strictEqual(n,2,'entry not dropped after settle');\n"
 " const rs=await Promise.allSettled([load('bad'),load('bad')]);\n"
 " a.strictEqual(rs[0].status,'rejected');a.strictEqual(rs[1].status,'rejected');\n"
 " const before=n;await Promise.allSettled([load('bad')]);\n"
 " a.strictEqual(n,before+1,'rejection was cached');\n"
 " const p1=load('c'),p2=load('d');\n"
 " a.strictEqual(load.inflight,2,'inflight '+load.inflight);\n"
 " await Promise.all([p1,p2]);a.strictEqual(load.inflight,0);\n"
 " console.log('OK');})().catch(e=>{console.error(e);process.exit(1);});",
 "function singleFlight(loader){const m=new Map();\n"
 "const load=key=>{if(m.has(key))return m.get(key);\n"
 " const p=Promise.resolve().then(()=>loader(key)).finally(()=>{m.delete(key);load.inflight=m.size;});\n"
 " m.set(key,p);load.inflight=m.size;return p;};\n"
 "load.inflight=0;return load;}\n"
 "module.exports={singleFlight};"),

("hjs-008",
 "`sqlTag` used as a tagged template, e.g. sqlTag`SELECT * FROM t WHERE a=${1} AND b=${x}`, "
 "returning `{text, values}` where each interpolation becomes a positional placeholder `$1`, `$2` "
 "and so on and `values` holds them in order. An interpolated value that is itself a result of "
 "`sqlTag` is INLINED: its text is spliced in with its placeholders renumbered and its values "
 "merged. An interpolated array becomes a parenthesised comma-separated list of placeholders. "
 "Repeated occurrences of the same value still get separate placeholders.",
 "const {sqlTag}=require('./sol.js');const a=require('assert');\n"
 "let q=sqlTag`SELECT * FROM t WHERE a=${1} AND b=${'x'}`;\n"
 "a.strictEqual(q.text,'SELECT * FROM t WHERE a=$1 AND b=$2');\n"
 "a.deepStrictEqual(q.values,[1,'x']);\n"
 "q=sqlTag`SELECT 1`;a.strictEqual(q.text,'SELECT 1');a.deepStrictEqual(q.values,[]);\n"
 "q=sqlTag`a=${5} b=${5}`;a.deepStrictEqual(q.values,[5,5]);\n"
 "a.strictEqual(q.text,'a=$1 b=$2');\n"
 "q=sqlTag`WHERE id IN ${[1,2,3]}`;\n"
 "a.strictEqual(q.text,'WHERE id IN ($1, $2, $3)');a.deepStrictEqual(q.values,[1,2,3]);\n"
 "const inner=sqlTag`b=${2} OR c=${3}`;\n"
 "q=sqlTag`SELECT * WHERE a=${1} AND (${inner}) AND d=${4}`;\n"
 "a.strictEqual(q.text,'SELECT * WHERE a=$1 AND (b=$2 OR c=$3) AND d=$4');\n"
 "a.deepStrictEqual(q.values,[1,2,3,4]);\n"
 "const i2=sqlTag`x=${9}`;const q2=sqlTag`${i2} AND ${i2}`;\n"
 "a.strictEqual(q2.text,'x=$1 AND x=$2');a.deepStrictEqual(q2.values,[9,9]);\n"
 "console.log('OK');",
 "const MARK=Symbol('sql');\n"
 "function sqlTag(strings,...vals){const values=[];let text='';\n"
 "const ph=v=>{values.push(v);return '$'+values.length;};\n"
 "for(let i=0;i<strings.length;i++){text+=strings[i];\n"
 " if(i<vals.length){const v=vals[i];\n"
 "  if(v&&v[MARK]){let t=v.text.replace(/\\$(\\d+)/g,(m,d)=>ph(v.values[Number(d)-1]));text+=t;}\n"
 "  else if(Array.isArray(v))text+='('+v.map(ph).join(', ')+')';\n"
 "  else text+=ph(v);}}\n"
 "return {text,values,[MARK]:true};}\n"
 "module.exports={sqlTag};"),

("hjs-009",
 "`observe(target, onChange)` returning a Proxy over a nested plain object that calls "
 "`onChange(path, value, oldValue)` on every property write and delete, where `path` is an array of "
 "keys from the root. Nested objects assigned later are also observed. A write that does not change "
 "the value (SameValueZero) fires nothing. Deleting reports the new value as undefined. Reading "
 "returns proxies for objects but the plain value for primitives, and array mutation via push must "
 "report the index write.",
 "const {observe}=require('./sol.js');const a=require('assert');\n"
 "const log=[];const o=observe({a:1,n:{b:2},arr:[1]},(p,v,old)=>log.push([p.join('.'),v,old]));\n"
 "o.a=2;a.deepStrictEqual(log,[['a',2,1]]);\n"
 "log.length=0;o.a=2;a.deepStrictEqual(log,[],'no-op write fired');\n"
 "log.length=0;o.n.b=5;a.deepStrictEqual(log,[['n.b',5,2]]);\n"
 "log.length=0;o.n={c:1};a.deepStrictEqual(log[0][0],'n');\n"
 "log.length=0;o.n.c=7;a.deepStrictEqual(log,[['n.c',7,1]],'newly assigned object not observed');\n"
 "log.length=0;delete o.a;a.deepStrictEqual(log,[['a',undefined,2]]);\n"
 "log.length=0;o.arr.push(9);\n"
 "a.ok(log.some(e=>e[0]==='arr.1'&&e[1]===9),'push index not reported: '+JSON.stringify(log));\n"
 "a.strictEqual(o.arr[1],9);a.strictEqual(typeof o.a,'undefined');\n"
 "console.log('OK');",
 "function observe(target,onChange){\n"
 "const wrap=(obj,path)=>new Proxy(obj,{\n"
 " get(t,k,r){const v=Reflect.get(t,k,r);\n"
 "  if(v&&typeof v==='object'&&typeof k!=='symbol')return wrap(v,path.concat(k));\n"
 "  return v;},\n"
 " set(t,k,v,r){const old=t[k];\n"
 "  const same=old===v?(old!==0||1/old===1/v):(old!==old&&v!==v);\n"
 "  const had=Object.prototype.hasOwnProperty.call(t,k);\n"
 "  const ok=Reflect.set(t,k,v);\n"
 "  if(typeof k!=='symbol'&&(!had||!same))onChange(path.concat(k),v,old);\n"
 "  return ok;},\n"
 " deleteProperty(t,k){const old=t[k];const had=Object.prototype.hasOwnProperty.call(t,k);\n"
 "  const ok=Reflect.deleteProperty(t,k);\n"
 "  if(had&&typeof k!=='symbol')onChange(path.concat(k),undefined,old);\n"
 "  return ok;}});\n"
 "return wrap(target,[]);}\n"
 "module.exports={observe};"),

("hjs-010",
 "`chunkAsync(source, size)` returning an async generator that yields arrays of up to `size` items "
 "from an async or sync iterable, yielding a final short chunk if any items remain and nothing at "
 "all for an empty source. It must be LAZY: it pulls at most `size` items ahead of what the "
 "consumer has requested, so it works on an infinite source, and it must call the source's "
 "`return()` if the consumer stops early.",
 "const {chunkAsync}=require('./sol.js');const a=require('assert');\n"
 "(async()=>{\n"
 " const take=async(it,n)=>{const out=[];for await(const c of it){out.push(c);if(out.length>=n)break;}return out;};\n"
 " async function* g(n){for(let i=0;i<n;i++)yield i;}\n"
 " a.deepStrictEqual(await take(chunkAsync(g(5),2),99),[[0,1],[2,3],[4]]);\n"
 " a.deepStrictEqual(await take(chunkAsync(g(0),2),99),[]);\n"
 " a.deepStrictEqual(await take(chunkAsync([1,2,3],3),99),[[1,2,3]],'sync iterable');\n"
 " let pulled=0,closed=false;\n"
 " const inf={[Symbol.asyncIterator](){return{next:async()=>({value:pulled++,done:false}),\n"
 "  return:async()=>{closed=true;return{done:true};}};}};\n"
 " const got=await take(chunkAsync(inf,3),2);\n"
 " a.deepStrictEqual(got,[[0,1,2],[3,4,5]]);\n"
 " a.ok(pulled<=9,'over-pulled: '+pulled);\n"
 " await new Promise(r=>setTimeout(r,10));\n"
 " a.ok(closed,'source not closed on early exit');\n"
 " console.log('OK');})().catch(e=>{console.error(e);process.exit(1);});",
 "async function* chunkAsync(source,size){let buf=[];\n"
 "const it=source[Symbol.asyncIterator]?source[Symbol.asyncIterator]():source[Symbol.iterator]();\n"
 "try{while(true){const r=await it.next();\n"
 "  if(r.done)break;\n"
 "  buf.push(r.value);\n"
 "  if(buf.length===size){yield buf;buf=[];}}\n"
 " if(buf.length)yield buf;}\n"
 "finally{if(typeof it.return==='function')await it.return();}}\n"
 "module.exports={chunkAsync};"),

("hjs-011",
 "`memoize(fn, keyFn)` caching by a key. When `keyFn` is absent, a single-argument call with an "
 "OBJECT argument is cached in a WeakMap keyed by that object so it does not leak, and calls with "
 "primitive arguments are cached in a Map keyed by the argument. Distinct objects that look alike "
 "are distinct keys. A call that throws is not cached. Expose `.cache` misses via a `.calls` "
 "counter of how many times the underlying fn ran, and a `.clear()`.",
 "const {memoize}=require('./sol.js');const a=require('assert');\n"
 "let n=0;const f=memoize(x=>{n++;if(x==='bad')throw new Error('e');\n"
 " return typeof x==='object'?x.v*2:x*2;});\n"
 "a.strictEqual(f(2),4);a.strictEqual(f(2),4);a.strictEqual(n,1);\n"
 "a.strictEqual(f(3),6);a.strictEqual(n,2);a.strictEqual(f.calls,2);\n"
 "const o={v:5};a.strictEqual(f(o),10);a.strictEqual(f(o),10);a.strictEqual(f.calls,3);\n"
 "a.strictEqual(f({v:5}),10);a.strictEqual(f.calls,4,'lookalike object shared a key');\n"
 "a.throws(()=>f('bad'));a.throws(()=>f('bad'));\n"
 "a.strictEqual(f.calls,6,'a throw was cached');\n"
 "f.clear();a.strictEqual(f(2),4);a.strictEqual(f.calls,7);\n"
 "let m=0;const g=memoize((a1,b1)=>{m++;return a1+b1;},(a1,b1)=>a1+':'+b1);\n"
 "a.strictEqual(g(1,2),3);a.strictEqual(g(1,2),3);a.strictEqual(m,1);\n"
 "a.strictEqual(g(2,1),3);a.strictEqual(m,2);\n"
 "a.strictEqual(f(0),0);a.strictEqual(f(0),0);\n"
 "console.log('OK');",
 "function memoize(fn,keyFn){let map=new Map(),wm=new WeakMap();\n"
 "const m=function(...args){\n"
 " let store,key;\n"
 " if(keyFn){store=map;key=keyFn.apply(this,args);}\n"
 " else if(args.length===1&&args[0]!==null&&(typeof args[0]==='object'||typeof args[0]==='function'))"
 "{store=wm;key=args[0];}\n"
 " else{store=map;key=args.length===1?args[0]:JSON.stringify(args);}\n"
 " if(store.has(key))return store.get(key);\n"
 " m.calls++;const v=fn.apply(this,args);store.set(key,v);return v;};\n"
 "m.calls=0;m.clear=()=>{map=new Map();wm=new WeakMap();};\n"
 "return m;}\n"
 "module.exports={memoize};"),

("hjs-012",
 "`zipLongest(fill, ...iterables)` returning a LAZY iterator of arrays, one per position, running "
 "until the longest input is exhausted and substituting `fill` for inputs that have already ended. "
 "With no iterables it yields nothing. It must be LAZY -- it pulls exactly one item per live input "
 "per yielded row, never draining an input up front -- and once an input reports done it must "
 "never be pulled again.",
 "const {zipLongest}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual([...zipLongest(0,[1,2,3],[4,5])],[[1,4],[2,5],[3,0]]);\n"
 "a.deepStrictEqual([...zipLongest(null)],[]);\n"
 "a.deepStrictEqual([...zipLongest(0,[],[])],[]);\n"
 "a.deepStrictEqual([...zipLongest('x',['a'])],[['a']]);\n"
 "let extra=0;\n"
 "function* counted(){yield 1;yield 2;extra++;}\n"
 "a.deepStrictEqual([...zipLongest(9,counted(),[1,2,3,4])],[[1,1],[2,2],[9,3],[9,4]]);\n"
 "a.strictEqual(extra,1,'kept pulling a finished iterator');\n"
 "let pulled=0;\n"
 "function* watched(){while(pulled<10){pulled++;yield pulled;}}\n"
 "const it=zipLongest(0,watched(),[4,5,6]);\n"
 "a.deepStrictEqual(it.next().value,[1,4]);\n"
 "a.strictEqual(pulled,1,'not lazy: pulled '+pulled);\n"
 "a.deepStrictEqual(it.next().value,[2,5]);\n"
 "a.strictEqual(pulled,2,'not lazy: pulled '+pulled);\n"
 "console.log('OK');",
 "function* zipLongest(fill,...iterables){\n"
 "const its=iterables.map(x=>x[Symbol.iterator]());\n"
 "if(!its.length)return;\n"
 "const done=its.map(()=>false);\n"
 "while(true){const row=[];let alive=0;\n"
 " for(let i=0;i<its.length;i++){\n"
 "  if(done[i]){row.push(fill);continue;}\n"
 "  const r=its[i].next();\n"
 "  if(r.done){done[i]=true;row.push(fill);}else{row.push(r.value);alive++;}}\n"
 " if(!alive)return;\n"
 " yield row;}}\n"
 "module.exports={zipLongest};"),

("hjs-013",
 "`parseQuery(qs)` and `buildQuery(obj)` round-tripping a query string with PHP/qs-style bracket "
 "nesting. `a=1&b=2` gives {a:'1',b:'2'}; `a[]=1&a[]=2` gives {a:['1','2']}; `a[b][c]=1` gives "
 "nested objects; `a[0]=x&a[1]=y` gives an array; a repeated bare key becomes an array; percent "
 "encoding is decoded and `+` is a space; a key with no `=` maps to an empty string. `buildQuery` "
 "produces a string that `parseQuery` maps back to the same structure, with keys sorted and values "
 "percent-encoded. A leading `?` is accepted and ignored.",
 "const {parseQuery,buildQuery}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(parseQuery(''),{});\n"
 "a.deepStrictEqual(parseQuery('?a=1&b=2'),{a:'1',b:'2'});\n"
 "a.deepStrictEqual(parseQuery('a[]=1&a[]=2'),{a:['1','2']});\n"
 "a.deepStrictEqual(parseQuery('a[b][c]=1'),{a:{b:{c:'1'}}});\n"
 "a.deepStrictEqual(parseQuery('a[0]=x&a[1]=y'),{a:['x','y']});\n"
 "a.deepStrictEqual(parseQuery('a=1&a=2'),{a:['1','2']},'repeated bare key');\n"
 "a.deepStrictEqual(parseQuery('a=hello+world'),{a:'hello world'});\n"
 "a.deepStrictEqual(parseQuery('a=%C3%A9'),{a:'\\u00e9'});\n"
 "a.deepStrictEqual(parseQuery('flag'),{flag:''});\n"
 "const round=o=>parseQuery(buildQuery(o));\n"
 "for(const o of [{a:'1'},{a:['1','2']},{a:{b:{c:'1'}}},{z:'1',a:'2'},{a:'a b&c=d'}])\n"
 "  a.deepStrictEqual(round(o),o,JSON.stringify(o));\n"
 "a.ok(buildQuery({z:'1',a:'2'}).indexOf('a=')===0,'keys not sorted');\n"
 "console.log('OK');",
 "const dec=s=>decodeURIComponent(String(s).split('+').join(' '));\n"
 "function parseQuery(qs){const out={};\n"
 "if(!qs)return out;if(qs[0]==='?')qs=qs.slice(1);if(!qs)return out;\n"
 "for(const pair of qs.split('&')){if(!pair)continue;\n"
 " const i=pair.indexOf('=');\n"
 " const rawk=i<0?pair:pair.slice(0,i);const rawv=i<0?'':pair.slice(i+1);\n"
 " const k=dec(rawk),v=dec(rawv);\n"
 " const m=k.match(/^([^\\[]+)((\\[[^\\]]*\\])*)$/);\n"
 " if(!m){out[k]=v;continue;}\n"
 " const parts=[m[1]];\n"
 " const rest=m[2]||'';\n"
 " const re=/\\[([^\\]]*)\\]/g;let mm;\n"
 " while((mm=re.exec(rest)))parts.push(mm[1]);\n"
 " let cur=out;\n"
 " for(let j=0;j<parts.length;j++){\n"
 "  const p=parts[j];const last=j===parts.length-1;\n"
 "  if(p===''){if(!Array.isArray(cur.__a))cur.__a=[];\n"
 "   if(last){cur.__a.push(v);}else{const n={};cur.__a.push(n);cur=n;}continue;}\n"
 "  if(last){\n"
 "   if(Object.prototype.hasOwnProperty.call(cur,p)){\n"
 "    if(Array.isArray(cur[p]))cur[p].push(v);else cur[p]=[cur[p],v];}\n"
 "   else cur[p]=v;}\n"
 "  else{const nextNum=/^\\d+$/.test(parts[j+1]);\n"
 "   if(typeof cur[p]!=='object'||cur[p]===null)cur[p]=nextNum?[]:{};\n"
 "   cur=cur[p];}}\n"
 " if(cur&&cur.__a){}\n"
 "}\n"
 "const fix=o=>{if(Array.isArray(o))return o.map(fix);\n"
 " if(o&&typeof o==='object'){\n"
 "  if(Array.isArray(o.__a)&&Object.keys(o).length===1)return o.__a.map(fix);\n"
 "  const ks=Object.keys(o);\n"
 "  if(ks.length&&ks.every((k,i)=>k===String(i)))return ks.map(k=>fix(o[k]));\n"
 "  const r={};for(const k of ks)r[k]=fix(o[k]);return r;}\n"
 " return o;};\n"
 "const res=fix(out);\n"
 "for(const k of Object.keys(out))if(Array.isArray(out[k])&&out[k].__a)delete out[k].__a;\n"
 "return res;}\n"
 "const enc=encodeURIComponent;\n"
 "function buildQuery(obj){const parts=[];\n"
 "const walk=(prefix,v)=>{\n"
 " if(Array.isArray(v)){v.forEach(x=>walk(prefix+'[]',x));}\n"
 " else if(v&&typeof v==='object'){\n"
 "  for(const k of Object.keys(v).sort())walk(prefix+'['+k+']',v[k]);}\n"
 " else parts.push(enc(prefix).split('%5B').join('[').split('%5D').join(']')+'='+enc(String(v)));};\n"
 "for(const k of Object.keys(obj).sort())walk(k,obj[k]);\n"
 "return parts.join('&');}\n"
 "module.exports={parseQuery,buildQuery};"),

("hjs-014",
 "`createStore(reducer, initial)` -- a Redux-shaped store with `getState()`, `dispatch(action)` and "
 "`subscribe(fn)` returning an unsubscribe. Dispatching from inside a reducer must throw. A "
 "subscriber list is snapshotted per dispatch, so subscribing during a notification does not run "
 "this round and unsubscribing during a notification does prevent the later call. Dispatching from "
 "inside a subscriber is allowed and processes to completion before the outer notification "
 "continues. `getState()` inside a subscriber already sees the new state.",
 "const {createStore}=require('./sol.js');const a=require('assert');\n"
 "const r=(s,ac)=>ac.type==='inc'?s+1:ac.type==='add'?s+ac.n:s;\n"
 "const st=createStore(r,0);\n"
 "a.strictEqual(st.getState(),0);\n"
 "st.dispatch({type:'inc'});a.strictEqual(st.getState(),1);\n"
 "const seen=[];const un=st.subscribe(()=>seen.push(st.getState()));\n"
 "st.dispatch({type:'inc'});a.deepStrictEqual(seen,[2],'state stale in subscriber');\n"
 "un();st.dispatch({type:'inc'});a.deepStrictEqual(seen,[2]);\n"
 "const st2=createStore((s,ac)=>{if(ac.type==='bad')st2.dispatch({type:'inc'});return s;},0);\n"
 "a.throws(()=>st2.dispatch({type:'bad'}),'dispatch inside reducer must throw');\n"
 "const st3=createStore(r,0);const l3=[];\n"
 "st3.subscribe(()=>{l3.push('a');st3.subscribe(()=>l3.push('late'));});\n"
 "st3.subscribe(()=>l3.push('b'));\n"
 "st3.dispatch({type:'inc'});\n"
 "a.deepStrictEqual(l3,['a','b'],'subscribed during notify ran: '+l3);\n"
 "l3.length=0;st3.dispatch({type:'inc'});\n"
 "a.deepStrictEqual(l3,['a','b','late']);\n"
 "const st4=createStore(r,0);const l4=[];let u2;\n"
 "st4.subscribe(()=>{l4.push('one');u2();});u2=st4.subscribe(()=>l4.push('two'));\n"
 "st4.dispatch({type:'inc'});\n"
 "a.deepStrictEqual(l4,['one'],'unsubscribed during notify still ran');\n"
 "const st5=createStore(r,0);const l5=[];let once=true;\n"
 "st5.subscribe(()=>{l5.push(st5.getState());if(once){once=false;st5.dispatch({type:'add',n:10});}});\n"
 "st5.dispatch({type:'inc'});\n"
 "a.deepStrictEqual(l5,[1,11],'nested dispatch: '+l5);\n"
 "console.log('OK');",
 "function createStore(reducer,initial){let state=initial;let subs=[];let inReducer=false;\n"
 "const getState=()=>state;\n"
 "const subscribe=fn=>{let live=true;subs=subs.concat([fn]);\n"
 " return()=>{if(!live)return;live=false;subs=subs.filter(f=>f!==fn);};};\n"
 "const dispatch=action=>{\n"
 " if(inReducer)throw new Error('dispatch from reducer');\n"
 " inReducer=true;\n"
 " try{state=reducer(state,action);}finally{inReducer=false;}\n"
 " const snap=subs;\n"
 " for(const f of snap){if(subs.indexOf(f)===-1)continue;f();}\n"
 " return action;};\n"
 "return {getState,dispatch,subscribe};}\n"
 "module.exports={createStore};"),

("hjs-015",
 "`toposortTasks(tasks)` where `tasks` maps a name to `{deps: [...], run: async () => value}`. "
 "Run every task after its dependencies, with independent tasks running CONCURRENTLY, and resolve "
 "to a map of name to returned value. A task's `run` receives an object of its dependencies' "
 "resolved values keyed by name. Reject with an Error whose message contains `cycle` on a "
 "dependency cycle, and one mentioning the missing name on an unknown dependency. If a task "
 "rejects, tasks that do not depend on it still complete, and the returned promise rejects with "
 "that error.",
 "const {toposortTasks}=require('./sol.js');const a=require('assert');\n"
 "(async()=>{\n"
 " const order=[];let cur=0,peak=0;\n"
 " const mk=(name,deps,ms)=>[name,{deps,run:async d=>{cur++;peak=Math.max(peak,cur);\n"
 "  order.push(name);await new Promise(r=>setTimeout(r,ms));cur--;\n"
 "  return name+':'+Object.keys(d).sort().join(',');}}];\n"
 " const t=Object.fromEntries([mk('a',[],20),mk('b',[],20),mk('c',['a','b'],5)]);\n"
 " const res=await toposortTasks(t);\n"
 " a.strictEqual(res.c,'c:a,b');a.strictEqual(peak,2,'a and b did not run concurrently');\n"
 " a.strictEqual(order[2],'c');\n"
 " await a.rejects(toposortTasks({x:{deps:['y'],run:async()=>1},y:{deps:['x'],run:async()=>1}}),/cycle/);\n"
 " await a.rejects(toposortTasks({x:{deps:['nope'],run:async()=>1}}),/nope/);\n"
 " let ran=false;\n"
 " const bad={p:{deps:[],run:async()=>{throw new Error('boom');}},\n"
 "  q:{deps:['p'],run:async()=>{ran=true;return 1;}},\n"
 "  r:{deps:[],run:async()=>{await new Promise(x=>setTimeout(x,10));ran=ran;return 2;}}};\n"
 " await a.rejects(toposortTasks(bad),/boom/);\n"
 " a.strictEqual(ran,false,'dependent of a failed task ran');\n"
 " a.deepStrictEqual(await toposortTasks({}),{});\n"
 " console.log('OK');})().catch(e=>{console.error(e);process.exit(1);});",
 "function toposortTasks(tasks){\n"
 "const names=Object.keys(tasks);\n"
 "for(const n of names)for(const d of tasks[n].deps)\n"
 " if(!Object.prototype.hasOwnProperty.call(tasks,d))\n"
 "  return Promise.reject(new Error('unknown dependency '+d));\n"
 "const state={};\n"
 "const detect=(n,seen)=>{if(seen.has(n))return true;seen.add(n);\n"
 " for(const d of tasks[n].deps)if(detect(d,new Set(seen)))return true;return false;};\n"
 "for(const n of names)if(detect(n,new Set()))return Promise.reject(new Error('cycle at '+n));\n"
 "const results={};\n"
 "const go=n=>{if(state[n])return state[n];\n"
 " state[n]=Promise.all(tasks[n].deps.map(go)).then(vals=>{\n"
 "  const arg={};tasks[n].deps.forEach((d,i)=>{arg[d]=vals[i];});\n"
 "  return tasks[n].run(arg);}).then(v=>{results[n]=v;return v;});\n"
 " return state[n];};\n"
 "const all=names.map(go);\n"
 "return Promise.allSettled(all).then(rs=>{\n"
 " const bad=rs.find(r=>r.status==='rejected');\n"
 " if(bad)throw bad.reason;\n"
 " return results;});}\n"
 "module.exports={toposortTasks};"),
]

# ---------------------------------------------------------------- TS (15)
TS = [
 ('hts-001',
  'export a type `DeepReadonly<T>` making every property readonly at every depth. Arrays become `readonly` arrays of DeepReadonly elements, tuples keep their arity and label positions, functions and primitives are left exactly as they are, and a `Date` is not recursed into. It must terminate on a recursive interface.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport type { DeepReadonly } from './sol';\n\ninterface Node { v: number; next: Node | null }\ninterface Shape {\n  a: number;\n  o: { b: string; c: { d: boolean } };\n  arr: number[];\n  tup: [number, string];\n  fn: (x: number) => string;\n  when: Date;\n  maybe?: { z: number };\n}\ntype R = DeepReadonly<Shape>;\ntype _1 = Expect<Eq<R['a'], number>>;\ntype _2 = Expect<Eq<R['o'], { readonly b: string; readonly c: { readonly d: boolean } }>>;\ntype _3 = Expect<Eq<R['arr'], readonly number[]>>;\ntype _4 = Expect<Eq<R['tup'], readonly [number, string]>>;\ntype _5 = Expect<Eq<R['fn'], (x: number) => string>>;\ntype _6 = Expect<Eq<R['when'], Date>>;\ntype _7 = Expect<Eq<R['maybe'], { readonly z: number } | undefined>>;\ntype _8 = Expect<Eq<DeepReadonly<Node>['next'], DeepReadonly<Node> | null>>;\n\nconst v: R = { a: 1, o: { b: 'x', c: { d: true } }, arr: [1], tup: [1, 'a'], fn: () => 'x', when: new Date() };\n// @ts-expect-error assigning to a deeply readonly property must fail\nv.o.c.d = false;\n// @ts-expect-error a readonly array has no push\nv.arr.push(2);\nconsole.log('OK');\n",
  '\nexport type DeepReadonly<T> =\n  T extends (...args: any[]) => any ? T\n  : T extends Date ? T\n  : T extends ReadonlyArray<infer E>\n    ? (T extends readonly [any, ...any[]]\n        ? { readonly [K in keyof T]: DeepReadonly<T[K]> }\n        : readonly DeepReadonly<E>[])\n  : T extends object ? { readonly [K in keyof T]: DeepReadonly<T[K]> }\n  : T;\n'),

 ('hts-002',
  'export a type `Paths<T>` producing the union of every dotted path into an object type, including intermediate paths, and `PathValue<T, P>` giving the type at a path. Arrays are leaf values, not indexed. Optional properties yield their path with the undefined stripped from the intermediate lookup but kept on the leaf. `Paths` of a non-object is `never`.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport type { Paths, PathValue } from './sol';\n\ninterface T {\n  a: number;\n  b: { c: string; d: { e: boolean } };\n  arr: number[];\n  opt?: { q: number };\n}\ntype P = Paths<T>;\ntype _1 = Expect<Eq<P, 'a' | 'b' | 'b.c' | 'b.d' | 'b.d.e' | 'arr' | 'opt' | 'opt.q'>>;\ntype _2 = Expect<Eq<PathValue<T, 'a'>, number>>;\ntype _3 = Expect<Eq<PathValue<T, 'b.d.e'>, boolean>>;\ntype _4 = Expect<Eq<PathValue<T, 'arr'>, number[]>>;\ntype _5 = Expect<Eq<PathValue<T, 'opt.q'>, number>>;\ntype _6 = Expect<Eq<Paths<number>, never>>;\n\ndeclare function at<O, K extends Paths<O>>(o: O, k: K): PathValue<O, K>;\n// Type-checked but never executed: `declare` emits no JavaScript, so calling\n// these for real would be a runtime crash rather than a type test.\nfunction _typeOnly(o: T) {\n  const n: number = at(o, 'a');\n  const bo: boolean = at(o, 'b.d.e');\n  // @ts-expect-error not a valid path\n  at(o, 'b.nope');\n  return [n, bo];\n}\nconsole.log('OK');\n",
  '\ntype Prim = string | number | boolean | bigint | symbol | null | undefined;\nexport type Paths<T> =\n  T extends Prim ? never\n  : T extends ReadonlyArray<any> ? never\n  : T extends object\n    ? { [K in keyof T & string]:\n          NonNullable<T[K]> extends infer V\n            ? V extends Prim | ReadonlyArray<any> ? K : K | `${K}.${Paths<V> & string}`\n            : never\n      }[keyof T & string]\n    : never;\nexport type PathValue<T, P extends string> =\n  P extends `${infer H}.${infer R}`\n    ? H extends keyof T ? PathValue<NonNullable<T[H]>, R> : never\n    : P extends keyof T ? T[P] : never;\n'),

 ('hts-003',
  'export a class `Bus<E extends Record<string, unknown>>` whose `on<K extends keyof E>(k, fn)` takes a handler receiving exactly `E[K]`, whose `emit<K extends keyof E>(k, payload: E[K])` type-checks the payload against the event, and where an event whose payload type is `void` is emitted with NO second argument while every other event REQUIRES one. `on` returns an unsubscribe function. It must work at runtime too.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { Bus } from './sol';\n\ntype E = { tick: void; msg: { text: string }; n: number };\nconst b = new Bus<E>();\nconst seen: unknown[] = [];\nconst off = b.on('msg', (p) => { const t: string = p.text; seen.push(t); });\nb.on('tick', () => seen.push('tick'));\nb.on('n', (v) => { const x: number = v; seen.push(x); });\n\nb.emit('msg', { text: 'hi' });\nb.emit('tick');\nb.emit('n', 7);\noff();\nb.emit('msg', { text: 'gone' });\n\n// Never invoked: these must fail to COMPILE, and executing them would also\n// mutate `seen` and invalidate the runtime assertion below.\nfunction _mustNotCompile() {\n  // @ts-expect-error payload shape is wrong\n  b.emit('msg', { text: 1 });\n  // @ts-expect-error a non-void event requires a payload\n  b.emit('n');\n  // @ts-expect-error a void event takes no payload\n  b.emit('tick', 1);\n  // @ts-expect-error unknown event\n  b.emit('nope', 1);\n  // @ts-expect-error the handler parameter is not any\n  b.on('n', (v) => { const s: string = v; return s; });\n}\n\nconst assert = require('assert');\nassert.deepStrictEqual(seen, ['hi', 'tick', 7]);\nconsole.log('OK');\n",
  '\ntype Handler<P> = (payload: P) => void;\nexport class Bus<E extends Record<string, unknown>> {\n  private m = new Map<keyof E, Handler<any>[]>();\n  on<K extends keyof E>(k: K, fn: Handler<E[K]>): () => void {\n    const l = this.m.get(k) ?? [];\n    l.push(fn);\n    this.m.set(k, l);\n    return () => {\n      const cur = this.m.get(k);\n      if (!cur) return;\n      const i = cur.indexOf(fn);\n      if (i >= 0) cur.splice(i, 1);\n    };\n  }\n  emit<K extends keyof E>(...args: E[K] extends void ? [k: K] : [k: K, payload: E[K]]): void {\n    const [k, payload] = args as [K, E[K]];\n    for (const fn of (this.m.get(k) ?? []).slice()) fn(payload);\n  }\n}\n'),

 ('hts-004',
  'export a function `match` performing exhaustive matching over a discriminated union on its `kind` field: `match(value, handlers)` where `handlers` must supply one function per variant, each receiving the NARROWED variant, and returns the union of their return types. Omitting a variant must be a compile error, and supplying a handler for a variant that does not exist must also be a compile error.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { match } from './sol';\n\ntype Shape =\n  | { kind: 'circle'; r: number }\n  | { kind: 'rect'; w: number; h: number }\n  | { kind: 'text'; s: string };\n\nconst area = (s: Shape) => match(s, {\n  circle: (c) => 3 * c.r * c.r,\n  rect: (r) => r.w * r.h,\n  text: (t) => t.s.length,\n});\ntype _1 = Expect<Eq<ReturnType<typeof area>, number>>;\n\nconst mixed = (s: Shape) => match(s, {\n  circle: (c) => c.r,\n  rect: () => 'rect' as const,\n  text: (t) => t.s,\n});\ntype _2 = Expect<Eq<ReturnType<typeof mixed>, number | 'rect' | string>>;\n\n// @ts-expect-error missing the text variant\nmatch({ kind: 'circle', r: 1 } as Shape, { circle: (c) => c.r, rect: (r) => r.w });\n// @ts-expect-error no such variant\nmatch({ kind: 'circle', r: 1 } as Shape, { circle: (c) => c.r, rect: (r) => r.w, text: (t) => t.s, blob: () => 0 });\n// @ts-expect-error the handler parameter is narrowed, so .w is not on a circle\nmatch({ kind: 'circle', r: 1 } as Shape, { circle: (c) => c.w, rect: (r) => r.w, text: (t) => t.s });\n\nconst assert = require('assert');\nassert.strictEqual(area({ kind: 'rect', w: 2, h: 3 }), 6);\nassert.strictEqual(area({ kind: 'text', s: 'abcd' }), 4);\nconsole.log('OK');\n",
  "\ntype Disc = { kind: string };\ntype Narrow<U extends Disc, K extends U['kind']> = Extract<U, { kind: K }>;\nexport function match<U extends Disc, H extends { [K in U['kind']]: (v: Narrow<U, K>) => unknown }>(\n  value: U,\n  handlers: H & { [K in Exclude<keyof H, U['kind']>]: never },\n): { [K in U['kind']]: ReturnType<H[K]> }[U['kind']] {\n  const fn = (handlers as Record<string, (v: unknown) => unknown>)[value.kind];\n  return fn(value) as never;\n}\n"),

 ('hts-005',
  "export a `Builder` such that `builder<Config>()` starts empty, `.set('key', value)` records a key with a value type-checked against Config, and `.build()` is ONLY callable once every REQUIRED key of Config has been set -- optional keys may be omitted. Calling `.build()` early must be a compile error, setting an unknown key or a wrongly-typed value must be a compile error, and `.build()` returns a fully typed Config.",
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { builder } from './sol';\n\ninterface Config { host: string; port: number; debug?: boolean }\n\nconst c = builder<Config>().set('host', 'h').set('port', 1).build();\ntype _1 = Expect<Eq<typeof c, Config>>;\n\nconst c2 = builder<Config>().set('port', 1).set('debug', true).set('host', 'h').build();\n\n// @ts-expect-error port has not been set yet\nbuilder<Config>().set('host', 'h').build();\n// @ts-expect-error nothing has been set\nbuilder<Config>().build();\n// @ts-expect-error wrong value type\nbuilder<Config>().set('port', 'nope');\n// @ts-expect-error unknown key\nbuilder<Config>().set('nope', 1);\n// @ts-expect-error an optional key alone is not enough\nbuilder<Config>().set('debug', true).build();\n\nconst assert = require('assert');\nassert.deepStrictEqual(c, { host: 'h', port: 1 });\nassert.deepStrictEqual(c2, { port: 1, debug: true, host: 'h' });\nconsole.log('OK');\n",
  '\ntype RequiredKeys<T> = { [K in keyof T]-?: {} extends Pick<T, K> ? never : K }[keyof T];\n\nexport interface Builder<T, Set extends keyof T> {\n  set<K extends keyof T>(key: K, value: T[K]): Builder<T, Set | K>;\n  build(this: RequiredKeys<T> extends Set ? Builder<T, Set> : never): T;\n}\n\nexport function builder<T>(): Builder<T, never> {\n  const acc: Partial<T> = {};\n  const self: any = {\n    set(key: keyof T, value: T[keyof T]) { (acc as any)[key] = value; return self; },\n    build() { return acc as T; },\n  };\n  return self as Builder<T, never>;\n}\n'),

 ('hts-006',
  'export a type `DeepAwaited<T>` unwrapping nested promises to any depth, including promises inside object properties and array elements, and a runtime function `deepAwait` returning that type. Non-promise values pass through unchanged, functions are untouched, and a promise of a promise of an object of promises resolves fully.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { deepAwait } from './sol';\nimport type { DeepAwaited } from './sol';\n\ntype _1 = Expect<Eq<DeepAwaited<Promise<Promise<number>>>, number>>;\ntype _2 = Expect<Eq<DeepAwaited<{ a: Promise<string>; b: { c: Promise<number> } }>, { a: string; b: { c: number } }>>;\ntype _3 = Expect<Eq<DeepAwaited<Promise<{ a: Promise<number>[] }>>, { a: number[] }>>;\ntype _4 = Expect<Eq<DeepAwaited<number>, number>>;\ntype _5 = Expect<Eq<DeepAwaited<(x: number) => Promise<string>>, (x: number) => Promise<string>>>;\n\nconst assert = require('assert');\n(async () => {\n  const r = await deepAwait({ a: Promise.resolve('x'), b: { c: Promise.resolve(1) } });\n  const s: string = r.a;\n  const n: number = r.b.c;\n  assert.deepStrictEqual(r, { a: 'x', b: { c: 1 } });\n  const r2 = await deepAwait(Promise.resolve({ a: [Promise.resolve(1), Promise.resolve(2)] }));\n  assert.deepStrictEqual(r2, { a: [1, 2] });\n  assert.strictEqual(await deepAwait(5), 5);\n  console.log('OK', s, n);\n})().catch((e) => { console.error(e); process.exit(1); });\n",
  "\nexport type DeepAwaited<T> =\n  T extends Promise<infer U> ? DeepAwaited<U>\n  : T extends (...args: any[]) => any ? T\n  : T extends ReadonlyArray<infer E>\n    ? (T extends readonly [any, ...any[]] ? { [K in keyof T]: DeepAwaited<T[K]> } : DeepAwaited<E>[])\n  : T extends object ? { [K in keyof T]: DeepAwaited<T[K]> }\n  : T;\n\nexport async function deepAwait<T>(value: T): Promise<DeepAwaited<T>> {\n  const v: any = await (value as any);\n  if (v === null || typeof v !== 'object' || typeof v === 'function') return v;\n  if (Array.isArray(v)) return (await Promise.all(v.map((x) => deepAwait(x)))) as any;\n  if (Object.getPrototypeOf(v) !== Object.prototype && Object.getPrototypeOf(v) !== null) return v;\n  const out: Record<string, unknown> = {};\n  for (const k of Object.keys(v)) out[k] = await deepAwait(v[k]);\n  return out as any;\n}\n"),

 ('hts-007',
  'export a `curry` turning a function of fixed arity into one callable with any split of its arguments, e.g. f(1)(2,3), f(1,2)(3) and f(1,2,3) all work and are all typed correctly, with the return type being the final result once every argument is supplied and a partially applied function otherwise. Supplying a wrongly-typed or extra argument must be a compile error.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { curry } from './sol';\n\nconst f = (a: number, b: string, c: boolean) => `${a}${b}${c}`;\nconst cf = curry(f);\n\nconst r1: string = cf(1, 'x', true);\nconst r2: string = cf(1)('x', true);\nconst r3: string = cf(1, 'x')(true);\nconst r4: string = cf(1)('x')(true);\n\ntype _1 = Expect<Eq<typeof r1, string>>;\n\n// @ts-expect-error wrong first argument type\ncf('nope');\n// @ts-expect-error wrong second argument type\ncf(1)(2);\n// @ts-expect-error too many arguments\ncf(1, 'x', true, 5);\n\nconst assert = require('assert');\nassert.strictEqual(r1, '1xtrue');\nassert.strictEqual(r2, '1xtrue');\nassert.strictEqual(r3, '1xtrue');\nassert.strictEqual(r4, '1xtrue');\nconst g = curry((a: number) => a + 1);\nassert.strictEqual(g(1), 2);\nconsole.log('OK');\n",
  "\ntype Drop<N extends number, T extends any[]> =\n  N extends 0 ? T : T extends [any, ...infer R] ? Drop<[...[], ...[]] extends [] ? never : Subtract1<N>, R> : [];\ntype Subtract1<N extends number> = N extends 0 ? 0 : Tuple<N> extends [any, ...infer R] ? R['length'] : 0;\ntype Tuple<N extends number, A extends any[] = []> = A['length'] extends N ? A : Tuple<N, [...A, any]>;\n\nexport type Curried<A extends any[], R> =\n  A extends [] ? R\n  : <P extends Partial<A> & any[]>(...args: P) =>\n      A extends [...Tuple<P['length']>, ...infer Rest]\n        ? Rest extends [] ? R : Curried<Rest extends any[] ? Rest : [], R>\n        : never;\n\nexport function curry<A extends any[], R>(fn: (...args: A) => R): Curried<A, R> {\n  const collect = (got: any[]): any =>\n    got.length >= fn.length ? fn(...(got as A)) : (...more: any[]) => collect([...got, ...more]);\n  return collect([]) as Curried<A, R>;\n}\n"),

 ('hts-008',
  "export a branded-type utility: `Brand<T, B>` producing a nominal type assignable FROM nothing but its own brand, a type guard `isEmail(s: string): s is Email` where `Email = Brand<string, 'Email'>`, and `asEmail(s: string): Email` that throws on an invalid address. A plain string must not be assignable to Email, an Email must still be usable everywhere a string is, and two different brands over the same base must not be mutually assignable.",
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { isEmail, asEmail } from './sol';\nimport type { Brand, Email } from './sol';\n\ntype UserId = Brand<string, 'UserId'>;\n\nconst e: Email = asEmail('a@b.com');\nconst asString: string = e;\nconst len: number = e.length;\n\n// @ts-expect-error a plain string is not an Email\nconst bad: Email = 'a@b.com';\n// @ts-expect-error different brands over the same base are not interchangeable\nconst bad2: UserId = e;\n\nconst s = 'x@y.com';\nlet out = 'no';\nif (isEmail(s)) { const narrowed: Email = s; out = narrowed; }\n\nconst assert = require('assert');\nassert.strictEqual(out, 'x@y.com');\nassert.strictEqual(asString, 'a@b.com');\nassert.strictEqual(len, 7);\nassert.throws(() => asEmail('nope'));\nassert.strictEqual(isEmail('nope'), false);\nconsole.log('OK');\n",
  "\ndeclare const brand: unique symbol;\nexport type Brand<T, B extends string> = T & { readonly [brand]: B };\nexport type Email = Brand<string, 'Email'>;\n\nexport function isEmail(s: string): s is Email {\n  return /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(s);\n}\nexport function asEmail(s: string): Email {\n  if (!isEmail(s)) throw new Error('invalid email');\n  return s;\n}\n"),

 ('hts-009',
  'export template-literal types `CamelCase<S>` turning `snake_case` and `kebab-case` into camelCase, `SnakeCase<S>` doing the reverse from camelCase, and `CamelKeys<T>` applying CamelCase to every key of an object type at one level. A string with no separator is unchanged; consecutive separators collapse; a leading separator is dropped.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport type { CamelCase, SnakeCase, CamelKeys } from './sol';\n\ntype _1 = Expect<Eq<CamelCase<'foo_bar'>, 'fooBar'>>;\ntype _2 = Expect<Eq<CamelCase<'foo-bar-baz'>, 'fooBarBaz'>>;\ntype _3 = Expect<Eq<CamelCase<'foo'>, 'foo'>>;\ntype _4 = Expect<Eq<CamelCase<'foo__bar'>, 'fooBar'>>;\ntype _5 = Expect<Eq<CamelCase<'_foo'>, 'foo'>>;\ntype _6 = Expect<Eq<SnakeCase<'fooBar'>, 'foo_bar'>>;\ntype _7 = Expect<Eq<SnakeCase<'fooBarBaz'>, 'foo_bar_baz'>>;\ntype _8 = Expect<Eq<SnakeCase<'foo'>, 'foo'>>;\ntype _9 = Expect<Eq<CamelKeys<{ foo_bar: number; baz: string }>, { fooBar: number; baz: string }>>;\ntype _10 = Expect<Eq<CamelCase<'a_b_c'>, 'aBC'>>;\n\nconsole.log('OK');\n",
  "\nexport type CamelCase<S extends string> =\n  S extends `${infer H}_${infer R}`\n    ? H extends '' ? CamelCase<R> : `${H}${Capitalize<CamelCase<R>>}`\n  : S extends `${infer H}-${infer R}`\n    ? H extends '' ? CamelCase<R> : `${H}${Capitalize<CamelCase<R>>}`\n  : S;\n\nexport type SnakeCase<S extends string> =\n  S extends `${infer H}${infer R}`\n    ? H extends Uppercase<H>\n      ? H extends Lowercase<H> ? `${H}${SnakeCase<R>}` : `_${Lowercase<H>}${SnakeCase<R>}`\n      : `${H}${SnakeCase<R>}`\n    : S;\n\nexport type CamelKeys<T> = { [K in keyof T as CamelCase<K & string>]: T[K] };\n"),

 ('hts-010',
  'export `UnionToIntersection<U>`, `IsUnion<T>` giving true only for a genuine union (never and a single type give false), and `LastOf<U>` giving the last member of a union. Then export `UnionToTuple<U>` turning a union into a tuple of its members. These must not collapse `boolean` incorrectly: boolean is the union true | false.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport type { UnionToIntersection, IsUnion, UnionToTuple } from './sol';\n\ntype _1 = Expect<Eq<UnionToIntersection<{ a: 1 } | { b: 2 }>, { a: 1 } & { b: 2 }>>;\ntype _2 = Expect<Eq<IsUnion<'a' | 'b'>, true>>;\ntype _3 = Expect<Eq<IsUnion<'a'>, false>>;\ntype _4 = Expect<Eq<IsUnion<never>, false>>;\ntype _5 = Expect<Eq<IsUnion<boolean>, true>>;\ntype T1 = UnionToTuple<'a' | 'b' | 'c'>;\ntype _6 = Expect<Eq<T1['length'], 3>>;\ntype _7 = Expect<Eq<T1[number], 'a' | 'b' | 'c'>>;\ntype _8 = Expect<Eq<UnionToTuple<never>, []>>;\ntype _9 = Expect<Eq<UnionToTuple<'a'>, ['a']>>;\n\nconsole.log('OK');\n",
  '\nexport type UnionToIntersection<U> =\n  (U extends any ? (k: U) => void : never) extends (k: infer I) => void ? I : never;\n\nexport type IsUnion<T, U = T> = [T] extends [never] ? false\n  : T extends any ? ([U] extends [T] ? false : true) : never;\n\nexport type LastOf<U> =\n  UnionToIntersection<U extends any ? (x: U) => void : never> extends (x: infer L) => void ? L : never;\n\nexport type UnionToTuple<U, Acc extends any[] = []> =\n  [U] extends [never] ? Acc : UnionToTuple<Exclude<U, LastOf<U>>, [LastOf<U>, ...Acc]>;\n'),

 ('hts-011',
  'export `pick(obj, keys)` and `omit(obj, keys)` that PRESERVE optionality and readonly modifiers of the surviving properties, accept only keys that exist on the object, and are correct at runtime -- `pick` copies only own properties that are present, and `omit` copies everything else. `pick` of no keys is an empty object type.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { pick, omit } from './sol';\n\ninterface Src { a: number; b?: string; readonly c: boolean; d: number[] }\nconst src: Src = { a: 1, c: true, d: [1] };\n\nconst p = pick(src, ['a', 'b', 'c']);\ntype _1 = Expect<Eq<typeof p, { a: number; b?: string; readonly c: boolean }>>;\nconst o = omit(src, ['d']);\ntype _2 = Expect<Eq<typeof o, { a: number; b?: string; readonly c: boolean }>>;\nconst e = pick(src, []);\ntype _3 = Expect<Eq<typeof e, {}>>;\n\n// @ts-expect-error not a key of Src\npick(src, ['nope']);\n// @ts-expect-error not a key of Src\nomit(src, ['nope']);\n\nconst assert = require('assert');\nassert.deepStrictEqual(p, { a: 1, c: true });\nassert.strictEqual('b' in p, false, 'pick copied an absent optional key');\nassert.deepStrictEqual(o, { a: 1, c: true });\nassert.deepStrictEqual(e, {});\nconsole.log('OK');\n",
  '\nexport function pick<T extends object, K extends keyof T>(obj: T, keys: readonly K[]): Pick<T, K> {\n  const out = {} as Pick<T, K>;\n  for (const k of keys) {\n    if (Object.prototype.hasOwnProperty.call(obj, k)) (out as T)[k] = obj[k];\n  }\n  return out;\n}\nexport function omit<T extends object, K extends keyof T>(obj: T, keys: readonly K[]): Omit<T, K> {\n  const drop = new Set<PropertyKey>(keys as readonly PropertyKey[]);\n  const out = {} as Record<PropertyKey, unknown>;\n  for (const k of Object.keys(obj) as (keyof T)[]) {\n    if (!drop.has(k)) out[k as PropertyKey] = obj[k];\n  }\n  return out as Omit<T, K>;\n}\n'),

 ('hts-012',
  'export a `Result<T, E>` discriminated union with `ok(value)` and `err(error)` constructors, type guards `isOk` and `isErr` that NARROW, a `map` that transforms only the ok branch and preserves the error type, and an `unwrapOr`. After `isOk(r)` the value must be typed T with no undefined, and after `isErr(r)` accessing `.value` must be a compile error.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { ok, err, isOk, isErr, map, unwrapOr } from './sol';\nimport type { Result } from './sol';\n\nconst a: Result<number, string> = ok(1);\nconst b: Result<number, string> = err('bad');\n\nlet got = -1;\nif (isOk(a)) { const v: number = a.value; got = v; }\nlet msg = '';\nif (isErr(b)) { const e: string = b.error; msg = e; }\n\nconst m = map(a, (n) => `n=${n}`);\ntype _1 = Expect<Eq<typeof m, Result<string, string>>>;\n\n// @ts-expect-error the error branch has no value\nif (isErr(b)) { b.value; }\n// @ts-expect-error the ok branch has no error\nif (isOk(a)) { a.error; }\n// @ts-expect-error map's callback receives T, not the error\nmap(a, (n: string) => n);\n\nconst assert = require('assert');\nassert.strictEqual(got, 1);\nassert.strictEqual(msg, 'bad');\nassert.deepStrictEqual(m, ok('n=1'));\nassert.strictEqual(unwrapOr(b, 99), 99);\nassert.strictEqual(unwrapOr(a, 99), 1);\nassert.deepStrictEqual(map(b, (n) => n + 1), b);\nconsole.log('OK');\n",
  '\nexport type Result<T, E> = { readonly ok: true; readonly value: T } | { readonly ok: false; readonly error: E };\n\nexport function ok<T>(value: T): Result<T, never> { return { ok: true, value }; }\nexport function err<E>(error: E): Result<never, E> { return { ok: false, error }; }\nexport function isOk<T, E>(r: Result<T, E>): r is { readonly ok: true; readonly value: T } { return r.ok; }\nexport function isErr<T, E>(r: Result<T, E>): r is { readonly ok: false; readonly error: E } { return !r.ok; }\nexport function map<T, E, U>(r: Result<T, E>, fn: (v: T) => U): Result<U, E> {\n  return r.ok ? { ok: true, value: fn(r.value) } : r;\n}\nexport function unwrapOr<T, E>(r: Result<T, E>, fallback: T): T { return r.ok ? r.value : fallback; }\n'),

 ('hts-013',
  "export a type `Split<S, D>` splitting a string literal type on a delimiter into a tuple, `Join<T, D>` doing the reverse, and `Trim<S>` removing leading and trailing spaces. Splitting on an empty delimiter yields the characters; splitting an empty string yields `['']`; joining an empty tuple yields `''`.",
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport type { Split, Join, Trim } from './sol';\n\ntype _1 = Expect<Eq<Split<'a,b,c', ','>, ['a', 'b', 'c']>>;\ntype _2 = Expect<Eq<Split<'abc', ''>, ['a', 'b', 'c']>>;\ntype _3 = Expect<Eq<Split<'', ','>, ['']>>;\ntype _4 = Expect<Eq<Split<'a', ','>, ['a']>>;\ntype _5 = Expect<Eq<Split<'a,,b', ','>, ['a', '', 'b']>>;\ntype _6 = Expect<Eq<Join<['a', 'b', 'c'], '-'>, 'a-b-c'>>;\ntype _7 = Expect<Eq<Join<[], '-'>, ''>>;\ntype _8 = Expect<Eq<Join<['a'], '-'>, 'a'>>;\ntype _9 = Expect<Eq<Trim<'  hi  '>, 'hi'>>;\ntype _10 = Expect<Eq<Trim<'hi'>, 'hi'>>;\ntype _11 = Expect<Eq<Trim<'   '>, ''>>;\ntype _12 = Expect<Eq<Join<Split<'a.b.c', '.'>, '/'>, 'a/b/c'>>;\n\nconsole.log('OK');\n",
  "\nexport type Split<S extends string, D extends string> =\n  D extends ''\n    ? (S extends `${infer H}${infer R}` ? [H, ...Split<R, D>] : [])\n    : S extends `${infer H}${D}${infer R}` ? [H, ...Split<R, D>] : [S];\n\nexport type Join<T extends readonly string[], D extends string> =\n  T extends readonly [infer H extends string, ...infer R extends string[]]\n    ? R extends readonly [] ? H : `${H}${D}${Join<R, D>}`\n    : '';\n\nexport type Trim<S extends string> =\n  S extends ` ${infer R}` ? Trim<R> : S extends `${infer R} ` ? Trim<R> : S;\n"),

 ('hts-014',
  'export a `defineRoutes` taking an object mapping route names to path template strings, and returning an object of the same keys whose values are functions taking exactly the params that appear as `:name` segments in that path -- typed as an object of string-keyed params, or taking NO argument at all when the path has no params -- and returning the interpolated path. Passing a missing or extra param must be a compile error.',
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { defineRoutes } from './sol';\n\nconst r = defineRoutes({\n  home: '/',\n  user: '/users/:id',\n  post: '/users/:id/posts/:postId',\n});\n\nconst a: string = r.home();\nconst b: string = r.user({ id: '7' });\nconst c: string = r.post({ id: '7', postId: '9' });\n\n// Never invoked: `r.nope()` must fail to compile, and running it would be a\n// TypeError rather than a type test.\nfunction _mustNotCompile() {\n  // @ts-expect-error a param-less route takes no argument\n  r.home({ id: '1' });\n  // @ts-expect-error missing a required param\n  r.post({ id: '7' });\n  // @ts-expect-error extra param\n  r.user({ id: '7', nope: 'x' });\n  // @ts-expect-error unknown route\n  r.nope();\n}\n\nconst assert = require('assert');\nassert.strictEqual(a, '/');\nassert.strictEqual(b, '/users/7');\nassert.strictEqual(c, '/users/7/posts/9');\nconsole.log('OK');\n",
  "\ntype Params<S extends string> =\n  S extends `${string}:${infer P}/${infer R}` ? P | Params<`/${R}`>\n  : S extends `${string}:${infer P}` ? P\n  : never;\n\ntype Route<S extends string> =\n  [Params<S>] extends [never] ? () => string : (params: { [K in Params<S>]: string }) => string;\n\nexport function defineRoutes<const T extends Record<string, string>>(defs: T): { [K in keyof T]: Route<T[K]> } {\n  const out = {} as Record<string, (params?: Record<string, string>) => string>;\n  for (const key of Object.keys(defs)) {\n    const tmpl = defs[key] as string;\n    out[key] = (params?: Record<string, string>) =>\n      tmpl.split('/').map((seg) => (seg.startsWith(':') ? (params ?? {})[seg.slice(1)] : seg)).join('/');\n  }\n  return out as { [K in keyof T]: Route<T[K]> };\n}\n"),

 ('hts-015',
  "export `DeepPartial<T>` making every property optional at every depth without touching arrays' element requiredness or functions, and a runtime `applyPatch(base, patch)` typed `(base: T, patch: DeepPartial<T>) => T` that merges the patch recursively, returns a new object, replaces arrays wholesale, and treats an explicit `undefined` in the patch as 'leave alone'.",
  "\n// Exact type equality: this two-conditional trick distinguishes `any`, `unknown`\n// and a union from the intended type, which `extends` alone does not.\ntype Eq<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;\ntype Expect<T extends true> = T;\n\nimport { applyPatch } from './sol';\nimport type { DeepPartial } from './sol';\n\ninterface Cfg { host: string; nested: { a: number; b: { c: boolean } }; list: number[]; fn: () => void }\ntype P = DeepPartial<Cfg>;\ntype _1 = Expect<Eq<P['host'], string | undefined>>;\ntype _2 = Expect<Eq<NonNullable<P['nested']>, { a?: number; b?: { c?: boolean } }>>;\ntype _3 = Expect<Eq<P['list'], number[] | undefined>>;\ntype _4 = Expect<Eq<P['fn'], (() => void) | undefined>>;\n\nconst base: Cfg = { host: 'h', nested: { a: 1, b: { c: true } }, list: [1, 2], fn: () => {} };\nconst out = applyPatch(base, { nested: { b: { c: false } }, list: [9] });\ntype _5 = Expect<Eq<typeof out, Cfg>>;\n\n// @ts-expect-error wrong leaf type\napplyPatch(base, { nested: { a: 'no' } });\n// @ts-expect-error unknown key\napplyPatch(base, { nope: 1 });\n\nconst assert = require('assert');\nassert.strictEqual(out.host, 'h');\nassert.strictEqual(out.nested.a, 1);\nassert.strictEqual(out.nested.b.c, false);\nassert.deepStrictEqual(out.list, [9]);\nassert.notStrictEqual(out, base);\nassert.deepStrictEqual(base.nested.b, { c: true }, 'base was mutated');\nassert.strictEqual(applyPatch(base, { host: undefined }).host, 'h');\nconsole.log('OK');\n",
  "\nexport type DeepPartial<T> =\n  T extends (...args: any[]) => any ? T\n  : T extends ReadonlyArray<any> ? T\n  : T extends object ? { [K in keyof T]?: DeepPartial<T[K]> }\n  : T;\n\nfunction isPlain(v: unknown): v is Record<string, unknown> {\n  return typeof v === 'object' && v !== null && !Array.isArray(v)\n    && (Object.getPrototypeOf(v) === Object.prototype || Object.getPrototypeOf(v) === null);\n}\n\nexport function applyPatch<T>(base: T, patch: DeepPartial<T>): T {\n  if (!isPlain(base)) return (patch === undefined ? base : (patch as unknown as T));\n  const out: Record<string, unknown> = { ...(base as unknown as Record<string, unknown>) };\n  const p = patch as unknown as Record<string, unknown>;\n  for (const k of Object.keys(p ?? {})) {\n    const v = p[k];\n    if (v === undefined) continue;\n    out[k] = isPlain(v) && isPlain(out[k]) ? applyPatch(out[k] as any, v as any) : v;\n  }\n  return out as unknown as T;\n}\n"),

]


def tasks():
    return ([(tid, spec, tests) for tid, spec, tests, _r in JS],
            [(tid, spec, tests) for tid, spec, tests, _r in TS])


if __name__ == "__main__":
    print("hard js: %d, hard ts: %d" % (len(JS), len(TS)))
