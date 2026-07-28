#!/usr/bin/env python3
"""JS (50) and TS (50) categories. JS runs under node; TS is typechecked with
`tsc --strict` first, then executed."""

# ---------------------------------------------------------------- JS (50)
# (id, spec, tests, reference)  -- solution exports via module.exports
JS = [
("js-001", "`deepEqual(a, b)` returning true when two values are deeply equal (objects, arrays, "
 "primitives; key order irrelevant).",
 "const {deepEqual}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(deepEqual({a:1,b:[1,2]},{b:[1,2],a:1}),true);\n"
 "a.strictEqual(deepEqual({a:1},{a:2}),false);\n"
 "a.strictEqual(deepEqual([1,[2]],[1,[2]]),true);\n"
 "a.strictEqual(deepEqual(null,null),true);\n"
 "a.strictEqual(deepEqual({a:1},{a:1,b:2}),false);console.log('OK');",
 "function deepEqual(a,b){if(a===b)return true;\n"
 "if(typeof a!=='object'||typeof b!=='object'||a===null||b===null)return false;\n"
 "if(Array.isArray(a)!==Array.isArray(b))return false;\n"
 "const ka=Object.keys(a),kb=Object.keys(b);if(ka.length!==kb.length)return false;\n"
 "return ka.every(k=>Object.prototype.hasOwnProperty.call(b,k)&&deepEqual(a[k],b[k]));}\n"
 "module.exports={deepEqual};"),
("js-002", "`flattenObject(obj)` turning a nested object into a flat object with dot-separated keys. "
 "Arrays are leaf values.",
 "const {flattenObject}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(flattenObject({a:{b:{c:1}},d:2}),{'a.b.c':1,'d':2});\n"
 "a.deepStrictEqual(flattenObject({a:[1,2]}),{'a':[1,2]});\n"
 "a.deepStrictEqual(flattenObject({}),{});console.log('OK');",
 "function flattenObject(o,p=''){const out={};for(const[k,v]of Object.entries(o)){\n"
 "const key=p?p+'.'+k:k;\n"
 "if(v&&typeof v==='object'&&!Array.isArray(v))Object.assign(out,flattenObject(v,key));\n"
 "else out[key]=v;}return out;}\nmodule.exports={flattenObject};"),
("js-003", "async `retryAsync(fn, attempts)` calling fn up to attempts times, resolving with the first "
 "success and rejecting with the last error. Do not sleep.",
 "const {retryAsync}=require('./sol.js');const a=require('assert');\n"
 "(async()=>{let n=0;const r=await retryAsync(async()=>{n++;if(n<3)throw new Error('x');return 'ok';},5);\n"
 "a.strictEqual(r,'ok');a.strictEqual(n,3);let m=0;\n"
 "await a.rejects(retryAsync(async()=>{m++;throw new Error('a');},2));a.strictEqual(m,2);\n"
 "console.log('OK');})().catch(e=>{console.error(e);process.exit(1);});",
 "async function retryAsync(fn,attempts){let last;for(let i=0;i<attempts;i++){\n"
 "try{return await fn();}catch(e){last=e;}}throw last;}\nmodule.exports={retryAsync};"),
("js-004", "`groupBy(arr, keyFn)` returning an object mapping each key to the array of matching items, "
 "preserving input order.",
 "const {groupBy}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(groupBy([1,2,3,4],x=>x%2?'odd':'even'),{odd:[1,3],even:[2,4]});\n"
 "a.deepStrictEqual(groupBy([],x=>x),{});console.log('OK');",
 "function groupBy(arr,keyFn){const o={};for(const it of arr){const k=keyFn(it);\n"
 "(o[k]=o[k]||[]).push(it);}return o;}\nmodule.exports={groupBy};"),
("js-005", "`chunk(arr, size)` splitting an array into consecutive arrays of length size, last one "
 "possibly shorter. Throws on size < 1.",
 "const {chunk}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(chunk([1,2,3,4,5],2),[[1,2],[3,4],[5]]);\n"
 "a.deepStrictEqual(chunk([],3),[]);a.throws(()=>chunk([1],0));console.log('OK');",
 "function chunk(arr,size){if(size<1)throw new Error('size');const o=[];\n"
 "for(let i=0;i<arr.length;i+=size)o.push(arr.slice(i,i+size));return o;}\nmodule.exports={chunk};"),
("js-006", "`uniqueBy(arr, keyFn)` removing duplicates by key, keeping first occurrence order.",
 "const {uniqueBy}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(uniqueBy([{i:1},{i:1},{i:2}],o=>o.i),[{i:1},{i:2}]);\n"
 "a.deepStrictEqual(uniqueBy([],x=>x),[]);console.log('OK');",
 "function uniqueBy(arr,keyFn){const s=new Set(),o=[];for(const x of arr){const k=keyFn(x);\n"
 "if(!s.has(k)){s.add(k);o.push(x);}}return o;}\nmodule.exports={uniqueBy};"),
("js-007", "`debounceCount(fn, ms)` returning a function that, using a timer, only invokes fn once "
 "after calls stop. Return an object {call, flush} where flush runs any pending invocation now.",
 "const {debounceCount}=require('./sol.js');const a=require('assert');\n"
 "let n=0;const d=debounceCount(()=>n++,50);d.call();d.call();d.call();a.strictEqual(n,0);\n"
 "d.flush();a.strictEqual(n,1);console.log('OK');",
 "function debounceCount(fn,ms){let t=null,pending=false;\n"
 "return{call(){pending=true;if(t)clearTimeout(t);t=setTimeout(()=>{pending=false;t=null;fn();},ms);},\n"
 "flush(){if(t){clearTimeout(t);t=null;}if(pending){pending=false;fn();}}};}\n"
 "module.exports={debounceCount};"),
("js-008", "`pick(obj, keys)` returning a new object containing only the listed keys that exist.",
 "const {pick}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(pick({a:1,b:2,c:3},['a','c']),{a:1,c:3});\n"
 "a.deepStrictEqual(pick({a:1},['z']),{});console.log('OK');",
 "function pick(obj,keys){const o={};for(const k of keys)\n"
 "if(Object.prototype.hasOwnProperty.call(obj,k))o[k]=obj[k];return o;}\nmodule.exports={pick};"),
("js-009", "`omit(obj, keys)` returning a new object without the listed keys.",
 "const {omit}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(omit({a:1,b:2},['b']),{a:1});\n"
 "a.deepStrictEqual(omit({},['x']),{});console.log('OK');",
 "function omit(obj,keys){const s=new Set(keys),o={};\n"
 "for(const[k,v]of Object.entries(obj))if(!s.has(k))o[k]=v;return o;}\nmodule.exports={omit};"),
("js-010", "`range(start, end, step)` returning an array from start up to but excluding end.",
 "const {range}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(range(0,5,1),[0,1,2,3,4]);a.deepStrictEqual(range(0,6,2),[0,2,4]);\n"
 "a.deepStrictEqual(range(3,3,1),[]);console.log('OK');",
 "function range(s,e,st){const o=[];for(let i=s;i<e;i+=st)o.push(i);return o;}\n"
 "module.exports={range};"),
("js-011", "`zip(a, b)` pairing two arrays into an array of two-element arrays, stopping at the shorter.",
 "const {zip}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(zip([1,2],['a','b']),[[1,'a'],[2,'b']]);\n"
 "a.deepStrictEqual(zip([1],['a','b']),[[1,'a']]);console.log('OK');",
 "function zip(a,b){const n=Math.min(a.length,b.length),o=[];\n"
 "for(let i=0;i<n;i++)o.push([a[i],b[i]]);return o;}\nmodule.exports={zip};"),
("js-012", "`sortBy(arr, keyFn)` returning a new sorted array by the computed key ascending, without "
 "mutating the input.",
 "const {sortBy}=require('./sol.js');const a=require('assert');\n"
 "const src=[{n:3},{n:1}];a.deepStrictEqual(sortBy(src,o=>o.n),[{n:1},{n:3}]);\n"
 "a.deepStrictEqual(src,[{n:3},{n:1}]);console.log('OK');",
 "function sortBy(arr,keyFn){return arr.slice().sort((x,y)=>{const a=keyFn(x),b=keyFn(y);\n"
 "return a<b?-1:a>b?1:0;});}\nmodule.exports={sortBy};"),
("js-013", "`sum(arr)` returning the numeric total, 0 for an empty array.",
 "const {sum}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(sum([1,2,3]),6);a.strictEqual(sum([]),0);console.log('OK');",
 "function sum(arr){return arr.reduce((a,b)=>a+b,0);}\nmodule.exports={sum};"),
("js-014", "`capitalizeWords(s)` upper-casing the first letter of each whitespace-separated word.",
 "const {capitalizeWords}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(capitalizeWords('hello big world'),'Hello Big World');\n"
 "a.strictEqual(capitalizeWords(''),'');console.log('OK');",
 "function capitalizeWords(s){return s.split(' ').map(w=>w?w[0].toUpperCase()+w.slice(1):w)\n"
 ".join(' ');}\nmodule.exports={capitalizeWords};"),
("js-015", "`parseQuery(qs)` parsing a query string into an object; repeated keys become arrays; "
 "percent escapes decoded.",
 "const {parseQuery}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(parseQuery('a=1&b=2'),{a:'1',b:'2'});\n"
 "a.deepStrictEqual(parseQuery('a=1&a=2'),{a:['1','2']});\n"
 "a.deepStrictEqual(parseQuery('q=hi%20there'),{q:'hi there'});console.log('OK');",
 "function parseQuery(qs){const o={};if(!qs)return o;\n"
 "for(const part of qs.split('&')){const[k,v='']=part.split('=');\n"
 "const key=decodeURIComponent(k),val=decodeURIComponent(v);\n"
 "if(key in o){o[key]=[].concat(o[key],val);}else o[key]=val;}return o;}\n"
 "module.exports={parseQuery};"),
("js-016", "`memoize(fn)` caching results by the JSON of the arguments.",
 "const {memoize}=require('./sol.js');const a=require('assert');\n"
 "let calls=0;const f=memoize(x=>{calls++;return x*2;});\n"
 "a.strictEqual(f(2),4);a.strictEqual(f(2),4);a.strictEqual(calls,1);console.log('OK');",
 "function memoize(fn){const c=new Map();return(...a)=>{const k=JSON.stringify(a);\n"
 "if(!c.has(k))c.set(k,fn(...a));return c.get(k);};}\nmodule.exports={memoize};"),
("js-017", "`flattenDeep(arr)` flattening an arbitrarily nested array.",
 "const {flattenDeep}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(flattenDeep([1,[2,[3,[4]]]]),[1,2,3,4]);\n"
 "a.deepStrictEqual(flattenDeep([]),[]);console.log('OK');",
 "function flattenDeep(arr){return arr.reduce((o,x)=>o.concat(Array.isArray(x)?flattenDeep(x):x),[]);}\n"
 "module.exports={flattenDeep};"),
("js-018", "`countBy(arr, keyFn)` returning an object mapping key to the number of items with it.",
 "const {countBy}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(countBy([1,2,3],x=>x%2?'o':'e'),{o:2,e:1});console.log('OK');",
 "function countBy(arr,keyFn){const o={};for(const x of arr){const k=keyFn(x);o[k]=(o[k]||0)+1;}\n"
 "return o;}\nmodule.exports={countBy};"),
("js-019", "`clamp(n, lo, hi)` constraining a number to a range.",
 "const {clamp}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(clamp(5,1,3),3);a.strictEqual(clamp(0,1,3),1);a.strictEqual(clamp(2,1,3),2);\n"
 "console.log('OK');",
 "function clamp(n,lo,hi){return Math.min(hi,Math.max(lo,n));}\nmodule.exports={clamp};"),
("js-020", "`titleCaseSlug(s)` converting 'my-blog-post' into 'My Blog Post'.",
 "const {titleCaseSlug}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(titleCaseSlug('my-blog-post'),'My Blog Post');console.log('OK');",
 "function titleCaseSlug(s){return s.split('-').map(w=>w?w[0].toUpperCase()+w.slice(1):w)\n"
 ".join(' ');}\nmodule.exports={titleCaseSlug};"),
("js-021", "`once(fn)` returning a function that only calls fn the first time and thereafter returns "
 "the first result.",
 "const {once}=require('./sol.js');const a=require('assert');\n"
 "let n=0;const f=once(()=>++n);a.strictEqual(f(),1);a.strictEqual(f(),1);a.strictEqual(n,1);\n"
 "console.log('OK');",
 "function once(fn){let done=false,val;return(...a)=>{if(!done){done=true;val=fn(...a);}return val;};}\n"
 "module.exports={once};"),
("js-022", "`isPalindrome(s)` ignoring case and non-alphanumeric characters.",
 "const {isPalindrome}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(isPalindrome('A man, a plan, a canal: Panama'),true);\n"
 "a.strictEqual(isPalindrome('abc'),false);console.log('OK');",
 "function isPalindrome(s){const t=s.toLowerCase().replace(/[^a-z0-9]/g,'');\n"
 "return t===t.split('').reverse().join('');}\nmodule.exports={isPalindrome};"),
("js-023", "`mergeDeep(a, b)` deeply merging b into a returning a new object without mutating either.",
 "const {mergeDeep}=require('./sol.js');const a=require('assert');\n"
 "const x={p:{q:1,r:2}},y={p:{r:9,s:3}};\n"
 "a.deepStrictEqual(mergeDeep(x,y),{p:{q:1,r:9,s:3}});\n"
 "a.deepStrictEqual(x,{p:{q:1,r:2}});console.log('OK');",
 "function mergeDeep(a,b){const o={...a};for(const[k,v]of Object.entries(b)){\n"
 "if(v&&typeof v==='object'&&!Array.isArray(v)&&o[k]&&typeof o[k]==='object')\n"
 "o[k]=mergeDeep(o[k],v);else o[k]=v;}return o;}\nmodule.exports={mergeDeep};"),
("js-024", "`chunkString(s, n)` splitting a string into pieces of at most n characters.",
 "const {chunkString}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(chunkString('abcde',2),['ab','cd','e']);\n"
 "a.deepStrictEqual(chunkString('',3),[]);console.log('OK');",
 "function chunkString(s,n){const o=[];for(let i=0;i<s.length;i+=n)o.push(s.slice(i,i+n));\n"
 "return o;}\nmodule.exports={chunkString};"),
("js-025", "`sumBy(arr, keyFn)` totalling a computed numeric key.",
 "const {sumBy}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(sumBy([{v:1},{v:2}],o=>o.v),3);a.strictEqual(sumBy([],o=>o.v),0);console.log('OK');",
 "function sumBy(arr,keyFn){return arr.reduce((t,x)=>t+keyFn(x),0);}\nmodule.exports={sumBy};"),
("js-026", "`intersection(a, b)` returning values present in both arrays, order of a, no duplicates.",
 "const {intersection}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(intersection([1,2,2,3],[2,3,4]),[2,3]);\n"
 "a.deepStrictEqual(intersection([],[1]),[]);console.log('OK');",
 "function intersection(a,b){const s=new Set(b),seen=new Set();\n"
 "return a.filter(x=>s.has(x)&&!seen.has(x)&&seen.add(x));}\nmodule.exports={intersection};"),
("js-027", "`difference(a, b)` returning values in a that are not in b.",
 "const {difference}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(difference([1,2,3],[2]),[1,3]);console.log('OK');",
 "function difference(a,b){const s=new Set(b);return a.filter(x=>!s.has(x));}\n"
 "module.exports={difference};"),
("js-028", "`safeJsonParse(s, fallback)` returning the parsed value or fallback on invalid JSON.",
 "const {safeJsonParse}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(safeJsonParse('{\"a\":1}',null),{a:1});\n"
 "a.strictEqual(safeJsonParse('nope','x'),'x');console.log('OK');",
 "function safeJsonParse(s,fallback){try{return JSON.parse(s);}catch(e){return fallback;}}\n"
 "module.exports={safeJsonParse};"),
("js-029", "`mapValues(obj, fn)` applying fn to each value returning a new object.",
 "const {mapValues}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(mapValues({a:1,b:2},v=>v*2),{a:2,b:4});console.log('OK');",
 "function mapValues(obj,fn){const o={};for(const[k,v]of Object.entries(obj))o[k]=fn(v);return o;}\n"
 "module.exports={mapValues};"),
("js-030", "`partition(arr, pred)` returning [matching, notMatching] preserving order.",
 "const {partition}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(partition([1,2,3,4],x=>x%2===0),[[2,4],[1,3]]);console.log('OK');",
 "function partition(arr,pred){const y=[],n=[];for(const x of arr)(pred(x)?y:n).push(x);\n"
 "return[y,n];}\nmodule.exports={partition};"),
("js-031", "`escapeHtml(s)` escaping &, <, >, \" and '.",
 "const {escapeHtml}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(escapeHtml('<a href=\"x\">&</a>'),'&lt;a href=&quot;x&quot;&gt;&amp;&lt;/a&gt;');\n"
 "console.log('OK');",
 "function escapeHtml(s){const m={'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'};\n"
 "return s.replace(/[&<>\"']/g,c=>m[c]);}\nmodule.exports={escapeHtml};"),
("js-032", "`sleepless(tasks)` running an array of functions returning promises sequentially and "
 "resolving with the array of results in order.",
 "const {sleepless}=require('./sol.js');const a=require('assert');\n"
 "(async()=>{const order=[];\n"
 "const r=await sleepless([async()=>{order.push(1);return 1;},async()=>{order.push(2);return 2;}]);\n"
 "a.deepStrictEqual(r,[1,2]);a.deepStrictEqual(order,[1,2]);console.log('OK');})()\n"
 ".catch(e=>{console.error(e);process.exit(1);});",
 "async function sleepless(tasks){const out=[];for(const t of tasks)out.push(await t());return out;}\n"
 "module.exports={sleepless};"),
("js-033", "`maxBy(arr, keyFn)` returning the item with the largest computed key, or undefined for an "
 "empty array.",
 "const {maxBy}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(maxBy([{v:1},{v:9}],o=>o.v),{v:9});\n"
 "a.strictEqual(maxBy([],o=>o),undefined);console.log('OK');",
 "function maxBy(arr,keyFn){if(!arr.length)return undefined;\n"
 "return arr.reduce((b,x)=>keyFn(x)>keyFn(b)?x:b);}\nmodule.exports={maxBy};"),
("js-034", "`padLeft(s, n, ch)` left-padding a string to length n.",
 "const {padLeft}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(padLeft('7',3,'0'),'007');a.strictEqual(padLeft('abcd',2,'0'),'abcd');\n"
 "console.log('OK');",
 "function padLeft(s,n,ch){return s.length>=n?s:ch.repeat(n-s.length)+s;}\n"
 "module.exports={padLeft};"),
("js-035", "`toQueryString(obj)` building a query string with encoded keys and values, sorted by key.",
 "const {toQueryString}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(toQueryString({b:2,a:'x y'}),'a=x%20y&b=2');console.log('OK');",
 "function toQueryString(o){return Object.keys(o).sort()\n"
 ".map(k=>encodeURIComponent(k)+'='+encodeURIComponent(String(o[k])).replace(/%20/g,'%20'))\n"
 ".join('&');}\nmodule.exports={toQueryString};"),
("js-036", "`average(arr)` returning the mean, or 0 for an empty array.",
 "const {average}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(average([2,4]),3);a.strictEqual(average([]),0);console.log('OK');",
 "function average(arr){return arr.length?arr.reduce((a,b)=>a+b,0)/arr.length:0;}\n"
 "module.exports={average};"),
("js-037", "`deepClone(v)` producing a structural copy of nested objects and arrays.",
 "const {deepClone}=require('./sol.js');const a=require('assert');\n"
 "const o={a:{b:[1,2]}};const c=deepClone(o);c.a.b.push(3);\n"
 "a.deepStrictEqual(o,{a:{b:[1,2]}});a.deepStrictEqual(c.a.b,[1,2,3]);console.log('OK');",
 "function deepClone(v){if(Array.isArray(v))return v.map(deepClone);\n"
 "if(v&&typeof v==='object'){const o={};for(const[k,x]of Object.entries(v))o[k]=deepClone(x);\n"
 "return o;}return v;}\nmodule.exports={deepClone};"),
("js-038", "`throttleManual(fn)` returning {call, tick} where call runs fn only if tick has been "
 "called since the last invocation (first call always runs).",
 "const {throttleManual}=require('./sol.js');const a=require('assert');\n"
 "let n=0;const t=throttleManual(()=>n++);t.call();t.call();a.strictEqual(n,1);\n"
 "t.tick();t.call();a.strictEqual(n,2);console.log('OK');",
 "function throttleManual(fn){let ready=true;\n"
 "return{call(){if(ready){ready=false;fn();}},tick(){ready=true;}};}\n"
 "module.exports={throttleManual};"),
("js-039", "`words(s)` returning the array of alphabetic words lowercased.",
 "const {words}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(words('Hello, World!'),['hello','world']);\n"
 "a.deepStrictEqual(words(''),[]);console.log('OK');",
 "function words(s){return (s.toLowerCase().match(/[a-z]+/g)||[]);}\nmodule.exports={words};"),
("js-040", "`rotateArray(arr, k)` rotating right by k handling k larger than length and negative k, "
 "returning a new array.",
 "const {rotateArray}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(rotateArray([1,2,3,4,5],2),[4,5,1,2,3]);\n"
 "a.deepStrictEqual(rotateArray([1,2,3],-1),[2,3,1]);\n"
 "a.deepStrictEqual(rotateArray([],3),[]);console.log('OK');",
 "function rotateArray(arr,k){if(!arr.length)return[];\n"
 "const n=((k%arr.length)+arr.length)%arr.length;return arr.slice(-n||arr.length)\n"
 ".concat(arr.slice(0,-n||arr.length)).slice(0,arr.length);}\nmodule.exports={rotateArray};"),
("js-041", "`isEmpty(v)` true for null, undefined, '', [], {} and false otherwise.",
 "const {isEmpty}=require('./sol.js');const a=require('assert');\n"
 "[null,undefined,'',[],{}].forEach(v=>a.strictEqual(isEmpty(v),true));\n"
 "[0,'a',[1],{a:1}].forEach(v=>a.strictEqual(isEmpty(v),false));console.log('OK');",
 "function isEmpty(v){if(v===null||v===undefined)return true;\n"
 "if(typeof v==='string'||Array.isArray(v))return v.length===0;\n"
 "if(typeof v==='object')return Object.keys(v).length===0;return false;}\n"
 "module.exports={isEmpty};"),
("js-042", "`compact(arr)` removing all falsy values.",
 "const {compact}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(compact([0,1,'',2,null,3]),[1,2,3]);console.log('OK');",
 "function compact(arr){return arr.filter(Boolean);}\nmodule.exports={compact};"),
("js-043", "`indexBy(arr, keyFn)` returning an object mapping key to the last item with that key.",
 "const {indexBy}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(indexBy([{i:1,v:'a'},{i:1,v:'b'}],o=>o.i),{1:{i:1,v:'b'}});console.log('OK');",
 "function indexBy(arr,keyFn){const o={};for(const x of arr)o[keyFn(x)]=x;return o;}\n"
 "module.exports={indexBy};"),
("js-044", "`formatBytes(n)` producing '512 B', '2.0 KB', '1.0 MB' using 1024 steps with one decimal "
 "above bytes.",
 "const {formatBytes}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(formatBytes(512),'512 B');a.strictEqual(formatBytes(2048),'2.0 KB');\n"
 "a.strictEqual(formatBytes(1048576),'1.0 MB');console.log('OK');",
 "function formatBytes(n){const u=['B','KB','MB','GB'];let i=0,f=n;\n"
 "while(f>=1024&&i<u.length-1){f/=1024;i++;}\n"
 "return i===0?`${f} B`:`${f.toFixed(1)} ${u[i]}`;}\nmodule.exports={formatBytes};"),
("js-045", "`sortByMulti(arr, keyFns)` sorting by several key functions in priority order, ascending, "
 "without mutating the input.",
 "const {sortByMulti}=require('./sol.js');const a=require('assert');\n"
 "const d=[{a:1,b:2},{a:1,b:1},{a:0,b:9}];\n"
 "a.deepStrictEqual(sortByMulti(d,[o=>o.a,o=>o.b]),[{a:0,b:9},{a:1,b:1},{a:1,b:2}]);\n"
 "console.log('OK');",
 "function sortByMulti(arr,keyFns){return arr.slice().sort((x,y)=>{for(const f of keyFns){\n"
 "const a=f(x),b=f(y);if(a<b)return -1;if(a>b)return 1;}return 0;});}\n"
 "module.exports={sortByMulti};"),
("js-046", "`truncate(s, n)` shortening a string to n characters appending '...' when it was cut.",
 "const {truncate}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(truncate('abcdefg',4),'abcd...');a.strictEqual(truncate('ab',5),'ab');\n"
 "console.log('OK');",
 "function truncate(s,n){return s.length<=n?s:s.slice(0,n)+'...';}\nmodule.exports={truncate};"),
("js-047", "`allSettledCounts(promises)` resolving with {fulfilled, rejected} counts.",
 "const {allSettledCounts}=require('./sol.js');const a=require('assert');\n"
 "(async()=>{const r=await allSettledCounts([Promise.resolve(1),Promise.reject(new Error('x'))]);\n"
 "a.deepStrictEqual(r,{fulfilled:1,rejected:1});console.log('OK');})()\n"
 ".catch(e=>{console.error(e);process.exit(1);});",
 "async function allSettledCounts(ps){const r=await Promise.allSettled(ps);\n"
 "return{fulfilled:r.filter(x=>x.status==='fulfilled').length,\n"
 "rejected:r.filter(x=>x.status==='rejected').length};}\nmodule.exports={allSettledCounts};"),
("js-048", "`toPairs(obj)` returning an array of [key, value] pairs in insertion order.",
 "const {toPairs}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(toPairs({a:1,b:2}),[['a',1],['b',2]]);console.log('OK');",
 "function toPairs(obj){return Object.entries(obj);}\nmodule.exports={toPairs};"),
("js-049", "`defaults(obj, defs)` filling in keys missing from obj, returning a new object.",
 "const {defaults}=require('./sol.js');const a=require('assert');\n"
 "a.deepStrictEqual(defaults({a:1},{a:9,b:2}),{a:1,b:2});console.log('OK');",
 "function defaults(obj,defs){return{...defs,...obj};}\nmodule.exports={defaults};"),
("js-050", "`countOccurrences(s, sub)` counting non-overlapping occurrences of a substring.",
 "const {countOccurrences}=require('./sol.js');const a=require('assert');\n"
 "a.strictEqual(countOccurrences('aaaa','aa'),2);a.strictEqual(countOccurrences('abc','z'),0);\n"
 "console.log('OK');",
 "function countOccurrences(s,sub){if(!sub)return 0;let n=0,i=0;\n"
 "while((i=s.indexOf(sub,i))!==-1){n++;i+=sub.length;}return n;}\n"
 "module.exports={countOccurrences};"),
]

# ---------------------------------------------------------------- TS (50)
TS = [
("ts-001", "export `function pick<T extends object, K extends keyof T>(obj: T, keys: K[]): Pick<T, K>` "
 "returning a new object with only those keys.",
 "import {pick} from './sol';import * as a from 'assert';\n"
 "const r=pick({a:1,b:'x',c:true},['a','b']);a.deepStrictEqual(r,{a:1,b:'x'});\n"
 "const n:number=r.a;a.strictEqual(n,1);console.log('OK');",
 "export function pick<T extends object, K extends keyof T>(obj:T,keys:K[]):Pick<T,K>{\n"
 "const out={} as Pick<T,K>;for(const k of keys)out[k]=obj[k];return out;}"),
("ts-002", "export `type Shape = {kind:'circle'; r:number} | {kind:'rect'; w:number; h:number}` and "
 "`function area(s: Shape): number` switching exhaustively on kind.",
 "import {area,Shape} from './sol';import * as a from 'assert';\n"
 "const s:Shape[]=[{kind:'circle',r:1},{kind:'rect',w:2,h:3}];\n"
 "a.ok(Math.abs(area(s[0])-Math.PI)<1e-9);a.strictEqual(area(s[1]),6);console.log('OK');",
 "export type Shape={kind:'circle';r:number}|{kind:'rect';w:number;h:number};\n"
 "export function area(s:Shape):number{switch(s.kind){case 'circle':return Math.PI*s.r*s.r;\n"
 "case 'rect':return s.w*s.h;}}"),
("ts-003", "export `type Result<T,E> = {ok:true; value:T} | {ok:false; error:E}` plus "
 "`function mapResult<T,U,E>(r: Result<T,E>, f:(t:T)=>U): Result<U,E>` applying f only on success.",
 "import {mapResult,Result} from './sol';import * as a from 'assert';\n"
 "const ok:Result<number,string>={ok:true,value:2};const bad:Result<number,string>={ok:false,error:'e'};\n"
 "a.deepStrictEqual(mapResult(ok,(x:number)=>x*3),{ok:true,value:6});\n"
 "a.deepStrictEqual(mapResult(bad,(x:number)=>x*3),{ok:false,error:'e'});console.log('OK');",
 "export type Result<T,E>={ok:true;value:T}|{ok:false;error:E};\n"
 "export function mapResult<T,U,E>(r:Result<T,E>,f:(t:T)=>U):Result<U,E>{\n"
 "return r.ok?{ok:true,value:f(r.value)}:r;}"),
("ts-004", "export `function groupBy<T,K extends string>(arr:T[], keyFn:(t:T)=>K): Record<K,T[]>`.",
 "import {groupBy} from './sol';import * as a from 'assert';\n"
 "const r=groupBy([1,2,3],n=>(n%2?'odd':'even') as 'odd'|'even');\n"
 "a.deepStrictEqual(r.odd,[1,3]);console.log('OK');",
 "export function groupBy<T,K extends string>(arr:T[],keyFn:(t:T)=>K):Record<K,T[]>{\n"
 "const o={} as Record<K,T[]>;for(const x of arr){const k=keyFn(x);(o[k]=o[k]||[]).push(x);}\n"
 "return o;}"),
("ts-005", "export `function compact<T>(arr:(T|null|undefined)[]): T[]` removing null and undefined "
 "with a type guard so the result is T[].",
 "import {compact} from './sol';import * as a from 'assert';\n"
 "const r:number[]=compact([1,null,2,undefined]);a.deepStrictEqual(r,[1,2]);console.log('OK');",
 "export function compact<T>(arr:(T|null|undefined)[]):T[]{\n"
 "return arr.filter((x):x is T=>x!==null&&x!==undefined);}"),
("ts-006", "export `interface User {id:number; name:string; email?:string}` and "
 "`function displayName(u:User):string` returning name, or 'anon' when name is empty.",
 "import {displayName,User} from './sol';import * as a from 'assert';\n"
 "const u:User={id:1,name:''};a.strictEqual(displayName(u),'anon');\n"
 "a.strictEqual(displayName({id:2,name:'Zed'}),'Zed');console.log('OK');",
 "export interface User{id:number;name:string;email?:string}\n"
 "export function displayName(u:User):string{return u.name||'anon';}"),
("ts-007", "export `function keysOf<T extends object>(o:T): (keyof T)[]`.",
 "import {keysOf} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(keysOf({a:1,b:2}).sort(),['a','b']);console.log('OK');",
 "export function keysOf<T extends object>(o:T):(keyof T)[]{return Object.keys(o) as (keyof T)[];}"),
("ts-008", "export `type Maybe<T> = T | null` and `function orElse<T>(v:Maybe<T>, d:T): T`.",
 "import {orElse} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(orElse<number>(null,5),5);a.strictEqual(orElse(2,5),2);console.log('OK');",
 "export type Maybe<T>=T|null;\nexport function orElse<T>(v:Maybe<T>,d:T):T{return v===null?d:v;}"),
("ts-009", "export `function partition<T>(arr:T[], pred:(t:T)=>boolean): [T[], T[]]`.",
 "import {partition} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(partition([1,2,3,4],n=>n%2===0),[[2,4],[1,3]]);console.log('OK');",
 "export function partition<T>(arr:T[],pred:(t:T)=>boolean):[T[],T[]]{\n"
 "const y:T[]=[],n:T[]=[];for(const x of arr)(pred(x)?y:n).push(x);return[y,n];}"),
("ts-010", "export `function zip<A,B>(a:A[], b:B[]): [A,B][]` stopping at the shorter array.",
 "import {zip} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(zip([1,2],['a','b']),[[1,'a'],[2,'b']]);console.log('OK');",
 "export function zip<A,B>(a:A[],b:B[]):[A,B][]{const n=Math.min(a.length,b.length);\n"
 "const o:[A,B][]=[];for(let i=0;i<n;i++)o.push([a[i],b[i]]);return o;}"),
("ts-011", "export `function assertNever(x: never): never` throwing, and use it to make "
 "`function label(k:'a'|'b'):string` exhaustive.",
 "import {label} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(label('a'),'A');a.strictEqual(label('b'),'B');console.log('OK');",
 "export function assertNever(x:never):never{throw new Error('unexpected '+String(x));}\n"
 "export function label(k:'a'|'b'):string{switch(k){case 'a':return 'A';case 'b':return 'B';\n"
 "default:return assertNever(k);}}"),
("ts-012", "export `function mapValues<T extends object,U>(o:T, f:(v:T[keyof T])=>U): Record<keyof T,U>`.",
 "import {mapValues} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(mapValues({a:1,b:2},v=>v*2),{a:2,b:4});console.log('OK');",
 "export function mapValues<T extends object,U>(o:T,f:(v:T[keyof T])=>U):Record<keyof T,U>{\n"
 "const out={} as Record<keyof T,U>;\n"
 "for(const k of Object.keys(o) as (keyof T)[])out[k]=f(o[k]);return out;}"),
("ts-013", "export `type DeepReadonly<T>` making every nested property readonly, and a function "
 "`freeze<T>(o:T): DeepReadonly<T>` returning the same object cast.",
 "import {freeze} from './sol';import * as a from 'assert';\n"
 "const f=freeze({a:{b:1}});a.strictEqual(f.a.b,1);console.log('OK');",
 "export type DeepReadonly<T>={readonly [K in keyof T]:T[K] extends object?DeepReadonly<T[K]>:T[K]};\n"
 "export function freeze<T>(o:T):DeepReadonly<T>{return o as DeepReadonly<T>;}"),
("ts-014", "export `function sumBy<T>(arr:T[], f:(t:T)=>number): number`.",
 "import {sumBy} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(sumBy([{v:1},{v:2}],o=>o.v),3);console.log('OK');",
 "export function sumBy<T>(arr:T[],f:(t:T)=>number):number{return arr.reduce((t,x)=>t+f(x),0);}"),
("ts-015", "export `class Stack<T>` with push, pop returning `T | undefined`, and a readonly size getter.",
 "import {Stack} from './sol';import * as a from 'assert';\n"
 "const s=new Stack<number>();s.push(1);s.push(2);a.strictEqual(s.size,2);\n"
 "a.strictEqual(s.pop(),2);a.strictEqual(s.size,1);console.log('OK');",
 "export class Stack<T>{private items:T[]=[];push(x:T):void{this.items.push(x);}\n"
 "pop():T|undefined{return this.items.pop();}get size():number{return this.items.length;}}"),
("ts-016", "export `function unique<T>(arr:T[]): T[]` preserving order.",
 "import {unique} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(unique([1,1,2]),[1,2]);console.log('OK');",
 "export function unique<T>(arr:T[]):T[]{return Array.from(new Set(arr));}"),
("ts-017", "export `function isString(x: unknown): x is string` and use it in "
 "`function joinStrings(xs: unknown[]): string` joining only the strings with commas.",
 "import {joinStrings} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(joinStrings(['a',1,'b']),'a,b');console.log('OK');",
 "export function isString(x:unknown):x is string{return typeof x==='string';}\n"
 "export function joinStrings(xs:unknown[]):string{return xs.filter(isString).join(',');}"),
("ts-018", "export `type Pair<A,B> = readonly [A,B]` and `function swap<A,B>(p:Pair<A,B>): Pair<B,A>`.",
 "import {swap} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(swap([1,'x'] as const),['x',1]);console.log('OK');",
 "export type Pair<A,B>=readonly [A,B];\n"
 "export function swap<A,B>(p:Pair<A,B>):Pair<B,A>{return [p[1],p[0]] as const;}"),
("ts-019", "export `function clamp(n:number, lo:number, hi:number): number`.",
 "import {clamp} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(clamp(5,1,3),3);console.log('OK');",
 "export function clamp(n:number,lo:number,hi:number):number{return Math.min(hi,Math.max(lo,n));}"),
("ts-020", "export `function entriesOf<T extends object>(o:T): [keyof T, T[keyof T]][]`.",
 "import {entriesOf} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(entriesOf({a:1}),[['a',1]]);console.log('OK');",
 "export function entriesOf<T extends object>(o:T):[keyof T,T[keyof T]][]{\n"
 "return Object.entries(o) as [keyof T,T[keyof T]][];}"),
("ts-021", "export `interface Node { value:number; children: Node[] }` and "
 "`function totalValue(n: Node): number` summing the tree.",
 "import {totalValue} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(totalValue({value:1,children:[{value:2,children:[]}]}),3);console.log('OK');",
 "export interface Node{value:number;children:Node[]}\n"
 "export function totalValue(n:Node):number{\n"
 "return n.value+n.children.reduce((t,c)=>t+totalValue(c),0);}"),
("ts-022", "export `function withDefault<T extends object>(o: Partial<T>, d: T): T`.",
 "import {withDefault} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(withDefault<{a:number;b:number}>({a:1},{a:9,b:2}),{a:1,b:2});console.log('OK');",
 "export function withDefault<T extends object>(o:Partial<T>,d:T):T{return {...d,...o};}"),
("ts-023", "export `type Handler = (e: {type:string}) => void` and `class Emitter` with "
 "`on(t:string,h:Handler)` and `emit(t:string)`.",
 "import {Emitter} from './sol';import * as a from 'assert';\n"
 "const e=new Emitter();let n=0;e.on('x',()=>n++);e.emit('x');a.strictEqual(n,1);\n"
 "e.emit('y');a.strictEqual(n,1);console.log('OK');",
 "export type Handler=(e:{type:string})=>void;\n"
 "export class Emitter{private h:Record<string,Handler[]>={};\n"
 "on(t:string,fn:Handler):void{(this.h[t]=this.h[t]||[]).push(fn);}\n"
 "emit(t:string):void{for(const fn of this.h[t]||[])fn({type:t});}}"),
("ts-024", "export `function firstOrNull<T>(arr:T[]): T | null`.",
 "import {firstOrNull} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(firstOrNull([1,2]),1);a.strictEqual(firstOrNull<number>([]),null);console.log('OK');",
 "export function firstOrNull<T>(arr:T[]):T|null{return arr.length?arr[0]:null;}"),
("ts-025", "export `function countBy<T>(arr:T[], f:(t:T)=>string): Record<string,number>`.",
 "import {countBy} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(countBy([1,2,3],n=>n%2?'o':'e'),{o:2,e:1});console.log('OK');",
 "export function countBy<T>(arr:T[],f:(t:T)=>string):Record<string,number>{\n"
 "const o:Record<string,number>={};for(const x of arr){const k=f(x);o[k]=(o[k]||0)+1;}return o;}"),
("ts-026", "export `type Status='idle'|'busy'|'done'` and `function next(s:Status): Status` cycling "
 "idle->busy->done->idle.",
 "import {next} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(next('idle'),'busy');a.strictEqual(next('done'),'idle');console.log('OK');",
 "export type Status='idle'|'busy'|'done';\n"
 "export function next(s:Status):Status{return s==='idle'?'busy':s==='busy'?'done':'idle';}"),
("ts-027", "export `function toRecord<T, K extends string>(arr:T[], key:(t:T)=>K): Record<K,T>`.",
 "import {toRecord} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(toRecord([{id:'a'}],o=>o.id),{a:{id:'a'}});console.log('OK');",
 "export function toRecord<T,K extends string>(arr:T[],key:(t:T)=>K):Record<K,T>{\n"
 "const o={} as Record<K,T>;for(const x of arr)o[key(x)]=x;return o;}"),
("ts-028", "export `function chunk<T>(arr:T[], n:number): T[][]`.",
 "import {chunk} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(chunk([1,2,3],2),[[1,2],[3]]);console.log('OK');",
 "export function chunk<T>(arr:T[],n:number):T[][]{const o:T[][]=[];\n"
 "for(let i=0;i<arr.length;i+=n)o.push(arr.slice(i,i+n));return o;}"),
("ts-029", "export `async function mapAsync<T,U>(arr:T[], f:(t:T)=>Promise<U>): Promise<U[]>` running "
 "sequentially.",
 "import {mapAsync} from './sol';import * as a from 'assert';\n"
 "(async()=>{const r=await mapAsync([1,2],async n=>n*2);a.deepStrictEqual(r,[2,4]);\n"
 "console.log('OK');})().catch(e=>{console.error(e);process.exit(1);});",
 "export async function mapAsync<T,U>(arr:T[],f:(t:T)=>Promise<U>):Promise<U[]>{\n"
 "const o:U[]=[];for(const x of arr)o.push(await f(x));return o;}"),
("ts-030", "export `function omit<T extends object, K extends keyof T>(o:T, keys:K[]): Omit<T,K>`.",
 "import {omit} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(omit({a:1,b:2},['b']),{a:1});console.log('OK');",
 "export function omit<T extends object,K extends keyof T>(o:T,keys:K[]):Omit<T,K>{\n"
 "const out={...o} as T;for(const k of keys)delete out[k];return out as Omit<T,K>;}"),
("ts-031", "export `function tryParse<T>(s:string): T | null` returning null on invalid JSON.",
 "import {tryParse} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(tryParse<{a:number}>('{\"a\":1}'),{a:1});\n"
 "a.strictEqual(tryParse('bad'),null);console.log('OK');",
 "export function tryParse<T>(s:string):T|null{try{return JSON.parse(s) as T;}catch{return null;}}"),
("ts-032", "export `function maxBy<T>(arr:T[], f:(t:T)=>number): T | undefined`.",
 "import {maxBy} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(maxBy([{v:1},{v:9}],o=>o.v),{v:9});console.log('OK');",
 "export function maxBy<T>(arr:T[],f:(t:T)=>number):T|undefined{\n"
 "return arr.length?arr.reduce((b,x)=>f(x)>f(b)?x:b):undefined;}"),
("ts-033", "export `type Reducer<S,A> = (s:S,a:A)=>S` and `function run<S,A>(r:Reducer<S,A>, init:S, "
 "actions:A[]): S`.",
 "import {run} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(run<number,number>((s,x)=>s+x,0,[1,2,3]),6);console.log('OK');",
 "export type Reducer<S,A>=(s:S,a:A)=>S;\n"
 "export function run<S,A>(r:Reducer<S,A>,init:S,actions:A[]):S{return actions.reduce(r,init);}"),
("ts-034", "export `function invert(o: Record<string,string>): Record<string,string>`.",
 "import {invert} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(invert({a:'1'}),{'1':'a'});console.log('OK');",
 "export function invert(o:Record<string,string>):Record<string,string>{\n"
 "const out:Record<string,string>={};for(const[k,v]of Object.entries(o))out[v]=k;return out;}"),
("ts-035", "export `function isDefined<T>(x: T | undefined): x is T` and use it in "
 "`function firstDefined<T>(xs:(T|undefined)[]): T | undefined`.",
 "import {firstDefined} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(firstDefined([undefined,3]),3);console.log('OK');",
 "export function isDefined<T>(x:T|undefined):x is T{return x!==undefined;}\n"
 "export function firstDefined<T>(xs:(T|undefined)[]):T|undefined{return xs.filter(isDefined)[0];}"),
("ts-036", "export `function repeat<T>(v:T, n:number): T[]`.",
 "import {repeat} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(repeat('a',3),['a','a','a']);console.log('OK');",
 "export function repeat<T>(v:T,n:number):T[]{return new Array(n).fill(v);}"),
("ts-037", "export `interface Cache<K,V>` with get/set and a `class MapCache<K,V> implements Cache<K,V>`.",
 "import {MapCache} from './sol';import * as a from 'assert';\n"
 "const c=new MapCache<string,number>();c.set('a',1);a.strictEqual(c.get('a'),1);\n"
 "a.strictEqual(c.get('z'),undefined);console.log('OK');",
 "export interface Cache<K,V>{get(k:K):V|undefined;set(k:K,v:V):void}\n"
 "export class MapCache<K,V> implements Cache<K,V>{private m=new Map<K,V>();\n"
 "get(k:K):V|undefined{return this.m.get(k);}set(k:K,v:V):void{this.m.set(k,v);}}"),
("ts-038", "export `function sortNumbers(xs:number[]): number[]` ascending without mutating input.",
 "import {sortNumbers} from './sol';import * as a from 'assert';\n"
 "const s=[3,1,2];a.deepStrictEqual(sortNumbers(s),[1,2,3]);a.deepStrictEqual(s,[3,1,2]);\n"
 "console.log('OK');",
 "export function sortNumbers(xs:number[]):number[]{return xs.slice().sort((a,b)=>a-b);}"),
("ts-039", "export `type Optional<T,K extends keyof T> = Omit<T,K> & Partial<Pick<T,K>>` and a function "
 "`make(o: Optional<{a:number;b:number},'b'>): {a:number;b:number}` defaulting b to 0.",
 "import {make} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(make({a:1}),{a:1,b:0});a.deepStrictEqual(make({a:1,b:2}),{a:1,b:2});\n"
 "console.log('OK');",
 "export type Optional<T,K extends keyof T>=Omit<T,K>&Partial<Pick<T,K>>;\n"
 "export function make(o:Optional<{a:number;b:number},'b'>):{a:number;b:number}{\n"
 "return {a:o.a,b:o.b??0};}"),
("ts-040", "export `function average(xs:number[]): number` returning 0 for empty.",
 "import {average} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(average([2,4]),3);a.strictEqual(average([]),0);console.log('OK');",
 "export function average(xs:number[]):number{return xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:0;}"),
("ts-041", "export `function hasKey<T extends object>(o:T, k:PropertyKey): k is keyof T`.",
 "import {hasKey} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(hasKey({a:1},'a'),true);a.strictEqual(hasKey({a:1},'z'),false);console.log('OK');",
 "export function hasKey<T extends object>(o:T,k:PropertyKey):k is keyof T{\n"
 "return Object.prototype.hasOwnProperty.call(o,k);}"),
("ts-042", "export `function flatten<T>(arr:T[][]): T[]`.",
 "import {flatten} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(flatten([[1],[2,3]]),[1,2,3]);console.log('OK');",
 "export function flatten<T>(arr:T[][]):T[]{return ([] as T[]).concat(...arr);}"),
("ts-043", "export `function pipe<A,B,C>(f:(a:A)=>B, g:(b:B)=>C): (a:A)=>C`.",
 "import {pipe} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(pipe((n:number)=>n+1,(n:number)=>n*2)(3),8);console.log('OK');",
 "export function pipe<A,B,C>(f:(a:A)=>B,g:(b:B)=>C):(a:A)=>C{return (a:A)=>g(f(a));}"),
("ts-044", "export `function truncate(s:string, n:number): string` appending '...' when cut.",
 "import {truncate} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(truncate('abcdefg',4),'abcd...');console.log('OK');",
 "export function truncate(s:string,n:number):string{return s.length<=n?s:s.slice(0,n)+'...';}"),
("ts-045", "export `function ensureArray<T>(v: T | T[]): T[]`.",
 "import {ensureArray} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(ensureArray(1),[1]);a.deepStrictEqual(ensureArray([1,2]),[1,2]);console.log('OK');",
 "export function ensureArray<T>(v:T|T[]):T[]{return Array.isArray(v)?v:[v];}"),
("ts-046", "export `function findIndexBy<T>(arr:T[], pred:(t:T)=>boolean): number` returning -1 when absent.",
 "import {findIndexBy} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(findIndexBy([1,2,3],n=>n===2),1);a.strictEqual(findIndexBy([1],n=>n===9),-1);\n"
 "console.log('OK');",
 "export function findIndexBy<T>(arr:T[],pred:(t:T)=>boolean):number{return arr.findIndex(pred);}"),
("ts-047", "export `type Brand<T,B extends string> = T & {readonly __brand:B}` and "
 "`function toUserId(n:number): Brand<number,'UserId'>`.",
 "import {toUserId} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(toUserId(5) as unknown as number,5);console.log('OK');",
 "export type Brand<T,B extends string>=T&{readonly __brand:B};\n"
 "export function toUserId(n:number):Brand<number,'UserId'>{return n as Brand<number,'UserId'>;}"),
("ts-048", "export `function last<T>(arr:T[]): T | undefined`.",
 "import {last} from './sol';import * as a from 'assert';\n"
 "a.strictEqual(last([1,2]),2);a.strictEqual(last<number>([]),undefined);console.log('OK');",
 "export function last<T>(arr:T[]):T|undefined{return arr[arr.length-1];}"),
("ts-049", "export `function fromEntries<K extends string,V>(e:[K,V][]): Record<K,V>`.",
 "import {fromEntries} from './sol';import * as a from 'assert';\n"
 "a.deepStrictEqual(fromEntries([['a',1]]),{a:1});console.log('OK');",
 "export function fromEntries<K extends string,V>(e:[K,V][]):Record<K,V>{\n"
 "const o={} as Record<K,V>;for(const[k,v]of e)o[k]=v;return o;}"),
("ts-050", "export `function debounceState(): {pending:boolean; mark():void; clear():void}`.",
 "import {debounceState} from './sol';import * as a from 'assert';\n"
 "const d=debounceState();a.strictEqual(d.pending,false);d.mark();a.strictEqual(d.pending,true);\n"
 "d.clear();a.strictEqual(d.pending,false);console.log('OK');",
 "export function debounceState():{pending:boolean;mark():void;clear():void}{\n"
 "return{pending:false,mark(){this.pending=true;},clear(){this.pending=false;}};}"),
]


def tasks_js():
    return [(tid, "Write JavaScript defining " + spec +
             " Export it with module.exports. Output only the code, no explanation.", tests)
            for tid, spec, tests, _r in JS]


def tasks_ts():
    return [(tid, "Write TypeScript that " + spec +
             " It must typecheck under --strict. Output only the code, no explanation.", tests)
            for tid, spec, tests, _r in TS]


if __name__ == "__main__":
    for name, rows in (("js", JS), ("ts", TS)):
        ids = [r[0] for r in rows]
        assert len(ids) == len(set(ids)), f"dup ids in {name}"
        print(f"{name} tasks: {len(rows)}  ids unique: ok")
