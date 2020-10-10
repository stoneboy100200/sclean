import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import csv
import argparse
import os
import time
import sys

usr_process = ['algorithm_app',
               'data_source_app',
               'MCSApp',
               'MCenter',
               'cali_upload',
               'jt_app',
               'main.out',
               'storage.out',
               'MTransferCenter',
               'test_tuning']

def to_csv(path, file):
    with open(file, 'w+', newline='') as csvfile:
        csv_file = csv.writer(csvfile, dialect='excel')
        with open(path, 'r', encoding='utf-8') as filein:
            for line in filein:
                line_list = line.strip('\n').split()
                csv_file.writerow(line_list)

def match_cpu_core(detail):
    cpu = {}
    def cpu_core(tgid_g, tid_g, core):
        if tid_g.isdigit():
            cpu.setdefault(tid_g, set()).add(core)
        elif tgid_g.isdigit():
            cpu.setdefault(tgid_g, set()).add(core)

    detail.apply(lambda row: cpu_core(row['TGID'], row['TID'], row['CPU']), axis = 1)
    return cpu

def gen_data(data):
    # delete rows that contain 'Average:'
    detail = data[~data['Time'].isin(['Average:'])]
    cpu = match_cpu_core(detail)

    # get rows that contain 'Average:'
    av = data[data['Time'] == 'Average:']
    av = av.reset_index(drop=True)
    av = av.drop(index=[0], axis = 0)

    def get_cpu_core(tgid, tid):
        return sorted(list(map(int, cpu[tid] if tid.isdigit() else cpu[tgid])))
    av['CPU'] = av.apply(lambda row: get_cpu_core(row['TGID'], row['TID']), axis = 1)
    av = av.drop(columns=['Time', 'UID'])
    return av

def add_process(data):
    process = ""
    def get_process(tgid, command):
        global process
        if tgid.isdigit():
            process = command
        return process
    data['Process'] = data.apply(lambda row: get_process(row['TGID'], row['Thread']), axis = 1)

def filter_process(data):
    data = data[data['TGID'].isin(['-'])]
    data = data[data['Process'].isin(usr_process)]
    return data

def get_graph_data(data):
    data[['%usr', '%system', '%CPU']] = data[['%usr', '%system', '%CPU']].astype(float)
    process = data.groupby(data['Process'])[['%usr', '%system', '%CPU']].sum()
    x_list = process.index
    index = np.arange(len(x_list));
    y_list1 = round(process['%usr'], 2)
    y_list2 = round(process['%system'], 2)
    y_list3 = round(process['%CPU'], 2)
    return x_list, index, y_list1, y_list2, y_list3

def set_graph_param(data, ax, bar_width, title):
    x_list, index, y_list1, y_list2, y_list3 = get_graph_data(data)
    rect1 = ax.bar(index-bar_width, y_list1, bar_width, label='usr')
    rect2 = ax.bar(index, y_list2, bar_width, label='system')
    rect3 = ax.bar(index+bar_width, y_list3, bar_width, label='total')
    ax.set_ylabel('CPU Usage(%)')
    ax.set_xticks(index)
    ax.set_xticklabels(x_list, rotation=10)
    ax.set_title(title)
    ax.set_ylim(0, 100)
    ax.legend(loc='upper right', frameon=False)
    auto_text(rect1, ax)
    auto_text(rect2, ax)
    auto_text(rect3, ax)

def gen_graph(data_0, data_1, data_2, data_3, data_n):
    bar_width=0.3
    fig, (ax0, ax1, ax2, ax3, ax4) = plt.subplots(5, figsize=(12, 20))
    plt.subplots_adjust(hspace=0.5)
    set_graph_param(data_0, ax0, bar_width, 'CPU0')
    set_graph_param(data_1, ax1, bar_width, 'CPU1')
    set_graph_param(data_2, ax2, bar_width, 'CPU2')
    set_graph_param(data_3, ax3, bar_width, 'CPU3')
    set_graph_param(data_n, ax4, bar_width, 'CPU0~CPU3')
    plt.savefig("pidstat.png", facecolor="white")

def auto_text(rects, ax):
    for rect in rects:
        ax.text(rect.get_x(), rect.get_height(), rect.get_height(), ha='left', va='bottom')

def sort_by_cpu(data):
    # add a new column for length of 'CPU'
    data['Len'] = data.apply(lambda row: len(row['CPU']), axis = 1)
    data = data.sort_values(by = 'Len' , ascending = True)
    data_s = data.loc[data['Len'] == 1].sort_values(by = 'CPU', ascending = True)
    data_m = data.loc[data['Len'] != 1]
    data = data_s.append(data_m)

    # transform list to str
    data['CPU'] = data['CPU'].apply(lambda row: ','.join(str(i) for i in row))
    # sort by 'Process' and 'TID'
    data_0 = data.loc[data['CPU'] == '0'].sort_values(by = ['Process', 'TID'], ascending = True)
    data_1 = data.loc[data['CPU'] == '1'].sort_values(by = ['Process', 'TID'], ascending = True)
    data_2 = data.loc[data['CPU'] == '2'].sort_values(by = ['Process', 'TID'], ascending = True)
    data_3 = data.loc[data['CPU'] == '3'].sort_values(by = ['Process', 'TID'], ascending = True)
    data_n = data.loc[data['Len'] != 1].sort_values(by = ['Process', 'TID'], ascending = True)
    # gen bar graph for every CPU
    gen_graph(data_0, data_1, data_2, data_3, data_n)

    data = pd.concat([data_0, data_1, data_2, data_3, data_n], axis=0,ignore_index=True)
    data = data.drop(columns=['Len'])
    return data


def main(args):
    data_path = args.path
    file = args.file
    print("data_path={}".format(data_path))
    if not os.path.exists(data_path):
        print("[Error] {} does not exist!".format(data_path))
        sys.exit(1)
    if len(file) == 0:
        file = 'pid_stat.csv'

    if os.path.exists(file):
        org_file = file
        now = time.strftime("%Y-%m-%d-%H_%M_%S",time.localtime(time.time()))
        file = now + r"_" + file
        print("{} already exist, it will be renamed with {}".format(org_file, file))
    else:
        print("file={}".format(file))

    # convert to csv file
    to_csv(data_path, file)
    data = pd.read_csv(file, header=0,
                       names=['Time', 'UID', 'TGID', 'TID', '%usr', '%system', '%guest', '%wait', '%CPU', 'CPU', 'Thread'])
    # data cleaning
    av = gen_data(data)
    add_process(av)
    # remove row of main process
    av = filter_process(av)
    av = sort_by_cpu(av)

    # save by csv
    order = ['Thread', 'Process', 'TGID', 'TID', '%usr', '%system', '%guest', '%wait', '%CPU', 'CPU']
    av.to_csv(file, index=False, columns = order)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="data cleaning tool for pidstat. Develop by LiChao.")
    parser.add_argument("-p", "--path", type=str, default="", help="path of original file.")
    parser.add_argument("-f", "--file", type=str, default="", help="name of target file.")
    args = parser.parse_args()
    main(args)
