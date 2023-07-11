import sys

if len(sys.argv) != 4:
    print("Unsupported argument number!")
    print("get_list.py ci_list.txt full_list.txt INT8/FP32/FP16")
    sys.exit(0) 
if (sys.argv[3] != 'INT8' and sys.argv[3] != 'FP16' and sys.argv[3] != 'FP32'):
    print("unsupported Precision, INT8/FP16/FP32")
    sys.exit(0) 

# Using readlines()
file1 = open(sys.argv[1], 'r')
Line1s = file1.readlines()
file2 = open(sys.argv[2], 'r')
Line2s = file2.readlines()
outfile = open(sys.argv[3].lower()+'_out_list.txt', 'w')
# Strips the newline character
for line1 in Line1s:
    lists = line1.split()
    if (lists[5] != sys.argv[3]):
        continue
    for line2 in Line2s:
        if (line2.find('/'+ lists[3] + '/' + lists[4].lower()+'/') != -1 and line2.find('/'+lists[5]+'/') != -1):
            # print('------------------------')
            # print(lists[3]+'/')
            # print(lists[4].lower()+'/')
            # print(lists[5]+'/')
            # print(line2)
            outfile.write(line2[:-1]+' ./configs/fp16/i3d-flow-tf.yml\n')
outfile.close()
file2.close()
file1.close()
