lines=open('main.py','r',encoding='utf-8').read().splitlines()
print('LINE 200:',repr(lines[199]))
for i in range(200,260):
    if 'except Exception as e' in lines[i]:
        print('found except at', i+1, repr(lines[i]))
        break
else:
    print('no except found in 200-260')
print('\nContext:')
for i in range(188,270):
    print(f"{i+1:4}: {lines[i]!r}")
