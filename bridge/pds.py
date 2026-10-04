import re
TOKEN=re.compile(r'"(?:\\.|[^"\\])*"|\#[^\n]*|[{}=]|[^\s{}=#]+')
def entries(text):
 text=text.lstrip('\ufeff')
 tokens=[m for m in TOKEN.finditer(text) if not m[0].startswith('#')];out=[];i=0
 while i+2<len(tokens):
  if tokens[i+1][0]!='=':i+=1;continue
  key=tokens[i][0].strip('"');start=tokens[i].start();value=tokens[i+2]
  if value[0]=='{':
   depth=1;j=i+3
   while j<len(tokens) and depth:
    depth+=(tokens[j][0]=='{')-(tokens[j][0]=='}');j+=1
   if depth:raise ValueError('Unclosed PDS block: '+key)
   end=tokens[j-1].end();out.append({'key':key,'block':True,'inner':text[value.end():tokens[j-1].start()],'raw':text[start:end]});i=j
  else:out.append({'key':key,'block':False,'value':value[0],'raw':text[start:value.end()]});i+=3
 return out
def block(key,inner):return key+' = {\n'+inner+'\n}\n'
def fields(text):return {e['key']:e.get('value','').strip('"') for e in entries(text)}
