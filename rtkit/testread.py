import yaml  
f=open('data.yaml')  
settings=yaml.load(f)  
print 'tinfo', settings[0]
print 'attachments', settings[1]
print 'comments', len(settings[2])
