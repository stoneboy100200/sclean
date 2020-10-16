#!/usr/bin/env python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import csv
import argparse
import os
import time
import sys
from matplotlib import font_manager as fm, rcParams

# compatible with Chinese fonts
plt.rcParams['font.sans-serif'] = ['SimHei']

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

def convert_csv(path, file):
    # remove the first line to avoid converting error (not utf8)
    os.system("sed -i -e '/Linux/d' " + path)
    with open(file, 'w+', newline='') as csvfile:
        csv_file = csv.writer(csvfile, dialect='excel')
        with open(path, 'r', encoding='utf-8') as filein:
            next(filein)
            for line in filein:
                line_list = line.strip('\n').split()
                csv_file.writerow(line_list)

# def check_file_charset(file):
#     with open(file,'rb') as f:
#         return chardet.detect(f.read())
#     return {}

# def to_utf8(file):
#     f_type = check_file_charset(file)
#     print("file type: {}".format(f_type))
#     if f_type and 'encoding' in f_type.keys() and f_type['encoding'] != 'utf-8':
#         try:
#             with codecs.open(file, 'rb', f_type['encoding']) as f:
#                 content = smart_text(f.read())
#             with codecs.open(file, 'wb', 'utf-8') as f:
#                 f.write(content)
#         except:
#             print("[Error]: failed to convert to utf8!")
#             pass


def match_cpu_core(detail):
    cpu = {}
    def cpu_core(tgid_g, tid_g, core):
        if tid_g.isdigit():
            cpu.setdefault(tid_g, set()).add(core)
        elif tgid_g.isdigit():
            cpu.setdefault(tgid_g, set()).add(core)

    detail.apply(lambda row: cpu_core(row['tgid'], row['tid'], row['cpu']), axis = 1)
    return cpu

def gen_thread_graph(data, thread, p_status):
    thread_data = filter_process(data)
    tid_data = thread_data[thread_data['tid'] == thread]
    if len(tid_data) != 0:
        fig = plt.figure(figsize = (20, 10))
        set_line_char_param(tid_data, p_status, "Thread "+thread)
        plt.savefig(thread+".jpg", bbox_inches='tight')


def gen_data(data, thread, p_status):
    # delete rows that contain 'Average:'
    detail = data[~data.index.isin(['Average:'])]
    if len(thread) != 0:
        gen_thread_graph(detail, thread, p_status)
    cpu = match_cpu_core(detail)

    # get rows that contain 'Average:'
    av = data[data.index.isin(['Average:'])]
    av = av.reset_index(drop=True)
    av = av.drop(index=[0], axis = 0)

    def get_cpu_core(tgid, tid):
        return sorted(list(map(int, cpu[tid] if tid.isdigit() else cpu[tgid])))
    av['cpu'] = av.apply(lambda row: get_cpu_core(row['tgid'], row['tid']), axis = 1)
    return av

def add_process(data):
    process = ""
    def get_process(tgid, command):
        global process
        if tgid.isdigit():
            process = command
        return process
    data['process'] = data.apply(lambda row: get_process(row['tgid'], row['command']), axis = 1)

def filter_process(data):
    data = data[data['tgid'].isin(['-'])]
    # data = data[data['process'].isin(usr_process)]
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
    plt.subplots_adjust(hspace=0.4)
    set_graph_param(data_0, ax0, bar_width, 'CPU0')
    set_graph_param(data_1, ax1, bar_width, 'CPU1')
    set_graph_param(data_2, ax2, bar_width, 'CPU2')
    set_graph_param(data_3, ax3, bar_width, 'CPU3')
    set_graph_param(data_n, ax4, bar_width, 'CPU0~CPU3')
    plt.savefig("pidstat.png", facecolor="white", bbox_inches='tight')

def auto_text(rects, ax):
    for rect in rects:
        ax.text(rect.get_x(), rect.get_height(), rect.get_height(), ha='left', va='bottom')

def sort_by_cpu(data, core):
    # add a new column for length of 'CPU'
    data['len'] = data.apply(lambda row: len(row['cpu']), axis = 1)
    data = data.sort_values(by = 'len' , ascending = True)
    data_s = data.loc[data['len'] == 1].sort_values(by = 'cpu', ascending = True)
    data_m = data.loc[data['len'] != 1]
    data = data_s.append(data_m)

    # transform list to str
    data['cpu'] = data['cpu'].apply(lambda row: ','.join(str(i) for i in row))
    cpu_data = []
    for i, cpu in enumerate(core):
        core_data = data[(data['cpu'].isin([cpu])) & (data['len'] == 1)]
        if len(core_data) != 0:
            cpu_data.append(core_data.sort_values(by = ['process', 'tid'], ascending = True))

    cpu_unbound = data.loc[data['len'] != 1].sort_values(by = ['process', 'tid'], ascending = True)
    if len(cpu_unbound) != 0:
        cpu_data.append(cpu_unbound)
    data = pd.concat(cpu_data, axis = 0, ignore_index = True)
    data = data.drop(columns=['len'])
    return data

def set_line_char_param(cpu_data, cpu_status, title):
    line_color = ['b', 'r', 'g', 'y', 'k', 'c', 'm', 'pink', 'darkred', 'olive', 'lime', 'deeppink']
    line_style = '-'
    x_num = 30
    x_step = 35

    if len(cpu_data.index) > x_num:
        x_step = int(len(cpu_data.index) / x_num)
    for i, status in enumerate(cpu_status):
        plt.plot(cpu_data.index, cpu_data[status].astype(float), color = line_color[i], linestyle = line_style)
    plt.xlabel('Time', fontsize = 12)
    if title[0:3] == 'CPU':
        plt.ylabel('CPU Usage(%)', fontsize = 12)
    else:
        plt.ylabel('Mem Usage(KB)', fontsize = 12)

    plt.xticks(np.arange(0, len(cpu_data.index), x_step), cpu_data.iloc[np.arange(0, len(cpu_data.index), x_step), 0].index, rotation = 25)
    if title[0:3] == 'CPU':
        plt.ylim(0,100)
    plt.legend(cpu_status)
    plt.title(title)

def gen_line_chart(data, core, cpu_status):
    detail = data[~data.index.isin(['Average:'])]
    graph_num = len(core)
    fig = plt.figure(figsize = (20, graph_num*5))
    plt.subplots_adjust(hspace=0.4)
    for i, cpu in enumerate(core):
        cpu_data = detail[detail['cpu'].isin([cpu])]
        if len(cpu_data) != 0:
            subgraph_pos = str(graph_num) + '1' + str(i+1)
            plt.subplot(int(subgraph_pos))
            set_line_char_param(cpu_data, cpu_status, 'CPU'+cpu)
        else:
            print("[Warning] CPU core is invalid")

    plt.savefig("mpstat.jpg", bbox_inches='tight')

def pidstat_process(pidstat_path, core, thread, p_status):
    if not os.path.exists(pidstat_path):
        print("[Error] {} does not exist!".format(pidstat_path))
        sys.exit(1)
    print("pidstat_path={}".format(pidstat_path))

    # convert to csv file
    file = 'pidstat.csv'
    convert_csv(pidstat_path, file)
    data = pd.read_csv(file, header=0, index_col=0)
    data.columns = data.columns.map(lambda x:x.lower())
    cpu_status = ['%'+i for i in p_status]
    av = gen_data(data, thread, cpu_status)
    add_process(av)
    # remove row of main process
    av = filter_process(av)
    av = sort_by_cpu(av, core)
    av.to_csv(file, index=False)

def mpstat_process(mpstat_path, core, m_status):
    if not os.path.exists(mpstat_path):
        print("[Error] {} does not exist!".format(mpstat_path))
        sys.exit(1)
    print("mpstat_path={}".format(mpstat_path))

    # convert to csv file
    file = 'mpstat.csv'
    convert_csv(mpstat_path, file)
    data = pd.read_csv(file, header=0, index_col=0)
    data.columns = data.columns.map(lambda x:x.lower())
    cpu_status = ['%'+i for i in m_status]
    gen_line_chart(data, core, cpu_status)

def vmstat_process(vmstat_path, v_status):
    if not os.path.exists(vmstat_path):
        print("[Error] {} does not exist!".format(vmstat_path))
        sys.exit(1)
    print("vmstat_path={}".format(vmstat_path))

    # convert to csv file
    file = 'vmstat.csv'
    convert_csv(vmstat_path, file)
    data = pd.read_csv(file, header=0)
    # print(data)
    data.columns = data.columns.map(lambda x:x.lower())
    v_data = data[data.r.apply(lambda x: x.isnumeric())]
    # print(v_data)
    fig = plt.figure(figsize = (20, 10))
    set_line_char_param(v_data, v_status, 'vmstat')
    plt.savefig("vmstat.jpg", bbox_inches='tight')


def main(args):
    pidstat_path = args.pidstat
    mpstat_path = args.mpstat
    vmstat_path = args.vmstat
    thread = args.thread
    core = args.core
    m_status = args.m_status
    p_status = args.p_status
    v_status = args.v_status

    if len(pidstat_path) != 0:
        pidstat_process(pidstat_path, core, thread, p_status)
    if len(mpstat_path) != 0:
        mpstat_process(mpstat_path, core, m_status)
    if len(vmstat_path) != 0:
        vmstat_process(vmstat_path, v_status)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="data cleaning tool for pidstat and mpstat.")
    parser.add_argument("-p", "--pidstat", type=str, default="", help="path of pidstat log.")
    parser.add_argument("-m", "--mpstat", type=str, default="", help="path of mpstat log.")
    parser.add_argument("-v", "--vmstat", type=str, default="", help="path of vmstat log.")
    parser.add_argument("-c", "--core", type=str, default=['0'], nargs='*', help="CPU core.")
    parser.add_argument("-ms", "--m_status", type=str, default=['usr', 'sys', 'iowait', 'idle'], nargs='*', help="status of mpstat. eg. usr sys idle")
    parser.add_argument("-ps", "--p_status", type=str, default=['usr', 'system', 'cpu'], nargs='*', help="status of pidstat. eg. usr system")
    parser.add_argument("-vs", "--v_status", type=str, default=['free', 'buff', 'cache'], nargs='*', help="status of vmstat. eg. free in cs")
    parser.add_argument("-t", "--thread", type=str, default="", help="thread number.")
    args = parser.parse_args()
    main(args)
