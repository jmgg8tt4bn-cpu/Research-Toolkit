# -*- coding: utf-8 -*-

import os
import glob
import re
import numpy as np
import pandas as pd  # 用于导出 Excel

# ------------------------ 核心配置区 ------------------------
CENTER_ATOM = "Pb"      # 中心原子
COORD_ATOM = "I"        # 配位原子

# 数据文件 (.dat) 的键长过滤范围
MIN_DIST = 1.5          
MAX_DIST = 5.0          

# --- 结构几何判定参数 ---
MAX_COORD_DIST = 3.8    # 最大配位键长(Å)：用于识别哪些原子属于同一个八面体
AXIAL_VECTOR =[1.0, 0.0, 0.0] # 指定轴向键的参考向量 (笛卡尔坐标系)
TOL_DEG = 30.0          # 角度容忍度：与 AXIAL_VECTOR 夹角在 0±30° 或 180±30° 内的被识别为轴向键

# --- Excel 输出配置 ---
EXCEL_OUTPUT_FILE = "Bond_Statistics_Result.xlsx"  # 导出的 Excel 文件名
# -------------------------------------------------------------

def read_poscar(poscar_path):
    """读取 POSCAR，返回晶格基矢、元素列表和分数坐标"""
    with open(poscar_path, 'r') as f:
        lines =[l.strip() for l in f if l.strip()]
    
    scale = float(lines[1])
    cell = np.array([[float(x) for x in lines[2].split()],[float(x) for x in lines[3].split()],
                     [float(x) for x in lines[4].split()]]) * scale

    if lines[5].split()[0].isalpha():
        element_names = lines[5].split()
        element_counts = list(map(int, lines[6].split()))
        coord_start = 8
        if lines[7].lower()[0] == 's': 
            coord_start = 9
            is_direct = lines[8].lower()[0] == 'd'
        else:
            is_direct = lines[7].lower()[0] == 'd'
    else:
        raise ValueError("仅支持包含元素符号的 VASP 5+ POSCAR 格式。")

    elements =[]
    for name, count in zip(element_names, element_counts):
        elements.extend([name] * count)
    
    coords = []
    for line in lines[coord_start:coord_start+len(elements)]:
        x, y, z = map(float, line.split()[:3])
        coords.append([x, y, z])
    coords = np.array(coords)

    if not is_direct:
        inv_cell = np.linalg.inv(cell)
        coords = np.dot(coords, inv_cell)

    return cell, elements, coords

def build_center_coord_map(cell, elements, coords, center_atom, coord_atom):
    """
    考虑周期性边界条件(PBC)，找出每个中心原子的配位原子，并区分轴向和赤道向
    """
    center_map = {}
    axis_vec = np.array(AXIAL_VECTOR, dtype=float)
    axis_vec = axis_vec / np.linalg.norm(axis_vec)

    center_indices =[i for i, e in enumerate(elements) if e == center_atom]
    coord_indices =[i for i, e in enumerate(elements) if e == coord_atom]

    for c_idx in center_indices:
        c_coord = coords[c_idx]
        axial = []
        equatorial =[]
        
        for i in coord_indices:
            diff_frac = coords[i] - c_coord
            diff_frac = diff_frac - np.round(diff_frac)
            diff_cart = np.dot(diff_frac, cell)
            dist = np.linalg.norm(diff_cart)
            
            if dist > MAX_COORD_DIST or dist < 0.1:
                continue
                
            v_dir = diff_cart / dist
            cos_theta = np.clip(np.dot(v_dir, axis_vec), -1.0, 1.0)
            angle_deg = np.degrees(np.arccos(cos_theta))
            
            if angle_deg <= TOL_DEG or angle_deg >= (180 - TOL_DEG):
                axial.append(i + 1)
            else:
                equatorial.append(i + 1)
                
        center_map[c_idx + 1] = {'axial': axial, 'equatorial': equatorial}
    return center_map

def analyze_dat_file(dat_file, center_map, min_dist, max_dist):
    summary_stats = {}   
    detailed_stats = {}  
    
    with open(dat_file, 'r') as f:
        current_distance = 0.0
        for line in f:
            line = line.strip()
            if not line: continue
            
            match = re.search(r'distance\s*=\s*(\d+\.\d+)', line)
            if match:
                current_distance = float(match.group(1))
                continue
            
            if current_distance < min_dist or current_distance > max_dist:
                continue
                
            parts = line.split()
            for part in parts:
                if '-' not in part: continue
                atoms = re.findall(r'([A-Za-z]+)(\d+)', part)
                if len(atoms) != 2: continue
                
                elem1, num1 = atoms[0]
                elem2, num2 = atoms[1]
                num1, num2 = int(num1), int(num2)

                for center, local_bonds in center_map.items():
                    orientation = None
                    coord_num = None
                    
                    if center == num1 and elem2 == COORD_ATOM:
                        coord_num = num2
                    elif center == num2 and elem1 == COORD_ATOM:
                        coord_num = num1
                        
                    if coord_num is not None:
                        if coord_num in local_bonds['axial']:
                            orientation = 'axial'
                        elif coord_num in local_bonds['equatorial']:
                            orientation = 'equatorial'
                    
                    if orientation:
                        # 1. 具体键 (包含详细编号，例如 Pb238-I141(axial))
                        detailed_key = f"{CENTER_ATOM}{center}-{COORD_ATOM}{coord_num}({orientation})"
                        if detailed_key not in detailed_stats:
                            detailed_stats[detailed_key] = {'sum': 0.0, 'count': 0, 'min': float('inf'), 'max': float('-inf')}
                        ds = detailed_stats[detailed_key]
                        ds['sum'] += current_distance
                        ds['count'] += 1
                        ds['min'] = min(ds['min'], current_distance)
                        ds['max'] = max(ds['max'], current_distance)

                        # 2. 汇总键
                        keys_to_update =[
                            f"{CENTER_ATOM}{center}-{COORD_ATOM}({orientation})",
                            f"{CENTER_ATOM}{center}-{COORD_ATOM}(total)",
                            f"Overall_{CENTER_ATOM}-{COORD_ATOM}({orientation})",
                            f"Overall_{CENTER_ATOM}-{COORD_ATOM}(total)"
                        ]

                        for bond_key in keys_to_update:
                            if bond_key not in summary_stats:
                                summary_stats[bond_key] = {'sum': 0.0, 'count': 0, 'min': float('inf'), 'max': float('-inf')}
                            stats = summary_stats[bond_key]
                            stats['sum'] += current_distance
                            stats['count'] += 1
                            stats['min'] = min(stats['min'], current_distance)
                            stats['max'] = max(stats['max'], current_distance)
                            
    return detailed_stats, summary_stats

def process_and_print_stats(detailed_stats, summary_stats, dat_file, all_excel_data):
    filename = os.path.basename(dat_file)
    print(f"\n[{filename}] 统计结果：")
    if not summary_stats:
        print("没有找到匹配的键数据，请检查配位判定参数或键长范围。")
        return
    
    def sort_key(key_str):
        # 利用正则提取编号，先按中心原子编号排序，再按配位原子编号排序
        match = re.search(r'[A-Za-z]+(\d+)-[A-Za-z]+(\d+)', key_str)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (0, 0)

    def record_data(category_name, stats_dict, keys, sort_function=None):
        sorted_keys = sorted(keys, key=sort_function) if sort_function else sorted(keys)
        for k in sorted_keys:
            v = stats_dict[k]
            avg = v['sum'] / v['count']
            
            print(f"{k:<30} | {avg:<10.5f} | {v['min']:<10.5f} | {v['max']:<10.5f} | {v['count']:<5}")
            
            all_excel_data.append({
                "来源文件 (Source File)": filename,
                "统计分类 (Category)": category_name,
                "键型/编号 (Bond Type)": k,
                "平均值 (Avg / Å)": round(avg, 5),
                "最小值 (Min / Å)": round(v['min'], 5),
                "最大值 (Max / Å)": round(v['max'], 5),
                "计数 (Count)": v['count']
            })

    print(f"{'键型 / Bond Type':<30} | {'平均值(Å)':<10} | {'最小值(Å)':<10} | {'最大值(Å)':<10} | {'数量':<5}")
    print("=" * 80)
    
    print("【详细具体键统计 / Detailed Specific Bonds】")
    record_data("1_Detailed_Specific_Bonds", detailed_stats, detailed_stats.keys(), sort_function=sort_key)
        
    print("-" * 80)
    print("【单中心原子汇总 / Single Center Atom Summaries】")
    individual_keys =[k for k in summary_stats.keys() if not k.startswith("Overall_")]
    record_data("2_Single_Center_Summary", summary_stats, individual_keys)

    print("-" * 80)
    print("【全局整体统计 / Overall Statistics】")
    overall_keys =[k for k in summary_stats.keys() if k.startswith("Overall_")]
    record_data("3_Overall_Statistics", summary_stats, overall_keys)
    print("=" * 80)

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    poscar_path = os.path.join(current_dir, 'POSCAR')
    
    if not os.path.exists(poscar_path):
        print("错误：未在当前目录下找到 POSCAR 文件。")
        return

    print("正在解析 POSCAR 并建立八面体坐标映射表...")
    cell, elements, coords = read_poscar(poscar_path)
    center_map = build_center_coord_map(cell, elements, coords, CENTER_ATOM, COORD_ATOM)

    dat_files = glob.glob(os.path.join(current_dir, '*.dat'))
    if not dat_files:
        print("当前文件夹下没有找到任何 .dat 文件")
        return
    
    # 建立一个空列表，用于收集所有的统计数据（为了最终输出到 Excel）
    all_excel_data =[]  
    
    for f in dat_files:
        detailed_stats, summary_stats = analyze_dat_file(f, center_map, MIN_DIST, MAX_DIST)
        process_and_print_stats(detailed_stats, summary_stats, f, all_excel_data)
        
    # --- 将收集到的数据导出为 Excel ---
    if all_excel_data:
        excel_path = os.path.join(current_dir, EXCEL_OUTPUT_FILE)
        df = pd.DataFrame(all_excel_data)
        
        # 排序：按文件 -> 统计分类 -> 键型/编号，确保 Excel 里的数据井然有序
        df.sort_values(by=["来源文件 (Source File)", "统计分类 (Category)", "键型/编号 (Bond Type)"], inplace=True)
        
        # 输出到 Excel
        df.to_excel(excel_path, index=False)
        print(f"\n 所有数据已成功汇总并导出至 Excel 文件：{excel_path}")
    else:
        print("\n 没有提取到任何有效数据，未生成 Excel 文件。")

if __name__ == '__main__':
    main()
