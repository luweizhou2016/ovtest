import sys

n = len(sys.argv)
convert_list = ['(', ')', '{', '}']

if n != 2:
    print('invalid input argument') 
org = sys.argv[1]
for a in convert_list:
    print(a)
    escape = f'\{a}'
    print(escape)
    org = org.replace(a,  escape)
print(org)