import numpy as np
import pandas as pd
import csv
import argparse
import os
import time
import sys

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
    # detail.to_csv('detail.csv')
    cpu = match_cpu_core(detail)

    # get rows that contain 'Average:'
    av = data[data['Time'] == 'Average:']
    av = av.reset_index(drop=True)
    av = av.drop(index=[0], axis = 0)

    def get_cpu_core(tgid, tid):
        return sorted(list(cpu[tid] if tid.isdigit() else cpu[tgid]))
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
    data['Process'] = data.apply(lambda row: get_process(row['TGID'], row['Command']), axis = 1)

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
                       names=['Time', 'UID', 'TGID', 'TID', '%usr', '%system', '%guest', '%wait', '%CPU', 'CPU', 'Command'])
    # data cleaning
    av = gen_data(data)
    add_process(av)

    order = ['Command', 'Process', 'TGID', 'TID', '%usr', '%system', '%guest', '%wait', '%CPU', 'CPU']
    av.to_csv(file, index=False, columns = order)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="data cleaning tool for pidstat. Develop by LiChao.")
    parser.add_argument("-p", "--path", type=str, default="", help="path of original file.")
    parser.add_argument("-f", "--file", type=str, default="", help="name of target file.")
    args = parser.parse_args()
    main(args)
