# 此脚本在计算时会需要一定的时间，所以输出的步长时间应该要大于计算时间，不然会造成脏读、或者丢失更新的现象
# low最好1500步
# gpu最好7000步

import time
import os
from Lacomplex import Lacomplex
import numpy as np
import pandas as pd

lc = Lacomplex()
# cutoff = 999                         ########
# task = [""]
# shape = "cubic"
# d = 116.6782
"""if shape == "dodecahedron":
    pbc_box = [[d, 0, d * 0.5],
               [0, d, d * 0.5],
               [0, 0, d * 0.5 * np.sqrt(2)]]
if shape == "cubic":
    pbc_box = [[d, 0, 0],
               [0, d, 0],
               [0, 0, d]]"""

a_atom_cor_o, b_atom_cor_o, a_atom_nam, b_atom_nam, a_b_heavy_si = lc.readHeavyAtom("./start.pdb", monitor=True)

def process(FileName, pre_EMA, first):
    a = np.exp(-20 / 60)  # dt/τ        ########
    atom_cor = []  # 存储A、B重原子坐标
    end = len(a_b_heavy_si)

    with open(FileName, 'r') as f:
        n = 0
        for i in f.readlines():
            if a_b_heavy_si[n]:
                record = i.strip().split()
                atom_cor.append([float(j) * 10 for j in record])
            n += 1
            if n >= end:
                # print("n:", n)
                # print("end:", end)
                break

    atom_cor = np.array(atom_cor)
    # print("atom_cor:", atom_cor.shape)

    a_check_cor = atom_cor[:len(a_atom_nam)]
    b_check_cor = atom_cor[len(a_atom_nam):]

    # print("a_check_cor:", len(a_check_cor))
    # print("b_check_cor:", len(b_check_cor))

    lc.csv_path = './'
    lc.calContact(a_check_cor, b_check_cor, a_atom_nam=a_atom_nam, b_atom_nam=b_atom_nam, filename='extract_cor',
                  save_dis=True)
    aa_contact = list(np.load('./aa_contact.npy', allow_pickle=True).item())
    aa_contact.sort()
    contact_dif = np.zeros(shape=(1, len(aa_contact)))

    dataframe = pd.read_csv('./extract_cor.csv')
    new_col = ['Unnamed: 0']
    new_index = []
    # 去除原子序数
    for col in dataframe.columns[1:]:
        record = col.split('-')
        new_col.append(record[0] + '-' + record[1] + '-' + record[2])
    for row in dataframe[dataframe.columns[0]]:
        record = row.split('-')
        new_index.append(record[0] + '-' + record[1] + '-' + record[2])
    dataframe.columns = new_col
    dataframe.index = new_index

    # 构建含有CB的cp
    for l in range(len(aa_contact)):
        cp = aa_contact[l]
        a_rec = cp[0].split('-')
        b_rec = cp[1].split('-')
        a_atom = a_rec[0] + '-' + a_rec[1] + '-' + ['CB' if a_rec[1] != 'GLY' else 'CA'][0]
        b_atom = b_rec[0] + '-' + b_rec[1] + '-' + ['CB' if b_rec[1] != 'GLY' else 'CA'][0]
        contact_dif[0][l] = dataframe[a_atom][b_atom]  # 先列后行,索引需要减2

    w = np.load('./w_dis.npy', allow_pickle=True)

    value = (np.mat(contact_dif) * w).tolist()[0][0]

    if not first:
        EMA = a * value + (1 - a) * pre_EMA
    else:
        EMA = value
        first = False
    return EMA, first, value

def MD_monitor():
    # 因为导出的pdb只有蛋白质链上会有Chain ID，所以不用担心会读取到其他的信息

    EMA = 0  # Exponential Moving Average, EMA
    first = True
    EMA_npy = []
    value_npy = []
    n = 0

    while True:
        FileName = './extract_cor.txt'
        if os.path.exists(FileName):
            # Read fime name
            original_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.stat(FileName).st_mtime))
            time.sleep(1)
            # print file modified time
            modified_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.stat(FileName).st_mtime))
            if original_time != modified_time:
                time.sleep(3)  # 避免脏读
                start_t = time.time()
                with open('./log_dis.txt', 'a') as f:
                    f.write("###############  frame:{0} ###############".format(n) + '\n')
                    f.write("Original : " + original_time + '\n')
                    f.write("Now      : " + modified_time + '\n')
                    f.write("It has been changed!" + '\n')
                    EMA, first, value = process(FileName, EMA, first)

                    EMA_npy.append(EMA)
                    value_npy.append(value)
                    np.save("./EMA_dis.npy", np.array(EMA_npy))
                    np.save("./value_dis.npy", np.array(value_npy))

                    f.write("value    : " + str(value) + '\n')
                    f.write("EMA      : " + str(EMA) + '\n')
                    end_t = time.time()
                    f.write("Time used: " + str(end_t - start_t) + '\n')
                    f.write("############### Done process! ###############" + '\n')
                f.close()
                n += 1

MD_monitor()

